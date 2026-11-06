"""
ResearchMind AI – Fact Checker Agent
=======================================
The Fact Checker Agent extracts important factual claims from the
analysis and verifies each one against the collected evidence.

Responsibilities:
  1. Extract key factual claims from the analyst's findings.
  2. For each claim, examine the cited source excerpts.
  3. Assign a VerificationStatus based solely on collected evidence.
  4. Never treat LLM internal knowledge as proof.
  5. Flag claims that need more evidence for additional research.

Verification statuses:
  - VERIFIED: Directly supported by cited sources.
  - PARTIALLY_SUPPORTED: Some evidence exists but not conclusive.
  - UNSUPPORTED: No supporting evidence found in collected sources.
  - CONTRADICTED: Sources explicitly contradict the claim.
  - NEEDS_MORE_EVIDENCE: Insufficient sources to verify.

Design notes:
  - The Fact Checker assesses support in available evidence only.
  - It does NOT guarantee universal truth — only evidence-grounding.
  - Raises FactCheckerError on unrecoverable failures.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.schemas.research import (
    ResearchAnalysis,
    ResearchSource,
    VerificationStatus,
    VerifiedClaim,
)
from app.utils.exceptions import ConfigurationError, FactCheckerError, GeminiError, LLMOutputParseError
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_CLAIMS_TO_CHECK = 15
MAX_EXCERPT_FOR_VERIFICATION = 600


def _build_fact_check_prompt(
    findings_text: str,
    sources: list[ResearchSource],
    source_map: dict[str, ResearchSource],
) -> str:
    """Build the Gemini prompt for fact checking."""

    # Format sources as evidence blocks
    evidence_block = ""
    for s in sources[:30]:  # Limit to prevent token overflow
        excerpt = s.excerpt[:MAX_EXCERPT_FOR_VERIFICATION] if s.excerpt else "(no excerpt)"
        evidence_block += (
            f"\nEVIDENCE_ID: {s.source_id}\n"
            f"Source: {s.title} ({s.domain})\n"
            f"Text: {excerpt}\n---"
        )

    valid_ids = [s.source_id for s in sources[:30]]

    prompt = f"""You are a rigorous fact-checker for an AI research platform.

Your job is to assess whether key claims from research analysis are supported by the collected evidence.

IMPORTANT RULES:
- Base verification ONLY on the evidence provided below — not on your internal training knowledge.
- "VERIFIED" means the evidence explicitly supports the claim.
- "PARTIALLY_SUPPORTED" means some evidence exists but it is incomplete or indirect.
- "UNSUPPORTED" means no evidence in the collection addresses this claim.
- "CONTRADICTED" means evidence directly contradicts the claim.
- "NEEDS_MORE_EVIDENCE" means the claim is important but requires more sources.

RESEARCH FINDINGS TO FACT-CHECK:
{findings_text}

COLLECTED EVIDENCE:
{evidence_block}

VALID EVIDENCE IDs (use ONLY these):
{json.dumps(valid_ids)}

TASK:
1. Extract up to {MAX_CLAIMS_TO_CHECK} important factual claims from the findings above.
2. For each claim, determine its verification status based ONLY on the evidence above.
3. List the evidence IDs that support OR contradict the claim.

Return ONLY valid JSON in this exact structure:
{{
  "verified_claims": [
    {{
      "claim": "The specific factual claim being assessed.",
      "status": "VERIFIED",
      "reasoning": "Explanation of why this status was assigned based on the evidence.",
      "supporting_source_ids": ["evidence_id_1"],
      "contradicting_source_ids": [],
      "note": "Optional: additional context or caveats."
    }}
  ],
  "needs_more_research": false,
  "research_gaps": ["Optional: specific gaps that require additional research"]
}}

Valid status values: VERIFIED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTED, NEEDS_MORE_EVIDENCE
"""
    return prompt


def _parse_fact_check_response(
    raw_text: str, sources: list[ResearchSource]
) -> tuple[list[VerifiedClaim], bool, list[str]]:
    """Parse the Gemini fact-check response and validate source IDs."""
    text = raw_text.strip()

    # Remove markdown code blocks
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError as e:
                raise LLMOutputParseError(
                    f"Could not parse Fact Checker response as JSON: {e}",
                    raw_output=raw_text,
                )
        else:
            raise LLMOutputParseError(
                "No JSON found in Fact Checker response.", raw_output=raw_text
            )

    valid_source_ids = {s.source_id for s in sources}
    claims: list[VerifiedClaim] = []

    for c_raw in data.get("verified_claims", []):
        if not isinstance(c_raw, dict):
            continue

        # Validate status
        raw_status = c_raw.get("status", "UNSUPPORTED").upper()
        try:
            status = VerificationStatus(raw_status)
        except ValueError:
            status = VerificationStatus.UNSUPPORTED

        # Filter to real source IDs only
        supporting = [
            sid for sid in c_raw.get("supporting_source_ids", [])
            if sid in valid_source_ids
        ]
        contradicting = [
            sid for sid in c_raw.get("contradicting_source_ids", [])
            if sid in valid_source_ids
        ]

        claim_text = c_raw.get("claim", "").strip()
        if not claim_text:
            continue

        claims.append(VerifiedClaim(
            claim=claim_text,
            status=status,
            reasoning=c_raw.get("reasoning", ""),
            supporting_source_ids=supporting,
            contradicting_source_ids=contradicting,
            note=c_raw.get("note", ""),
        ))

    needs_more_research = bool(data.get("needs_more_research", False))
    research_gaps = data.get("research_gaps", [])

    return claims, needs_more_research, research_gaps


class FactCheckerAgent:
    """
    Fact Checker Agent – verifies claims against collected evidence.

    Uses Gemini to assess whether factual claims from the analysis
    are supported, partially supported, unsupported, or contradicted
    by the collected sources.

    Usage:
        agent = FactCheckerAgent()
        claims, needs_more = await agent.verify(analysis, sources)
    """

    def __init__(self) -> None:
        if not settings.is_gemini_configured:
            raise ConfigurationError(
                "GEMINI_API_KEY is not configured. "
                "Add your Gemini API key to the .env file."
            )
        try:
            from google import genai  # type: ignore[import]
            self._client = genai.Client(api_key=settings.gemini_api_key)
        except ImportError as e:
            raise ConfigurationError(f"google-genai package not installed: {e}")

        self._model = settings.gemini_model
        logger.info("fact_checker_agent_initialized", model=self._model)

    @retry(
        retry=retry_if_exception_type(GeminiError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def verify(
        self,
        analysis: ResearchAnalysis,
        sources: list[ResearchSource],
    ) -> tuple[list[VerifiedClaim], bool, list[str]]:
        """
        Verify factual claims from the analysis against collected sources.

        Args:
            analysis: The ResearchAnalysis from the Analyst Agent.
            sources: Real sources collected by the Researcher Agent.

        Returns:
            Tuple of:
              - List of VerifiedClaim objects with status and reasoning.
              - Boolean: True if more research is needed.
              - List of research gaps (topics that need more evidence).

        Raises:
            FactCheckerError: If verification fails.
        """
        logger.info(
            "fact_checker_starting",
            finding_count=len(analysis.findings),
            source_count=len(sources),
        )

        # Build a text representation of findings for the prompt
        findings_text = ""
        for i, f in enumerate(analysis.findings[:MAX_CLAIMS_TO_CHECK], 1):
            findings_text += f"{i}. [{f.category}] {f.finding}\n"

        if not findings_text.strip():
            raise FactCheckerError("No findings provided to fact-check.")

        # Build source map for validation
        source_map = {s.source_id: s for s in sources}

        prompt = _build_fact_check_prompt(findings_text, sources, source_map)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config={"temperature": 0.1, "max_output_tokens": 8192},
            )
            raw_text = response.text
        except Exception as e:
            error_msg = str(e)
            logger.error("gemini_fact_checker_error", error=error_msg)
            raise GeminiError(f"Gemini API call failed in Fact Checker: {error_msg}")

        if not raw_text or not raw_text.strip():
            raise FactCheckerError("Gemini returned empty response in Fact Checker.")

        claims, needs_more_research, research_gaps = _parse_fact_check_response(
            raw_text, sources
        )

        # Count verification statuses for logging
        status_counts: dict[str, int] = {}
        for c in claims:
            status_counts[c.status.value] = status_counts.get(c.status.value, 0) + 1

        logger.info(
            "fact_checker_complete",
            claims_verified=len(claims),
            needs_more_research=needs_more_research,
            status_counts=status_counts,
        )

        return claims, needs_more_research, research_gaps

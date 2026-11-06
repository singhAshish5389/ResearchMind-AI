"""
ResearchMind AI – Analyst Agent
=================================
The Analyst Agent examines collected research sources and produces
structured findings with evidence-linked analysis.

Responsibilities:
  1. Analyze all collected sources for a research topic.
  2. Identify themes, trends, opportunities, risks, contradictions.
  3. Link every finding to real source IDs (never invented).
  4. Detect evidence gaps and missing information.
  5. Return a validated ResearchAnalysis Pydantic model.

Design notes:
  - Every finding includes evidence_source_ids pointing to real sources.
  - LLM is given source IDs explicitly so it can reference them correctly.
  - Raises AnalystError on unrecoverable failures.
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
    ResearchFinding,
    ResearchPlan,
    ResearchSource,
)
from app.utils.exceptions import AnalystError, ConfigurationError, GeminiError, LLMOutputParseError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Max characters of source content to include in the prompt
MAX_SOURCE_EXCERPT_CHARS = 800
MAX_SOURCES_IN_PROMPT = 40  # Prevent token overflow


def _build_analyst_prompt(
    plan: ResearchPlan, sources: list[ResearchSource]
) -> str:
    """
    Build the Gemini prompt for the Analyst Agent.

    Includes real source excerpts with their source IDs so the LLM
    can correctly cite them in findings.
    """
    # Limit to prevent token overflow
    sources_to_analyze = sources[:MAX_SOURCES_IN_PROMPT]

    # Format sources as numbered references
    source_block = ""
    for s in sources_to_analyze:
        excerpt = s.excerpt[:MAX_SOURCE_EXCERPT_CHARS] if s.excerpt else "(no excerpt)"
        source_block += (
            f"\n---\n"
            f"SOURCE_ID: {s.source_id}\n"
            f"Title: {s.title}\n"
            f"Domain: {s.domain}\n"
            f"Excerpt: {excerpt}\n"
        )

    source_ids = [s.source_id for s in sources_to_analyze]

    prompt = f"""You are an expert research analyst for an AI research platform.

RESEARCH TOPIC: {plan.topic}

RESEARCH OBJECTIVES: {plan.scope_and_objectives}

You have been provided with {len(sources_to_analyze)} research sources collected from the internet.
Your job is to analyze these sources and extract structured findings.

COLLECTED SOURCES:
{source_block}

VALID SOURCE IDs (you MUST only use these when citing):
{json.dumps(source_ids, indent=2)}

INSTRUCTIONS:
1. Identify 5-12 specific, concrete findings from the sources.
2. Each finding MUST cite 1-3 SOURCE_IDs from the list above. Never invent source IDs.
3. Classify each finding: is it a trend, opportunity, risk, or contradiction?
4. Identify 3-6 common themes across sources.
5. Note any conflicting statements between sources.
6. Note any evidence gaps (topics mentioned in the objectives but not covered by sources).
7. Write a 2-3 paragraph overall summary.

CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY valid JSON. No markdown. No explanation.
- evidence_source_ids must ONLY contain IDs from VALID SOURCE IDs list above.

{{
  "summary": "2-3 paragraph overall analysis summary...",
  "themes": ["Theme 1", "Theme 2", "Theme 3"],
  "findings": [
    {{
      "category": "Market Trends",
      "finding": "Specific, concrete finding statement...",
      "evidence_source_ids": ["source_id_1", "source_id_2"],
      "confidence": 0.85,
      "is_trend": true,
      "is_opportunity": false,
      "is_risk": false,
      "is_contradiction": false
    }}
  ],
  "contradictions": ["Contradiction 1 (cite source IDs in text)"],
  "evidence_gaps": ["Gap 1: topic not covered by collected sources"]
}}

Generate between 5 and 12 findings. Be specific, evidence-based, and avoid vague generalizations.
"""
    return prompt


def _parse_and_validate(raw_text: str, sources: list[ResearchSource]) -> ResearchAnalysis:
    """Parse LLM JSON response and validate source IDs."""
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
                    f"Could not parse Analyst response as JSON: {e}", raw_output=raw_text
                )
        else:
            raise LLMOutputParseError(
                "No JSON object found in Analyst response.", raw_output=raw_text
            )

    # Build valid source ID set for citation validation
    valid_source_ids = {s.source_id for s in sources}

    findings: list[ResearchFinding] = []
    for i, f_raw in enumerate(data.get("findings", [])):
        if not isinstance(f_raw, dict):
            continue

        # Validate and filter source IDs — only keep real ones
        raw_ids = f_raw.get("evidence_source_ids", [])
        valid_ids = [sid for sid in raw_ids if sid in valid_source_ids]

        if not valid_ids:
            logger.warning("finding_has_no_valid_source_ids", finding_index=i)
            # Still include the finding but flag it
            valid_ids = []

        try:
            confidence = float(f_raw.get("confidence", 0.7))
            confidence = max(0.0, min(1.0, confidence))

            finding = ResearchFinding(
                category=f_raw.get("category", "General"),
                finding=f_raw.get("finding", ""),
                evidence_source_ids=valid_ids,
                confidence=confidence,
                is_trend=bool(f_raw.get("is_trend", False)),
                is_opportunity=bool(f_raw.get("is_opportunity", False)),
                is_risk=bool(f_raw.get("is_risk", False)),
                is_contradiction=bool(f_raw.get("is_contradiction", False)),
            )
            findings.append(finding)
        except Exception as e:
            logger.warning("finding_validation_failed", index=i, error=str(e))
            continue

    if not findings:
        raise AnalystError("Analyst produced zero valid findings.")

    return ResearchAnalysis(
        summary=data.get("summary", ""),
        themes=data.get("themes", []),
        findings=findings,
        contradictions=data.get("contradictions", []),
        evidence_gaps=data.get("evidence_gaps", []),
        created_at=datetime.now(timezone.utc),
    )


class AnalystAgent:
    """
    Analyst Agent – analyzes collected research sources.

    Uses Gemini to identify patterns, trends, opportunities, and risks
    from real collected sources. Every finding cites real source IDs.

    Usage:
        agent = AnalystAgent()
        analysis = await agent.analyze(plan, sources)
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
        logger.info("analyst_agent_initialized", model=self._model)

    @retry(
        retry=retry_if_exception_type(GeminiError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def analyze(
        self, plan: ResearchPlan, sources: list[ResearchSource]
    ) -> ResearchAnalysis:
        """
        Analyze collected sources and produce structured findings.

        Args:
            plan: The approved ResearchPlan (for context).
            sources: Real sources collected by the Researcher Agent.

        Returns:
            Validated ResearchAnalysis with evidence-linked findings.

        Raises:
            AnalystError: If analysis fails or produces invalid output.
        """
        if not sources:
            raise AnalystError(
                "Cannot analyze: no sources provided. "
                "The Researcher Agent must run first."
            )

        logger.info(
            "analyst_starting",
            source_count=len(sources),
            topic=plan.topic[:100],
        )

        prompt = _build_analyst_prompt(plan, sources)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config={"temperature": 0.2, "max_output_tokens": 8192},
            )
            raw_text = response.text
        except Exception as e:
            error_msg = str(e)
            logger.error("gemini_analyst_error", error=error_msg)
            raise GeminiError(f"Gemini API call failed in Analyst: {error_msg}")

        if not raw_text or not raw_text.strip():
            raise AnalystError("Gemini returned empty response in Analyst.")

        analysis = _parse_and_validate(raw_text, sources)

        logger.info(
            "analyst_complete",
            finding_count=len(analysis.findings),
            theme_count=len(analysis.themes),
        )

        return analysis

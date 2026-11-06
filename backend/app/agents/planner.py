"""
ResearchMind AI – Planner Agent
================================
The Planner Agent is responsible for understanding a research topic and
producing a structured, validated research plan.

Responsibilities:
  1. Understand the user's research topic and intent.
  2. Identify the scope and objectives.
  3. Generate 3–10 targeted research questions (based on depth setting).
  4. Generate optimized search queries for each question.
  5. Identify high-level information categories.
  6. Estimate research duration.
  7. Return a validated ResearchPlan Pydantic model.

Design notes:
  - Agent logic lives here; LangGraph node wrappers live in graph/workflow.py.
  - All LLM calls go through the GeminiClient helper (handles retries).
  - No fake or hardcoded research plans — always calls Gemini.
  - Validates output with Pydantic before returning.
  - Raises PlannerError on unrecoverable failures.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import uuid4

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.schemas.research import (
    ResearchDepth,
    ResearchMode,
    ResearchPlan,
    ResearchQuestion,
    ResearchRequest,
)
from app.utils.exceptions import ConfigurationError, GeminiError, LLMOutputParseError, PlannerError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Depth configuration ───────────────────────────────────────────────────────
DEPTH_CONFIG: dict[ResearchDepth, dict] = {
    ResearchDepth.QUICK: {
        "min_questions": 3,
        "max_questions": 5,
        "estimated_minutes": 3,
        "description": "Quick overview",
    },
    ResearchDepth.STANDARD: {
        "min_questions": 5,
        "max_questions": 7,
        "estimated_minutes": 8,
        "description": "Standard research depth",
    },
    ResearchDepth.COMPREHENSIVE: {
        "min_questions": 8,
        "max_questions": 10,
        "estimated_minutes": 15,
        "description": "Comprehensive, in-depth research",
    },
}


def _build_planner_prompt(request: ResearchRequest) -> str:
    """
    Build the system + user prompt for the Planner Agent.

    The prompt instructs Gemini to return strictly valid JSON
    that matches our ResearchPlan schema.
    """
    config = DEPTH_CONFIG[request.depth]
    min_q = request.max_questions or config["min_questions"]
    max_q = request.max_questions or config["max_questions"]

    prompt = f"""You are an expert research planner for an AI research platform.

Your task is to analyze the following research topic and create a structured research plan.

RESEARCH TOPIC:
{request.topic}

RESEARCH SETTINGS:
- Depth: {request.depth.value} ({config["description"]})
- Mode: {request.mode.value}
- Number of questions: {min_q} to {max_q}
- Report language: {request.language}

INSTRUCTIONS:
1. Carefully read and understand the research topic.
2. Define clear scope and objectives for this research.
3. Identify {min_q} to {max_q} specific, distinct research questions that together cover the topic comprehensively.
4. For each question, generate 2-3 precise internet search queries that will find high-quality, relevant results.
5. Group questions into logical information categories.
6. Each question must be genuinely useful — avoid redundant or trivial questions.
7. Prioritize questions: 1=high (critical to the topic), 2=medium, 3=low (nice to have).

CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY valid JSON. No markdown code blocks. No explanation text.
- The JSON must match this exact structure:

{{
  "scope_and_objectives": "A clear, 2-3 sentence statement of what this research aims to discover and why.",
  "information_categories": ["Category 1", "Category 2", "Category 3"],
  "estimated_duration_minutes": {config["estimated_minutes"]},
  "research_questions": [
    {{
      "question": "The specific research question?",
      "category": "Category name",
      "priority": 1,
      "search_queries": [
        "search query 1",
        "search query 2"
      ],
      "rationale": "Why this question is important for this research topic."
    }}
  ]
}}

Generate between {min_q} and {max_q} research questions.
Make search queries specific, keyword-rich, and likely to return high-quality results.
Do NOT include generic queries like "research topic information".
"""
    return prompt


def _parse_llm_response(raw_text: str) -> dict:
    """
    Parse the raw LLM text response into a Python dictionary.

    Handles common LLM output issues:
    - JSON wrapped in markdown code blocks (```json ... ```)
    - Leading/trailing whitespace
    - Common escape issues
    """
    text = raw_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        # Extract content between first ``` and last ```
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Attempt to parse as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find a JSON object within the text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        raise LLMOutputParseError(
            message=f"Could not parse Gemini response as JSON: {e}",
            raw_output=raw_text,
        )


def _validate_plan_data(data: dict, request: ResearchRequest) -> ResearchPlan:
    """
    Convert the parsed LLM dictionary into a validated ResearchPlan.

    Adds generated IDs and timestamps for each ResearchQuestion.
    Raises PlannerError if required fields are missing.
    """
    required_fields = ["scope_and_objectives", "information_categories", "research_questions"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise PlannerError(
            f"Planner LLM response missing required fields: {missing}",
            details={"missing_fields": missing, "received_keys": list(data.keys())},
        )

    questions_raw = data.get("research_questions", [])
    if not questions_raw:
        raise PlannerError("Planner returned zero research questions.")

    # Build ResearchQuestion objects with generated IDs
    questions: list[ResearchQuestion] = []
    for i, q_raw in enumerate(questions_raw):
        if not isinstance(q_raw, dict):
            logger.warning("skipping_invalid_question", index=i, value=q_raw)
            continue
        try:
            question = ResearchQuestion(
                id=str(uuid4()),
                question=q_raw.get("question", ""),
                category=q_raw.get("category", "General"),
                priority=q_raw.get("priority", 2),
                search_queries=q_raw.get("search_queries", []),
                rationale=q_raw.get("rationale", ""),
            )
            questions.append(question)
        except Exception as e:
            logger.warning("question_validation_failed", index=i, error=str(e))
            continue

    if len(questions) < 2:
        raise PlannerError(
            f"Planner produced only {len(questions)} valid question(s). Minimum is 2.",
            details={"raw_questions": questions_raw},
        )

    plan = ResearchPlan(
        plan_id=str(uuid4()),
        topic=request.topic,
        scope_and_objectives=data["scope_and_objectives"],
        information_categories=data.get("information_categories", []),
        research_questions=questions,
        estimated_duration_minutes=data.get("estimated_duration_minutes", 10),
        depth=request.depth,
        mode=request.mode,
        language=request.language,
        created_at=datetime.utcnow(),
        metadata={
            "model": settings.gemini_model,
            "question_count": len(questions),
        },
    )
    return plan


class PlannerAgent:
    """
    Planner Agent – generates a structured research plan from a user request.

    This agent uses the Google Gemini API to understand the research topic
    and produce a validated ResearchPlan.

    Usage:
        agent = PlannerAgent()
        plan = await agent.create_plan(request)
    """

    def __init__(self) -> None:
        if not settings.is_gemini_configured:
            raise ConfigurationError(
                "GEMINI_API_KEY is not configured. "
                "Please add your Gemini API key to the .env file. "
                "Get it at: https://aistudio.google.com/apikey"
            )

        # Import here so the module can be loaded without the key for testing
        try:
            from google import genai  # type: ignore[import]
            self._client = genai.Client(api_key=settings.gemini_api_key)
        except ImportError as e:
            raise ConfigurationError(
                f"google-genai package is not installed: {e}. "
                "Run: pip install google-genai"
            )

        self._model = settings.gemini_model
        logger.info("planner_agent_initialized", model=self._model)

    @retry(
        retry=retry_if_exception_type(GeminiError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def create_plan(self, request: ResearchRequest) -> ResearchPlan:
        """
        Generate a structured research plan for the given request.

        This is the main entry point for the Planner Agent.
        Calls Gemini with a structured prompt and validates the output.

        Args:
            request: The validated ResearchRequest from the user.

        Returns:
            A validated ResearchPlan ready for user review.

        Raises:
            ConfigurationError: If Gemini API key is missing.
            GeminiError: If the Gemini API call fails after retries.
            PlannerError: If the response cannot be parsed or is invalid.
        """
        logger.info(
            "planner_agent_starting",
            topic=request.topic[:100],
            depth=request.depth.value,
            mode=request.mode.value,
        )

        prompt = _build_planner_prompt(request)

        try:
            # Call Gemini API using the google-genai SDK
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config={
                    "temperature": 0.3,        # Lower = more structured, predictable output
                    "max_output_tokens": 4096,
                },
            )
        except Exception as e:
            error_msg = str(e)
            logger.error("gemini_api_error", error=error_msg)

            # Check for common, actionable errors
            if "API key" in error_msg or "UNAUTHENTICATED" in error_msg:
                raise GeminiError("Invalid or missing GEMINI_API_KEY. Check your .env file.")
            if "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                raise GeminiError("Gemini API quota exceeded. Wait a moment and try again.")
            if "model" in error_msg.lower() and "not found" in error_msg.lower():
                raise GeminiError(
                    f"Gemini model '{self._model}' not found. "
                    "Check GEMINI_MODEL in your .env file. "
                    "See: https://ai.google.dev/gemini-api/docs/models"
                )

            raise GeminiError(f"Gemini API call failed: {error_msg}")

        # Extract text from response
        try:
            raw_text = response.text
        except Exception as e:
            raise GeminiError(f"Could not extract text from Gemini response: {e}")

        if not raw_text or not raw_text.strip():
            raise PlannerError("Gemini returned an empty response.")

        logger.debug("planner_raw_response", length=len(raw_text))

        # Parse and validate
        data = _parse_llm_response(raw_text)
        plan = _validate_plan_data(data, request)

        logger.info(
            "planner_plan_created",
            plan_id=plan.plan_id,
            question_count=len(plan.research_questions),
        )

        return plan

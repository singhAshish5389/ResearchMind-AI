"""
ResearchMind AI – Planner Schema and Agent Tests
=================================================
Tests for:
1. ResearchRequest schema validation (input validation)
2. ResearchPlan schema validation (output validation)
3. Planner Agent internal parsing logic (no Gemini API calls)
4. Error handling for malformed LLM output

All tests run without consuming Gemini API credits.
Actual Gemini integration is tested with the `integration` marker.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.research import (
    ResearchDepth,
    ResearchMode,
    ResearchPlan,
    ResearchQuestion,
    ResearchRequest,
    VerificationStatus,
)
from app.utils.exceptions import LLMOutputParseError, PlannerError


# ─── ResearchRequest Validation ───────────────────────────────────────────────


class TestResearchRequestSchema:
    """Tests for the ResearchRequest input schema."""

    def test_valid_request_minimal(self):
        """A request with just a topic should use default values."""
        req = ResearchRequest(topic="What is the future of AI in healthcare?")
        assert req.depth == ResearchDepth.STANDARD
        assert req.mode == ResearchMode.WEB
        assert req.language == "English"
        assert req.document_ids == []

    def test_valid_request_full(self):
        """A fully specified request should preserve all values."""
        req = ResearchRequest(
            topic="Analyze blockchain adoption in supply chain management.",
            depth=ResearchDepth.COMPREHENSIVE,
            mode=ResearchMode.HYBRID,
            max_questions=8,
            max_results_per_query=5,
            language="Hindi",
            document_ids=["doc-1", "doc-2"],
        )
        assert req.depth == ResearchDepth.COMPREHENSIVE
        assert req.mode == ResearchMode.HYBRID
        assert req.max_questions == 8
        assert req.language == "Hindi"

    def test_topic_too_short(self):
        """Topics shorter than 10 characters should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchRequest(topic="AI jobs")
        errors = exc_info.value.errors()
        assert any("topic" in str(e) for e in errors)

    def test_topic_too_long(self):
        """Topics longer than 2000 characters should fail validation."""
        long_topic = "A" * 2001
        with pytest.raises(ValidationError):
            ResearchRequest(topic=long_topic)

    def test_topic_whitespace_stripped(self):
        """Leading and trailing whitespace should be stripped from the topic."""
        req = ResearchRequest(topic="   The future of quantum computing   ")
        assert req.topic == "The future of quantum computing"

    def test_document_ids_upgrade_mode_to_hybrid(self):
        """If document_ids are provided but mode is WEB, it should auto-upgrade to HYBRID."""
        req = ResearchRequest(
            topic="Climate change impact on agriculture.",
            mode=ResearchMode.WEB,
            document_ids=["doc-1"],
        )
        assert req.mode == ResearchMode.HYBRID

    def test_max_questions_bounds(self):
        """max_questions must be between 3 and 10."""
        with pytest.raises(ValidationError):
            ResearchRequest(topic="Valid topic here for testing.", max_questions=2)
        with pytest.raises(ValidationError):
            ResearchRequest(topic="Valid topic here for testing.", max_questions=11)

    def test_invalid_depth_value(self):
        """Invalid depth values should fail validation."""
        with pytest.raises(ValidationError):
            ResearchRequest(topic="Valid topic here for testing.", depth="ultra")

    def test_invalid_mode_value(self):
        """Invalid mode values should fail validation."""
        with pytest.raises(ValidationError):
            ResearchRequest(topic="Valid topic here for testing.", mode="internet")


# ─── ResearchPlan Schema ──────────────────────────────────────────────────────


class TestResearchPlanSchema:
    """Tests for the ResearchPlan output schema."""

    def test_valid_plan(self, sample_research_plan):
        """A complete, valid research plan should parse without errors."""
        plan = ResearchPlan(**sample_research_plan)
        assert plan.plan_id == "test-plan-123"
        assert len(plan.research_questions) == 3
        assert plan.depth == ResearchDepth.STANDARD

    def test_plan_requires_minimum_questions(self):
        """A plan with fewer than 3 questions should fail Pydantic validation."""
        with pytest.raises(ValidationError):
            ResearchPlan(
                topic="Test topic",
                scope_and_objectives="Test scope",
                information_categories=["Cat1"],
                research_questions=[],  # Empty – should fail min_length=3
                estimated_duration_minutes=5,
                depth=ResearchDepth.QUICK,
                mode=ResearchMode.WEB,
                language="English",
            )

    def test_research_question_has_auto_id(self):
        """ResearchQuestion should auto-generate an ID if none provided."""
        q = ResearchQuestion(
            question="What are the top AI frameworks?",
            category="Technology",
            priority=1,
            search_queries=["top AI frameworks 2024"],
            rationale="Understanding frameworks helps engineers make technology choices.",
        )
        assert q.id is not None
        assert len(q.id) > 0

    def test_research_question_priority_bounds(self):
        """Priority must be between 1 and 3."""
        with pytest.raises(ValidationError):
            ResearchQuestion(
                question="Test question for validation purposes?",
                category="Test",
                priority=0,  # Too low
                search_queries=["test query"],
                rationale="Test rationale.",
            )
        with pytest.raises(ValidationError):
            ResearchQuestion(
                question="Test question for validation purposes?",
                category="Test",
                priority=4,  # Too high
                search_queries=["test query"],
                rationale="Test rationale.",
            )

    def test_plan_auto_generates_id(self, sample_research_plan):
        """If plan_id is not in the data, one should be auto-generated."""
        data = {**sample_research_plan}
        del data["plan_id"]
        plan = ResearchPlan(**data)
        assert plan.plan_id is not None
        assert len(plan.plan_id) > 0


# ─── Planner Agent Internal Logic ────────────────────────────────────────────


class TestPlannerInternalLogic:
    """
    Tests for Planner Agent helper functions.

    These test the parsing and validation logic without calling Gemini.
    """

    def test_parse_valid_json(self):
        """Should parse clean JSON response correctly."""
        from app.agents.planner import _parse_llm_response

        valid_json = json.dumps({
            "scope_and_objectives": "Test scope.",
            "information_categories": ["Cat1", "Cat2"],
            "estimated_duration_minutes": 5,
            "research_questions": [
                {
                    "question": "Test question?",
                    "category": "Cat1",
                    "priority": 1,
                    "search_queries": ["test query"],
                    "rationale": "Important.",
                }
            ],
        })
        result = _parse_llm_response(valid_json)
        assert "research_questions" in result
        assert result["estimated_duration_minutes"] == 5

    def test_parse_json_with_markdown_wrapper(self):
        """Should extract JSON from a markdown code block."""
        from app.agents.planner import _parse_llm_response

        wrapped = '''```json
{
    "scope_and_objectives": "Test scope.",
    "information_categories": ["Cat1"],
    "estimated_duration_minutes": 5,
    "research_questions": []
}
```'''
        result = _parse_llm_response(wrapped)
        assert result["scope_and_objectives"] == "Test scope."

    def test_parse_invalid_json_raises_error(self):
        """Completely invalid text should raise LLMOutputParseError."""
        from app.agents.planner import _parse_llm_response

        with pytest.raises(LLMOutputParseError):
            _parse_llm_response("This is just plain text, not JSON at all.")

    def test_validate_plan_data_missing_fields(self):
        """Missing required fields should raise PlannerError."""
        from app.agents.planner import _validate_plan_data

        incomplete_data = {"scope_and_objectives": "Test scope."}
        request = ResearchRequest(topic="Test topic for plan validation.")

        with pytest.raises(PlannerError) as exc_info:
            _validate_plan_data(incomplete_data, request)
        assert "missing required fields" in str(exc_info.value).lower()

    def test_validate_plan_data_too_few_questions(self):
        """Too few valid questions should raise PlannerError."""
        from app.agents.planner import _validate_plan_data

        data = {
            "scope_and_objectives": "Test scope.",
            "information_categories": ["Cat1"],
            "estimated_duration_minutes": 5,
            "research_questions": [
                # Only 1 question – below minimum of 2
                {
                    "question": "Only one question?",
                    "category": "Cat1",
                    "priority": 1,
                    "search_queries": ["test query"],
                    "rationale": "Test.",
                }
            ],
        }
        request = ResearchRequest(topic="Test topic for validation purposes only.")

        with pytest.raises(PlannerError) as exc_info:
            _validate_plan_data(data, request)
        assert "valid question" in str(exc_info.value).lower()

    def test_validate_plan_data_malformed_questions_skipped(self):
        """Malformed question entries should be skipped, not crash the agent."""
        from app.agents.planner import _validate_plan_data

        data = {
            "scope_and_objectives": "Test scope.",
            "information_categories": ["Cat1"],
            "estimated_duration_minutes": 5,
            "research_questions": [
                {"question": "Valid question one?", "category": "Cat1", "priority": 1,
                 "search_queries": ["query 1"], "rationale": "Reason."},
                "not_a_dict",  # Malformed – should be skipped
                {"question": "Valid question two?", "category": "Cat1", "priority": 2,
                 "search_queries": ["query 2"], "rationale": "Reason."},
                None,  # Also malformed – should be skipped
                {"question": "Valid question three?", "category": "Cat2", "priority": 1,
                 "search_queries": ["query 3"], "rationale": "Reason."},
            ],
        }
        request = ResearchRequest(topic="Testing malformed question handling.")
        plan = _validate_plan_data(data, request)
        assert len(plan.research_questions) == 3  # Only valid questions included


# ─── VerificationStatus Enum ──────────────────────────────────────────────────


class TestVerificationStatus:
    """Tests for the VerificationStatus enum."""

    def test_all_statuses_accessible(self):
        """All expected verification statuses should exist."""
        assert VerificationStatus.VERIFIED == "VERIFIED"
        assert VerificationStatus.PARTIALLY_SUPPORTED == "PARTIALLY_SUPPORTED"
        assert VerificationStatus.UNSUPPORTED == "UNSUPPORTED"
        assert VerificationStatus.CONTRADICTED == "CONTRADICTED"
        assert VerificationStatus.NEEDS_MORE_EVIDENCE == "NEEDS_MORE_EVIDENCE"

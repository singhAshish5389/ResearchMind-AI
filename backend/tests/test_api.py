"""
ResearchMind AI – API Endpoint Tests
=====================================
Tests for FastAPI endpoints using the TestClient (no live server needed).

Tests:
1. Health check endpoint
2. Research plan endpoint (with mocked Gemini)
3. Error handling for missing API key
4. Input validation errors
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Health Check Tests ───────────────────────────────────────────────────────


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    def test_health_returns_200(self, test_client):
        """Health endpoint must return HTTP 200."""
        response = test_client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_structure(self, test_client):
        """Health response must include status, version, environment, and services."""
        response = test_client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "environment" in data
        assert "services" in data
        assert isinstance(data["services"], dict)

    def test_health_services_include_expected_keys(self, test_client):
        """Services object must include gemini, tavily, database, and qdrant keys."""
        response = test_client.get("/api/health")
        services = response.json()["services"]
        for key in ["gemini", "tavily", "database", "qdrant"]:
            assert key in services, f"Missing service key: {key}"

    def test_root_endpoint(self, test_client):
        """Root endpoint should return a JSON object with API info."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "docs" in data
        assert "health" in data


# ─── Research Plan Endpoint Tests ─────────────────────────────────────────────


class TestResearchPlanEndpoint:
    """Tests for POST /api/research/plan."""

    def test_plan_returns_503_when_gemini_not_configured(self, test_client):
        """
        When GEMINI_API_KEY is not set, the endpoint should return 503
        with a clear error message about which key is needed.
        """
        payload = {
            "topic": "Analyze the impact of AI on software engineering careers.",
            "depth": "standard",
        }
        response = test_client.post("/api/research/plan", json=payload)
        # Should return 503 Service Unavailable (Gemini not configured)
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert "GEMINI_API_KEY" in str(detail) or "gemini" in str(detail).lower()

    def test_plan_validation_topic_too_short(self, test_client):
        """Topics shorter than 10 characters should return 422 Unprocessable Entity."""
        payload = {"topic": "AI"}
        response = test_client.post("/api/research/plan", json=payload)
        assert response.status_code == 422

    def test_plan_validation_missing_topic(self, test_client):
        """Missing topic field should return 422."""
        response = test_client.post("/api/research/plan", json={})
        assert response.status_code == 422

    def test_plan_validation_invalid_depth(self, test_client):
        """Invalid depth value should return 422."""
        payload = {
            "topic": "This is a valid research topic for testing purposes.",
            "depth": "ultra_deep",
        }
        response = test_client.post("/api/research/plan", json=payload)
        assert response.status_code == 422

    def test_plan_with_mocked_gemini(self, test_client, sample_research_plan):
        """
        With a mocked Gemini response, the endpoint should return 201 with a valid plan.

        This test does NOT call the real Gemini API.
        """
        from app.schemas.research import ResearchPlan

        mock_plan = ResearchPlan(**sample_research_plan)

        # Mock the PlannerAgent.create_plan method
        with patch("app.api.research.PlannerAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.create_plan = AsyncMock(return_value=mock_plan)
            MockAgent.return_value = mock_instance

            payload = {
                "topic": "Analyze the future of Generative AI engineering jobs in India.",
                "depth": "standard",
                "mode": "web",
                "language": "English",
            }
            response = test_client.post("/api/research/plan", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "research_id" in data
        assert "plan" in data
        assert "message" in data
        assert data["plan"]["topic"] is not None

    def test_plan_response_has_research_id(self, test_client, sample_research_plan):
        """Response must include a research_id for tracking the research job."""
        from app.schemas.research import ResearchPlan

        mock_plan = ResearchPlan(**sample_research_plan)

        with patch("app.api.research.PlannerAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.create_plan = AsyncMock(return_value=mock_plan)
            MockAgent.return_value = mock_instance

            payload = {
                "topic": "The impact of quantum computing on cybersecurity.",
                "depth": "quick",
            }
            response = test_client.post("/api/research/plan", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "research_id" in data
        assert len(data["research_id"]) > 0

    def test_plan_response_includes_questions(self, test_client, sample_research_plan):
        """Response plan must include research questions."""
        from app.schemas.research import ResearchPlan

        mock_plan = ResearchPlan(**sample_research_plan)

        with patch("app.api.research.PlannerAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.create_plan = AsyncMock(return_value=mock_plan)
            MockAgent.return_value = mock_instance

            payload = {
                "topic": "Climate change mitigation strategies in developing countries.",
                "depth": "standard",
            }
            response = test_client.post("/api/research/plan", json=payload)

        data = response.json()
        plan = data["plan"]
        assert "research_questions" in plan
        assert len(plan["research_questions"]) >= 3

    def test_plan_questions_have_search_queries(self, test_client, sample_research_plan):
        """Each research question must have at least one search query."""
        from app.schemas.research import ResearchPlan

        mock_plan = ResearchPlan(**sample_research_plan)

        with patch("app.api.research.PlannerAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.create_plan = AsyncMock(return_value=mock_plan)
            MockAgent.return_value = mock_instance

            payload = {"topic": "Emerging trends in renewable energy storage technology."}
            response = test_client.post("/api/research/plan", json=payload)

        questions = response.json()["plan"]["research_questions"]
        for q in questions:
            assert "search_queries" in q
            assert len(q["search_queries"]) >= 1


# ─── Stub Endpoint Tests ──────────────────────────────────────────────────────


class TestStubEndpoints:
    """Tests for stubbed endpoints that will be implemented in later phases."""

    def test_start_research_returns_202(self, test_client):
        """POST /api/research should return 202 with an informational message."""
        response = test_client.post("/api/research")
        assert response.status_code == 202

    def test_list_research_returns_200(self, test_client):
        """GET /api/research should return 200."""
        response = test_client.get("/api/research")
        assert response.status_code == 200

    def test_get_research_job_returns_200(self, test_client):
        """GET /api/research/{id} should return 200."""
        response = test_client.get("/api/research/test-id-123")
        assert response.status_code == 200

    def test_request_id_header_present(self, test_client):
        """All responses should include an X-Request-ID header."""
        response = test_client.get("/api/health")
        assert "x-request-id" in response.headers

    def test_process_time_header_present(self, test_client):
        """All responses should include an X-Process-Time-Ms header."""
        response = test_client.get("/api/health")
        assert "x-process-time-ms" in response.headers

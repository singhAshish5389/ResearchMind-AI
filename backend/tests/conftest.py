"""
ResearchMind AI – Pytest Configuration
=======================================
Shared fixtures and configuration for all tests.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Set test environment variables BEFORE importing app modules
# This ensures no real API keys are needed to run tests.
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("TAVILY_API_KEY", "")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:password@localhost:5432/researchmind_test")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-app-secret-key-for-testing-only!")


@pytest.fixture(scope="session")
def test_client():
    """
    Create a FastAPI TestClient for the entire test session.

    This allows us to test the API without a running server.
    """
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def sample_research_request() -> dict:
    """A valid research request payload for use in multiple tests."""
    return {
        "topic": "Analyze the future of Generative AI engineering jobs in India over the next five years.",
        "depth": "standard",
        "mode": "web",
        "language": "English",
    }


@pytest.fixture
def sample_research_plan() -> dict:
    """
    A sample research plan as would be returned by the Planner Agent.
    Used for testing schema validation without calling Gemini.
    """
    return {
        "plan_id": "test-plan-123",
        "topic": "Future of Generative AI jobs in India",
        "scope_and_objectives": "Research the current and future state of GenAI employment in India.",
        "information_categories": ["Skills", "Salaries", "Opportunities", "Risks"],
        "research_questions": [
            {
                "id": "q1",
                "question": "What GenAI skills are most in demand in India?",
                "category": "Skills",
                "priority": 1,
                "search_queries": ["GenAI skills demand India 2024", "LLM engineer skills India"],
                "rationale": "Understanding skill demand helps job seekers prioritize learning.",
            },
            {
                "id": "q2",
                "question": "What are the salary ranges for GenAI engineers in India?",
                "category": "Salaries",
                "priority": 1,
                "search_queries": ["GenAI engineer salary India 2024", "LLM engineer compensation India"],
                "rationale": "Salary data helps candidates evaluate career opportunities.",
            },
            {
                "id": "q3",
                "question": "Which Indian companies are adopting Generative AI?",
                "category": "Industry Adoption",
                "priority": 2,
                "search_queries": ["Indian companies generative AI adoption", "AI startups India 2024"],
                "rationale": "Industry adoption drives job creation.",
            },
        ],
        "estimated_duration_minutes": 8,
        "depth": "standard",
        "mode": "web",
        "language": "English",
        "created_at": "2024-01-01T00:00:00",
        "metadata": {"model": "gemini-2.0-flash", "question_count": 3},
    }

"""
ResearchMind AI – Custom Exception Classes
==========================================
Defines application-level exceptions with structured context.

These exceptions are caught by FastAPI exception handlers in main.py
and converted into consistent JSON error responses.
"""

from __future__ import annotations

from typing import Any


class ResearchMindError(Exception):
    """
    Base exception for all ResearchMind AI application errors.

    Attributes:
        message: Human-readable description of the error.
        code: Machine-readable error code string.
        details: Optional dictionary with extra context.
        status_code: Suggested HTTP status code for API responses.
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ─── Configuration Errors ────────────────────────────────────────────────────


class ConfigurationError(ResearchMindError):
    """Raised when a required configuration value is missing or invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="CONFIGURATION_ERROR", details=details, status_code=500)


# ─── Agent Errors ────────────────────────────────────────────────────────────


class AgentError(ResearchMindError):
    """Base error for agent execution failures."""

    def __init__(
        self,
        message: str,
        code: str = "AGENT_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details, status_code=500)


class PlannerError(AgentError):
    """Raised when the Planner Agent fails to generate a valid research plan."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="PLANNER_ERROR", details=details)


class ResearcherError(AgentError):
    """Raised when the Researcher Agent fails to retrieve sources."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="RESEARCHER_ERROR", details=details)


class AnalystError(AgentError):
    """Raised when the Analyst Agent fails to produce findings."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="ANALYST_ERROR", details=details)


class FactCheckerError(AgentError):
    """Raised when the Fact Checker Agent fails to verify claims."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="FACT_CHECKER_ERROR", details=details)


class ReportWriterError(AgentError):
    """Raised when the Report Writer Agent fails to generate a report."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="REPORT_WRITER_ERROR", details=details)


# ─── API / Validation Errors ─────────────────────────────────────────────────


class ValidationError(ResearchMindError):
    """Raised when request input fails business-level validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details=details, status_code=422)


class NotFoundError(ResearchMindError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, resource_id: str | int) -> None:
        super().__init__(
            message=f"{resource} with id={resource_id!r} was not found.",
            code="NOT_FOUND",
            details={"resource": resource, "id": str(resource_id)},
            status_code=404,
        )


class PermissionError(ResearchMindError):
    """Raised when a user tries to access a resource they do not own."""

    def __init__(self, message: str = "You do not have permission to access this resource.") -> None:
        super().__init__(message, code="PERMISSION_DENIED", status_code=403)


class AuthenticationError(ResearchMindError):
    """Raised when authentication fails (invalid credentials, expired token, etc.)."""

    def __init__(self, message: str = "Authentication failed.", details: dict | None = None) -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR", details=details, status_code=401)


# ─── External Service Errors ──────────────────────────────────────────────────


class ExternalServiceError(ResearchMindError):
    """Raised when an external API (Gemini, Tavily, Qdrant, etc.) fails."""

    def __init__(
        self,
        service: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"{service} error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})},
            status_code=502,
        )


class GeminiError(ExternalServiceError):
    """Raised when the Gemini API returns an error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("Gemini", message, details)


class TavilyError(ExternalServiceError):
    """Raised when the Tavily Search API returns an error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("Tavily", message, details)


class QdrantError(ExternalServiceError):
    """Raised when the Qdrant vector database returns an error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("Qdrant", message, details)


# ─── LLM Output Errors ───────────────────────────────────────────────────────


class LLMOutputParseError(ResearchMindError):
    """
    Raised when an LLM returns output that cannot be parsed as expected.

    This handles cases where Gemini returns malformed JSON or text
    that doesn't match the required Pydantic schema.
    """

    def __init__(self, message: str, raw_output: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="LLM_OUTPUT_PARSE_ERROR",
            details={"raw_output_preview": raw_output[:500], **(details or {})},
            status_code=500,
        )

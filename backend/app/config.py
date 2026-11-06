"""
ResearchMind AI – Application Configuration
============================================
Loads and validates all environment variables using Pydantic Settings.
This is the single source of truth for configuration across the application.

Usage:
    from app.config import settings
    print(settings.gemini_api_key)
"""

from __future__ import annotations

import sys
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    Pydantic automatically reads from environment variables and the .env file.
    Fields with no default are required; fields with defaults are optional.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars gracefully
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "ResearchMind AI"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: str = ""
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # ── Google Gemini ─────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── Tavily Search ─────────────────────────────────────────────────────────
    tavily_api_key: str = ""

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/researchmind"

    # ── Qdrant ───────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "researchmind_documents"

    # ── Hugging Face Embeddings ───────────────────────────────────────────────
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_token: str = ""

    # ── JWT Authentication ────────────────────────────────────────────────────
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── LangSmith Tracing ─────────────────────────────────────────────────────
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "researchmind-ai"

    # ── Langfuse Tracing ──────────────────────────────────────────────────────
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Email ─────────────────────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@researchmind.ai"

    # ── File Uploads ──────────────────────────────────────────────────────────
    max_upload_size_mb: int = 50
    allowed_document_types: str = "pdf,txt,md,docx"

    # ── Optional Future Services ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    storage_provider: str = "local"

    # ─────────────────────────────────────────────────────────────────────────
    # Computed / derived properties
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def allowed_document_types_list(self) -> list[str]:
        """Return allowed document types as a list of lowercase extensions."""
        return [t.strip().lower() for t in self.allowed_document_types.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Return max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_gemini_configured(self) -> bool:
        """True if the Gemini API key has been set."""
        return bool(self.gemini_api_key)

    @property
    def is_tavily_configured(self) -> bool:
        """True if the Tavily API key has been set."""
        return bool(self.tavily_api_key)

    @property
    def is_database_configured(self) -> bool:
        """True if the DATABASE_URL appears to be set."""
        return bool(self.database_url and "username:password" not in self.database_url)

    @property
    def is_qdrant_configured(self) -> bool:
        """True if Qdrant URL is set (API key is optional for local installs)."""
        return bool(self.qdrant_url)

    @property
    def is_langsmith_configured(self) -> bool:
        return self.langchain_tracing_v2 and bool(self.langchain_api_key)

    @property
    def is_langfuse_configured(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    # ─────────────────────────────────────────────────────────────────────────
    # Startup validation – logs warnings for missing optional services
    # ─────────────────────────────────────────────────────────────────────────

    @model_validator(mode="after")
    def warn_on_missing_keys(self) -> "Settings":
        """
        Print startup warnings for missing API keys so users know which
        features are unavailable. Does NOT crash the application.
        """
        warnings: list[str] = []

        if not self.is_gemini_configured:
            warnings.append(
                "GEMINI_API_KEY is not set. AI agent features (Planner, Analyst, "
                "Fact Checker, Report Writer) will not work. "
                "Get your key at: https://aistudio.google.com/apikey"
            )

        if not self.is_tavily_configured:
            warnings.append(
                "TAVILY_API_KEY is not set. Web research (Researcher Agent) will not work. "
                "Get your key at: https://tavily.com"
            )

        if not self.jwt_secret_key:
            warnings.append(
                "JWT_SECRET_KEY is not set. User authentication will not work. "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        if self.app_env == "production" and self.debug:
            warnings.append(
                "DEBUG=true in a production environment. Set DEBUG=false in production."
            )

        if warnings:
            print("\n" + "=" * 60, file=sys.stderr)
            print("⚠  ResearchMind AI – Configuration Warnings", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            for i, w in enumerate(warnings, 1):
                print(f"\n  {i}. {w}", file=sys.stderr)
            print("\n" + "=" * 60 + "\n", file=sys.stderr)

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Using lru_cache means the .env file is only parsed once at startup.
    In tests, call get_settings.cache_clear() to reload settings.
    """
    return Settings()


# Module-level convenience alias used throughout the codebase:
#   from app.config import settings
settings: Settings = get_settings()

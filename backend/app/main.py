"""
ResearchMind AI – FastAPI Application Entry Point
==================================================
Creates and configures the FastAPI application instance.

This module:
  - Creates the FastAPI app with metadata for Swagger UI
  - Configures CORS (Cross-Origin Resource Sharing)
  - Registers global exception handlers
  - Mounts all API routers
  - Adds the health check endpoint
  - Configures structured logging on startup
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.research import router as research_router
from app.config import settings
from app.schemas.common import ErrorResponse, HealthResponse
from app.utils.exceptions import ResearchMindError
from app.utils.logging import configure_logging, get_logger

# Configure logging before anything else runs
configure_logging(debug=settings.debug)
logger = get_logger(__name__)


# ─── Application Lifespan ─────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application startup and shutdown lifecycle handler.

    Startup: Log which services are configured and which are not.
    Shutdown: Clean up resources.
    """
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info(
        "app_starting",
        name=settings.app_name,
        environment=settings.app_env,
        version="0.1.0",
    )

    # Log service availability (without printing secret key values)
    service_status = {
        "gemini": "✓ configured" if settings.is_gemini_configured else "✗ GEMINI_API_KEY missing",
        "tavily": "✓ configured" if settings.is_tavily_configured else "✗ TAVILY_API_KEY missing",
        "database": "✓ URL set" if settings.is_database_configured else "✗ DATABASE_URL not configured",
        "qdrant": "✓ URL set" if settings.is_qdrant_configured else "✗ QDRANT_URL missing",
        "auth": "✓ JWT configured" if settings.jwt_secret_key else "✗ JWT_SECRET_KEY missing",
    }

    logger.info("service_availability", **service_status)

    yield  # Application runs here

    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info("app_shutting_down")


# ─── FastAPI App Instance ─────────────────────────────────────────────────────


app = FastAPI(
    title="ResearchMind AI API",
    description=(
        "Autonomous Multi-Agent Research and Intelligence Platform.\n\n"
        "ResearchMind AI orchestrates specialized AI agents to conduct structured "
        "internet research, analyze findings, verify facts, and generate "
        "comprehensive research reports.\n\n"
        "**Phase 1+2**: Planner Agent + Research Plan Generation\n"
        "**Phase 3**: Researcher, Analyst, Fact Checker, Report Writer\n"
        "**Phase 4**: LangGraph multi-agent workflow\n"
        "**Phase 5**: RAG document research\n"
        "**Phase 6**: Full persistence, auth, and streaming"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─── CORS Middleware ──────────────────────────────────────────────────────────


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request ID Middleware ────────────────────────────────────────────────────


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Attach a unique request ID to every HTTP request.

    The request ID is added to the response headers and can be
    used to correlate logs when debugging issues.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

    logger.debug(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(process_time, 2),
        request_id=request_id,
    )

    return response


# ─── Global Exception Handlers ───────────────────────────────────────────────


@app.exception_handler(ResearchMindError)
async def researchmind_exception_handler(request: Request, exc: ResearchMindError) -> JSONResponse:
    """
    Handle all ResearchMind application errors and return structured JSON.

    This ensures every error from our custom exception hierarchy
    returns a consistent response format.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "application_error",
        error_code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Logs the full exception but returns a safe, generic message to the client.
    Never expose internal error details to the client in production.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled_exception",
        error=str(exc),
        request_id=request_id,
    )

    message = str(exc) if settings.debug else "An unexpected error occurred. Please try again."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message=message,
            request_id=request_id,
        ).model_dump(),
    )


# ─── API Routers ──────────────────────────────────────────────────────────────


# All routers are mounted under /api for clear separation
API_PREFIX = "/api"

app.include_router(research_router, prefix=API_PREFIX)

# Future routers (will be added in later phases):
# app.include_router(auth_router, prefix=API_PREFIX)
# app.include_router(documents_router, prefix=API_PREFIX)
# app.include_router(reports_router, prefix=API_PREFIX)
# app.include_router(analytics_router, prefix=API_PREFIX)


# ─── Health Check ─────────────────────────────────────────────────────────────


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health Check",
    description="Returns the current health status of the API and connected services.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the application status and which services are available.
    Used by load balancers, Docker health checks, and monitoring systems.

    Does NOT make live connections to external services — only checks
    whether credentials are configured.
    """
    services = {
        "gemini": "configured" if settings.is_gemini_configured else "unconfigured",
        "tavily": "configured" if settings.is_tavily_configured else "unconfigured",
        "database": "url_set" if settings.is_database_configured else "unconfigured",
        "qdrant": "url_set" if settings.is_qdrant_configured else "unconfigured",
        "langsmith": "enabled" if settings.is_langsmith_configured else "disabled",
    }

    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.app_env,
        services=services,
    )


@app.get("/", tags=["Root"], summary="Root", include_in_schema=False)
async def root() -> dict:
    """Redirect hint for the root path."""
    return {
        "message": "ResearchMind AI API",
        "docs": "/docs",
        "health": "/api/health",
        "version": "0.1.0",
    }

"""
ResearchMind AI – Database Session
=====================================
Async SQLAlchemy session factory and FastAPI dependency.

Provides:
  - Async engine creation
  - AsyncSession factory
  - `get_db` FastAPI dependency for dependency injection
  - `create_all_tables` utility for development
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────

_engine = None
_session_factory = None


def _get_engine():
    """Lazy-create the async database engine."""
    global _engine
    if _engine is None:
        if not settings.is_database_configured:
            raise RuntimeError(
                "DATABASE_URL is not configured. "
                "Please set DATABASE_URL in your .env file."
            )
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,          # Log SQL in debug mode
            pool_pre_ping=True,           # Verify connections before use
            pool_size=10,
            max_overflow=20,
        )
        logger.info("database_engine_created")
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazy-create the async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = _get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects accessible after commit
        )
        logger.info("session_factory_created")
    return _session_factory


# ── FastAPI Dependency ─────────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Usage in route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically committed on success and rolled back on error.
    """
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Table Creation (Development Only) ─────────────────────────────────────────


async def create_all_tables() -> None:
    """
    Create all database tables.

    Use for development only. In production, use Alembic migrations.
    """
    from app.database.models import Base  # Import here to avoid circular imports

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")


async def drop_all_tables() -> None:
    """
    Drop all database tables (DESTRUCTIVE — test environments only).
    """
    from app.database.models import Base

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("database_tables_dropped")

"""
ResearchMind AI – Research Service Layer
==========================================
Business logic for creating, running, and querying research jobs.

This service layer sits between the API routes and the database/agent layer.
API routes should call this service; they should NOT directly query the database.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AgentExecutionLog,
    ResearchPlanDB,
    ResearchProject,
    ResearchReportDB,
    ResearchSourceDB,
)
from app.graph.workflow import run_research_workflow
from app.graph.state import ResearchWorkflowState
from app.schemas.research import (
    ResearchDepth,
    ResearchMode,
    ResearchPlan,
    ResearchRequest,
    ResearchStatus,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ── Create and start research ──────────────────────────────────────────────────


async def create_research_project(
    db: AsyncSession,
    request: ResearchRequest,
    user_id: str,
) -> ResearchProject:
    """
    Create a new ResearchProject in the database and return it.

    The workflow is NOT started here — use start_research_workflow() after approval.

    Args:
        db: Database session.
        request: The user's research request.
        user_id: ID of the requesting user.

    Returns:
        The newly created ResearchProject ORM object.
    """
    research_id = str(uuid.uuid4())

    project = ResearchProject(
        id=research_id,
        user_id=user_id,
        topic=request.topic,
        depth=request.depth.value,
        mode=request.mode.value,
        language=request.language,
        status=ResearchStatus.PLANNING.value,
        plan_approved=False,
        workflow_events=[],
    )
    db.add(project)
    await db.flush()

    logger.info("research_project_created", research_id=research_id, user_id=user_id)
    return project


async def save_research_plan(
    db: AsyncSession,
    project: ResearchProject,
    plan: ResearchPlan,
) -> ResearchPlanDB:
    """
    Persist a research plan to the database.

    Args:
        db: Database session.
        project: The parent ResearchProject.
        plan: The Pydantic ResearchPlan from the Planner Agent.

    Returns:
        The created ResearchPlanDB ORM object.
    """
    # Serialize questions as JSON-compatible list
    questions_json = [q.model_dump(mode="json") for q in plan.research_questions]

    plan_db = ResearchPlanDB(
        project_id=project.id,
        plan_id=plan.plan_id,
        scope_and_objectives=plan.scope_and_objectives,
        information_categories=plan.information_categories,
        research_questions=questions_json,
        estimated_duration_minutes=plan.estimated_duration_minutes,
    )
    db.add(plan_db)

    # Update project status
    project.status = ResearchStatus.AWAITING_APPROVAL.value
    await db.flush()

    logger.info("research_plan_saved", project_id=project.id, plan_id=plan.plan_id)
    return plan_db


async def approve_research_plan(
    db: AsyncSession,
    project: ResearchProject,
) -> None:
    """Mark a research project's plan as approved."""
    project.plan_approved = True
    project.status = ResearchStatus.RESEARCHING.value
    project.started_at = datetime.now(timezone.utc)
    await db.flush()
    logger.info("research_plan_approved", project_id=project.id)


async def start_research_workflow_background(
    research_id: str,
    request: ResearchRequest,
    user_id: str,
    db_url: str,
) -> None:
    """
    Run the full research workflow in the background (called via asyncio.create_task).

    This function creates its own database session because it runs outside
    the original request context.

    Args:
        research_id: The research project ID.
        request: The user's research request.
        user_id: User ID for ownership.
        db_url: Database URL for creating a new session.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    logger.info("background_workflow_starting", research_id=research_id)

    engine = create_async_engine(db_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        final_state = await run_research_workflow(research_id=research_id, request=request)
        await _persist_workflow_results(factory, research_id, final_state)
    except Exception as e:
        logger.exception("background_workflow_failed", research_id=research_id, error=str(e))
        async with factory() as db:
            async with db.begin():
                result = await db.execute(
                    select(ResearchProject).where(ResearchProject.id == research_id)
                )
                project = result.scalar_one_or_none()
                if project:
                    project.status = ResearchStatus.FAILED.value
                    project.error_message = str(e)
                    project.completed_at = datetime.now(timezone.utc)
    finally:
        await engine.dispose()


async def _persist_workflow_results(
    factory,
    research_id: str,
    final_state: ResearchWorkflowState,
) -> None:
    """Persist the completed workflow state to the database."""
    async with factory() as db:
        async with db.begin():
            result = await db.execute(
                select(ResearchProject).where(ResearchProject.id == research_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                logger.error("project_not_found_for_persistence", research_id=research_id)
                return

            # Update project
            sources = final_state.get("sources", [])
            analysis = final_state.get("analysis")
            verified_claims = final_state.get("verified_claims", [])
            report = final_state.get("report")
            pdf_bytes = final_state.get("pdf_bytes", b"")
            status = final_state.get("status", ResearchStatus.FAILED)
            events = final_state.get("workflow_events", [])

            project.status = status.value if hasattr(status, "value") else str(status)
            project.source_count = len(sources)
            project.finding_count = len(analysis.findings) if analysis else 0
            project.claim_count = len(verified_claims)
            project.has_report = report is not None
            project.retry_count = final_state.get("retry_count", 0)
            project.workflow_events = [dict(e) for e in events]
            project.completed_at = datetime.now(timezone.utc)

            errors = final_state.get("errors", [])
            if errors:
                project.error_message = "; ".join(errors[:3])

            # Persist sources
            for src in sources:
                src_db = ResearchSourceDB(
                    project_id=research_id,
                    source_id=src.source_id,
                    question_id=src.question_id,
                    title=src.title,
                    url=src.url,
                    domain=src.domain,
                    excerpt=src.excerpt[:2000] if src.excerpt else "",
                    published_date=src.published_date,
                    relevance_score=src.relevance_score,
                    is_duplicate=src.is_duplicate,
                    retrieved_at=src.retrieved_at,
                )
                db.add(src_db)

            # Persist report
            if report:
                claims_json = [c.model_dump(mode="json") for c in report.verified_claims]
                report_db = ResearchReportDB(
                    project_id=research_id,
                    report_id=report.report_id,
                    title=report.title,
                    executive_summary=report.executive_summary,
                    objectives=report.objectives,
                    methodology=report.methodology,
                    key_findings=report.key_findings,
                    detailed_analysis=report.detailed_analysis,
                    industry_trends=report.industry_trends,
                    opportunities=report.opportunities,
                    risks_and_challenges=report.risks_and_challenges,
                    verified_claims=claims_json,
                    uncertain_findings=report.uncertain_findings,
                    limitations=report.limitations,
                    conclusion=report.conclusion,
                    word_count=report.word_count,
                    language=report.language,
                )
                db.add(report_db)

                # Save PDF to filesystem
                if pdf_bytes:
                    import os
                    pdf_dir = "uploads/reports"
                    os.makedirs(pdf_dir, exist_ok=True)
                    pdf_path = f"{pdf_dir}/{research_id}.pdf"
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_bytes)
                    report_db.pdf_path = pdf_path

    logger.info("workflow_results_persisted", research_id=research_id)


# ── Query functions ────────────────────────────────────────────────────────────


async def get_project_by_id(
    db: AsyncSession,
    research_id: str,
    user_id: str,
) -> ResearchProject | None:
    """Get a research project by ID, enforcing user ownership."""
    result = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == research_id,
            ResearchProject.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_user_projects(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ResearchProject], int]:
    """
    List a user's research projects with pagination.

    Returns:
        Tuple of (projects, total_count).
    """
    offset = (page - 1) * page_size

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(ResearchProject).where(
            ResearchProject.user_id == user_id
        )
    )
    total = count_result.scalar_one()

    # Fetch
    result = await db.execute(
        select(ResearchProject)
        .where(ResearchProject.user_id == user_id)
        .order_by(ResearchProject.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    projects = list(result.scalars().all())

    return projects, total


async def get_analytics_overview(
    db: AsyncSession,
    user_id: str,
) -> dict:
    """
    Get analytics overview for a user.

    Returns real data from the database.
    """
    # Total projects
    total_result = await db.execute(
        select(func.count()).select_from(ResearchProject).where(
            ResearchProject.user_id == user_id
        )
    )
    total = total_result.scalar_one()

    # By status
    completed_result = await db.execute(
        select(func.count()).select_from(ResearchProject).where(
            ResearchProject.user_id == user_id,
            ResearchProject.status == "completed",
        )
    )
    completed = completed_result.scalar_one()

    failed_result = await db.execute(
        select(func.count()).select_from(ResearchProject).where(
            ResearchProject.user_id == user_id,
            ResearchProject.status == "failed",
        )
    )
    failed = failed_result.scalar_one()

    # Total sources
    sources_result = await db.execute(
        select(func.sum(ResearchProject.source_count)).where(
            ResearchProject.user_id == user_id
        )
    )
    total_sources = sources_result.scalar_one() or 0

    return {
        "total_projects": total,
        "completed": completed,
        "failed": failed,
        "in_progress": total - completed - failed,
        "total_sources_collected": int(total_sources),
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
    }

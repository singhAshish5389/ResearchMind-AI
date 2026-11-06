"""
ResearchMind AI – Research API Router (Full Implementation)
=============================================================
FastAPI router for all research lifecycle endpoints.

Endpoints:
  POST /api/research/plan                   – Generate research plan (Planner Agent)
  POST /api/research                        – Start a research job (background)
  GET  /api/research                        – List user's research jobs
  GET  /api/research/{id}                   – Get research job details
  GET  /api/research/{id}/status            – Get current status + events
  GET  /api/research/{id}/plan              – Get the research plan
  POST /api/research/{id}/approve-plan      – Approve the plan and start research
  GET  /api/research/{id}/report            – Get the finished report
  GET  /api/research/{id}/sources           – Get collected sources
  DELETE /api/research/{id}                 – Delete a research job
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.planner import PlannerAgent
from app.auth.dependencies import get_current_active_user
from app.config import settings
from app.database.models import ResearchProject, ResearchPlanDB, ResearchSourceDB, ResearchReportDB, User
from app.database.session import get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.research import (
    PlanResponse,
    ResearchJobSummary,
    ResearchPlan,
    ResearchQuestion,
    ResearchRequest,
    ResearchStatus,
)
from app.services.research_service import (
    approve_research_plan,
    create_research_project,
    get_project_by_id,
    list_user_projects,
    save_research_plan,
    start_research_workflow_background,
)
from app.utils.exceptions import ConfigurationError, GeminiError, LLMOutputParseError, PlannerError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/research", tags=["Research"])


# ─── POST /research/plan ──────────────────────────────────────────────────────


@router.post(
    "/plan",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Research Plan",
    description=(
        "Submit a research topic to the Planner Agent. "
        "Returns a structured plan with research questions and search queries. "
        "Requires GEMINI_API_KEY."
    ),
)
async def generate_research_plan(
    request: ResearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """Generate a research plan and persist the project."""
    research_id = str(uuid.uuid4())

    logger.info(
        "research_plan_requested",
        research_id=research_id,
        topic=request.topic[:100],
        user_id=current_user.id,
    )

    # Create DB record
    project = await create_research_project(db=db, request=request, user_id=current_user.id)
    research_id = project.id  # Use DB-generated ID

    try:
        agent = PlannerAgent()
        plan = await agent.create_plan(request)
    except ConfigurationError as e:
        raise HTTPException(status_code=503, detail={"error_code": e.code, "message": e.message})
    except GeminiError as e:
        raise HTTPException(status_code=502, detail={"error_code": e.code, "message": e.message})
    except (PlannerError, LLMOutputParseError) as e:
        raise HTTPException(status_code=500, detail={"error_code": e.code, "message": e.message})
    except Exception as e:
        logger.exception("planner_unexpected_error", research_id=research_id)
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": str(e)})

    # Persist plan
    await save_research_plan(db=db, project=project, plan=plan)

    logger.info("research_plan_created", research_id=research_id, question_count=len(plan.research_questions))

    return PlanResponse(
        research_id=research_id,
        plan=plan,
        message=(
            f"Research plan created with {len(plan.research_questions)} questions. "
            "Review and approve to begin research."
        ),
    )


# ─── POST /research/{id}/approve-plan ────────────────────────────────────────


@router.post(
    "/{research_id}/approve-plan",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Approve Research Plan",
    description="Approve a research plan and start the full research workflow in the background.",
)
async def approve_plan(
    research_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve the plan and start background research execution."""
    project = await get_project_by_id(db=db, research_id=research_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")

    if project.status not in [ResearchStatus.AWAITING_APPROVAL.value, ResearchStatus.PLANNING.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve plan in status '{project.status}'. Expected 'awaiting_approval'.",
        )

    await approve_research_plan(db=db, project=project)

    # Reconstruct the original request from the saved project
    request = ResearchRequest(
        topic=project.topic,
        depth=project.depth,
        mode=project.mode,
        language=project.language,
    )

    # Start background research
    background_tasks.add_task(
        start_research_workflow_background,
        research_id=research_id,
        request=request,
        user_id=current_user.id,
        db_url=settings.database_url,
    )

    logger.info("research_workflow_started", research_id=research_id, user_id=current_user.id)

    return {
        "research_id": research_id,
        "status": "researching",
        "message": "Research started. Poll /status for progress updates.",
    }


# ─── GET /research ────────────────────────────────────────────────────────────


@router.get(
    "",
    summary="List Research Jobs",
    description="List all research projects for the authenticated user.",
)
async def list_research_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List the user's research projects with pagination."""
    projects, total = await list_user_projects(
        db=db, user_id=current_user.id, page=page, page_size=page_size
    )

    return {
        "data": [
            {
                "research_id": p.id,
                "topic": p.topic,
                "status": p.status,
                "depth": p.depth,
                "mode": p.mode,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                "source_count": p.source_count,
                "has_report": p.has_report,
            }
            for p in projects
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─── GET /research/{id} ───────────────────────────────────────────────────────


@router.get(
    "/{research_id}",
    summary="Get Research Job",
    description="Get full details of a specific research project.",
)
async def get_research_job(
    research_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a research project by ID."""
    project = await get_project_by_id(db=db, research_id=research_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")

    return {
        "research_id": project.id,
        "topic": project.topic,
        "status": project.status,
        "depth": project.depth,
        "mode": project.mode,
        "language": project.language,
        "plan_approved": project.plan_approved,
        "has_report": project.has_report,
        "source_count": project.source_count,
        "finding_count": project.finding_count,
        "claim_count": project.claim_count,
        "retry_count": project.retry_count,
        "error_message": project.error_message,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "started_at": project.started_at.isoformat() if project.started_at else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
    }


# ─── GET /research/{id}/status ───────────────────────────────────────────────


@router.get(
    "/{research_id}/status",
    summary="Get Research Status",
    description="Get the current status and workflow progress events.",
)
async def get_research_status(
    research_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get real-time status and progress events."""
    project = await get_project_by_id(db=db, research_id=research_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")

    return {
        "research_id": research_id,
        "status": project.status,
        "source_count": project.source_count,
        "finding_count": project.finding_count,
        "claim_count": project.claim_count,
        "retry_count": project.retry_count,
        "error_message": project.error_message,
        "workflow_events": project.workflow_events or [],
        "has_report": project.has_report,
    }


# ─── GET /research/{id}/plan ─────────────────────────────────────────────────


@router.get(
    "/{research_id}/plan",
    summary="Get Research Plan",
    description="Get the research plan for a specific project.",
)
async def get_research_plan(
    research_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the persisted research plan."""
    project = await get_project_by_id(db=db, research_id=research_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")

    result = await db.execute(
        select(ResearchPlanDB).where(ResearchPlanDB.project_id == research_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Research plan not found.")

    return {
        "research_id": research_id,
        "plan_id": plan.plan_id,
        "topic": project.topic,
        "scope_and_objectives": plan.scope_and_objectives,
        "information_categories": plan.information_categories,
        "research_questions": plan.research_questions,
        "estimated_duration_minutes": plan.estimated_duration_minutes,
        "plan_approved": project.plan_approved,
        "status": project.status,
    }


# ─── GET /research/{id}/sources ──────────────────────────────────────────────


@router.get(
    "/{research_id}/sources",
    summary="Get Research Sources",
    description="Get all sources collected during the research.",
)
async def get_research_sources(
    research_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get sources collected for a research project."""
    project = await get_project_by_id(db=db, research_id=research_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")

    result = await db.execute(
        select(ResearchSourceDB)
        .where(ResearchSourceDB.project_id == research_id)
        .order_by(ResearchSourceDB.retrieved_at)
    )
    sources = result.scalars().all()

    return {
        "research_id": research_id,
        "source_count": len(sources),
        "sources": [
            {
                "source_id": s.source_id,
                "question_id": s.question_id,
                "title": s.title,
                "url": s.url,
                "domain": s.domain,
                "excerpt": s.excerpt[:300] if s.excerpt else "",
                "published_date": s.published_date,
                "relevance_score": s.relevance_score,
                "retrieved_at": s.retrieved_at.isoformat() if s.retrieved_at else None,
            }
            for s in sources
        ],
    }


# ─── GET /research/{id}/report ───────────────────────────────────────────────


@router.get(
    "/{research_id}/report",
    summary="Get Research Report",
    description="Get the final research report for a completed project.",
)
async def get_research_report(
    research_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the report for a completed research job."""
    project = await get_project_by_id(db=db, research_id=research_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")

    if not project.has_report:
        raise HTTPException(
            status_code=404,
            detail=f"Report not ready. Current status: {project.status}",
        )

    result = await db.execute(
        select(ResearchReportDB).where(ResearchReportDB.project_id == research_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report record not found.")

    import os
    return {
        "report_id": report.id,
        "research_id": research_id,
        "title": report.title,
        "executive_summary": report.executive_summary,
        "objectives": report.objectives,
        "methodology": report.methodology,
        "key_findings": report.key_findings,
        "detailed_analysis": report.detailed_analysis,
        "industry_trends": report.industry_trends,
        "opportunities": report.opportunities,
        "risks_and_challenges": report.risks_and_challenges,
        "verified_claims": report.verified_claims,
        "uncertain_findings": report.uncertain_findings,
        "limitations": report.limitations,
        "conclusion": report.conclusion,
        "word_count": report.word_count,
        "language": report.language,
        "has_pdf": bool(report.pdf_path and os.path.exists(report.pdf_path)),
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


# ─── DELETE /research/{id} ───────────────────────────────────────────────────


@router.delete(
    "/{research_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Research Job",
    description="Delete a research project and all its data.",
)
async def delete_research_job(
    research_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a research project (cascade deletes all related data)."""
    project = await get_project_by_id(db=db, research_id=research_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")

    await db.delete(project)
    logger.info("research_project_deleted", research_id=research_id, user_id=current_user.id)

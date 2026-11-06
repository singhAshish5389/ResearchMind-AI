"""
ResearchMind AI – Reports API Router
=======================================
Report retrieval and PDF export endpoints.

Endpoints:
  GET /api/reports                  – List user's reports
  GET /api/reports/{report_id}      – Get a specific report
  GET /api/reports/{report_id}/export – Download PDF
"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.models import ResearchProject, ResearchReportDB, User
from app.database.session import get_db
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportSummary(BaseModel):
    """Brief report info for listing."""
    id: str
    project_id: str
    title: str
    word_count: int
    language: str
    has_pdf: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReportDetail(BaseModel):
    """Full report content."""
    id: str
    project_id: str
    report_id: str
    title: str
    executive_summary: str
    objectives: str
    methodology: str
    key_findings: list
    detailed_analysis: str
    industry_trends: list
    opportunities: list
    risks_and_challenges: list
    verified_claims: list
    uncertain_findings: list
    limitations: str
    conclusion: str
    word_count: int
    language: str
    has_pdf: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get(
    "",
    response_model=list[ReportSummary],
    summary="List Reports",
    description="List all completed research reports for the current user.",
)
async def list_reports(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReportSummary]:
    """List reports for the authenticated user."""
    # Join reports with projects to enforce user ownership
    result = await db.execute(
        select(ResearchReportDB)
        .join(ResearchProject, ResearchReportDB.project_id == ResearchProject.id)
        .where(ResearchProject.user_id == current_user.id)
        .order_by(ResearchReportDB.created_at.desc())
    )
    reports = result.scalars().all()

    summaries = []
    for r in reports:
        summaries.append(ReportSummary(
            id=r.id,
            project_id=r.project_id,
            title=r.title,
            word_count=r.word_count,
            language=r.language,
            has_pdf=bool(r.pdf_path and os.path.exists(r.pdf_path)),
            created_at=r.created_at,
        ))

    return summaries


@router.get(
    "/{report_id}",
    response_model=ReportDetail,
    summary="Get Report",
    description="Get the full content of a research report.",
)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ReportDetail:
    """Get a specific report by ID."""
    result = await db.execute(
        select(ResearchReportDB)
        .join(ResearchProject, ResearchReportDB.project_id == ResearchProject.id)
        .where(
            ResearchReportDB.id == report_id,
            ResearchProject.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    return ReportDetail(
        id=report.id,
        project_id=report.project_id,
        report_id=report.report_id,
        title=report.title,
        executive_summary=report.executive_summary,
        objectives=report.objectives,
        methodology=report.methodology,
        key_findings=report.key_findings or [],
        detailed_analysis=report.detailed_analysis,
        industry_trends=report.industry_trends or [],
        opportunities=report.opportunities or [],
        risks_and_challenges=report.risks_and_challenges or [],
        verified_claims=report.verified_claims or [],
        uncertain_findings=report.uncertain_findings or [],
        limitations=report.limitations,
        conclusion=report.conclusion,
        word_count=report.word_count,
        language=report.language,
        has_pdf=bool(report.pdf_path and os.path.exists(report.pdf_path)),
        created_at=report.created_at,
    )


@router.get(
    "/{report_id}/export",
    summary="Download Report PDF",
    description="Download the PDF version of a research report.",
    response_class=FileResponse,
)
async def export_report_pdf(
    report_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the PDF for a specific report."""
    result = await db.execute(
        select(ResearchReportDB)
        .join(ResearchProject, ResearchReportDB.project_id == ResearchProject.id)
        .where(
            ResearchReportDB.id == report_id,
            ResearchProject.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    if not report.pdf_path or not os.path.exists(report.pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this report.",
        )

    safe_title = "".join(c for c in report.title[:50] if c.isalnum() or c in " _-").strip()
    filename = f"ResearchMind_{safe_title}.pdf".replace(" ", "_")

    return FileResponse(
        path=report.pdf_path,
        media_type="application/pdf",
        filename=filename,
    )

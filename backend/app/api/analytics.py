"""
ResearchMind AI – Analytics API Router
=========================================
Analytics and usage statistics for the user dashboard.

Endpoints:
  GET /api/analytics/overview  – Summary stats for dashboard
  GET /api/analytics/usage     – Research activity over time
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.models import ResearchProject, User
from app.database.session import get_db
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    summary="Analytics Overview",
    description="Get summary statistics for the current user's research activity.",
)
async def get_analytics_overview(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get analytics overview for the current user."""
    from app.services.research_service import get_analytics_overview
    return await get_analytics_overview(db=db, user_id=current_user.id)


@router.get(
    "/usage",
    summary="Usage Over Time",
    description="Get research activity counts over the last 30 days.",
)
async def get_usage_over_time(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return daily research counts for the last 30 days."""
    # Fetch all projects in last 30 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    result = await db.execute(
        select(ResearchProject.created_at, ResearchProject.status)
        .where(
            ResearchProject.user_id == current_user.id,
            ResearchProject.created_at >= cutoff,
        )
        .order_by(ResearchProject.created_at)
    )
    rows = result.all()

    # Group by date
    daily: dict[str, dict] = {}
    for created_at, status in rows:
        day = created_at.strftime("%Y-%m-%d") if created_at else "unknown"
        if day not in daily:
            daily[day] = {"date": day, "total": 0, "completed": 0, "failed": 0}
        daily[day]["total"] += 1
        if status == "completed":
            daily[day]["completed"] += 1
        elif status == "failed":
            daily[day]["failed"] += 1

    # Sort by date
    usage_data = sorted(daily.values(), key=lambda x: x["date"])

    return {
        "period_days": 30,
        "data": usage_data,
    }

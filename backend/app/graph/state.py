"""
ResearchMind AI – LangGraph Workflow State
==========================================
Defines the shared TypedDict state object that flows through
all nodes in the LangGraph StateGraph.

All agents read from and write to this shared state.
LangGraph merges state updates from each node automatically.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.schemas.research import (
    ResearchAnalysis,
    ResearchPlan,
    ResearchReport,
    ResearchRequest,
    ResearchStatus,
    ResearchSource,
    VerifiedClaim,
)


class WorkflowEvent(TypedDict):
    """A single workflow progress event for real-time UI updates."""
    timestamp: str          # ISO format
    agent: str              # Agent name: "planner", "researcher", etc.
    stage: str              # Stage name matching ResearchStatus
    message: str            # Human-readable progress message
    details: dict[str, Any] # Extra data (source count, etc.)


class ResearchWorkflowState(TypedDict, total=False):
    """
    Shared state object for the ResearchMind AI LangGraph workflow.

    This TypedDict defines every field that can appear in the state.
    All fields are optional (total=False) so nodes only need to set
    fields they are responsible for.

    Lifecycle:
        1. User submits ResearchRequest → state initialized.
        2. Planner sets plan + status = AWAITING_APPROVAL.
        3. Approval sets plan_approved = True.
        4. Researcher fills sources.
        5. Analyst fills analysis.
        6. Fact Checker fills verified_claims + needs_more_research.
        7. Quality gate: if needs_more_research and retry_count < 2 → loop.
        8. Report Writer fills report + pdf_bytes.
        9. Final node persists everything and sets status = COMPLETED.
    """

    # ── Identity ────────────────────────────────────────────────────────────
    research_id: str
    """Unique ID for this research job (matches DB record)."""

    # ── Input ───────────────────────────────────────────────────────────────
    request: ResearchRequest
    """The original user research request."""

    # ── Planning ────────────────────────────────────────────────────────────
    plan: ResearchPlan | None
    """Structured research plan produced by the Planner Agent."""

    plan_approved: bool
    """True when the user has explicitly approved the research plan."""

    # ── Research ────────────────────────────────────────────────────────────
    sources: list[ResearchSource]
    """All sources collected by the Researcher Agent (deduplicated)."""

    # ── Analysis ────────────────────────────────────────────────────────────
    analysis: ResearchAnalysis | None
    """Structured analysis produced by the Analyst Agent."""

    # ── Fact Checking ───────────────────────────────────────────────────────
    verified_claims: list[VerifiedClaim]
    """Claims verified by the Fact Checker Agent."""

    needs_more_research: bool
    """True if the Fact Checker determined more evidence is needed."""

    research_gaps: list[str]
    """Specific gaps that require additional research (from Fact Checker)."""

    # ── Report ──────────────────────────────────────────────────────────────
    report: ResearchReport | None
    """Final research report produced by the Report Writer Agent."""

    pdf_bytes: bytes | None
    """Raw PDF bytes for download."""

    # ── Workflow Control ────────────────────────────────────────────────────
    status: ResearchStatus
    """Current workflow stage / status."""

    retry_count: int
    """Number of times we've looped back for additional research (max 2)."""

    errors: list[str]
    """Non-fatal errors that occurred during the workflow."""

    workflow_events: list[WorkflowEvent]
    """Ordered list of progress events for real-time UI updates."""

    # ── Persistence ─────────────────────────────────────────────────────────
    db_record_id: str | None
    """Database primary key for the research project (set after first DB write)."""


def initial_state(research_id: str, request: ResearchRequest) -> ResearchWorkflowState:
    """
    Create the initial workflow state for a new research job.

    Args:
        research_id: Unique ID for this research job.
        request: The user's validated research request.

    Returns:
        A fresh ResearchWorkflowState ready for the Planner node.
    """
    return ResearchWorkflowState(
        research_id=research_id,
        request=request,
        plan=None,
        plan_approved=False,
        sources=[],
        analysis=None,
        verified_claims=[],
        needs_more_research=False,
        research_gaps=[],
        report=None,
        pdf_bytes=None,
        status=ResearchStatus.PLANNING,
        retry_count=0,
        errors=[],
        workflow_events=[],
        db_record_id=None,
    )

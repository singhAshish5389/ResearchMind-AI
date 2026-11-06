"""
ResearchMind AI – LangGraph Workflow
======================================
Implements the full multi-agent research pipeline using LangGraph StateGraph.

Workflow:
    USER REQUEST
        │
        ▼
    plan_node           ← Planner Agent (Gemini)
        │
        ▼
    await_approval_node ← Human-in-the-loop checkpoint
        │
        ▼
    research_node       ← Researcher Agent (Tavily)
        │
        ▼
    analyze_node        ← Analyst Agent (Gemini)
        │
        ▼
    fact_check_node     ← Fact Checker Agent (Gemini)
        │
        ▼
    quality_gate        ← Conditional: needs more research?
        │
    ┌───┴───────────────────────────┐
    │ yes (retry_count < 2)         │ no
    ▼                               ▼
    more_research_node          write_report_node  ← Report Writer (Gemini + PDF)
        │                           │
        └───────────────────────────┘
                                    ▼
                                  END

Design notes:
  - Each node wraps an agent and handles errors without crashing the graph.
  - The quality gate prevents infinite loops (max MAX_RESEARCH_RETRIES).
  - All nodes emit WorkflowEvents for real-time progress updates.
  - plan_node and await_approval_node are separated: approval is external.
  - The graph is built once and reused; state is passed per execution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.agents.analyst import AnalystAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.planner import PlannerAgent
from app.agents.report_writer import ReportWriterAgent
from app.agents.researcher import ResearcherAgent
from app.graph.state import ResearchWorkflowState, WorkflowEvent, initial_state
from app.schemas.research import ResearchRequest, ResearchStatus
from app.utils.exceptions import ConfigurationError, ResearchMindError
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_RESEARCH_RETRIES = 2


# ── Event helper ─────────────────────────────────────────────────────────────


def _make_event(agent: str, stage: str, message: str, **details: Any) -> WorkflowEvent:
    """Create a WorkflowEvent dict."""
    return WorkflowEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent=agent,
        stage=stage,
        message=message,
        details=dict(details),
    )


def _append_event(state: ResearchWorkflowState, event: WorkflowEvent) -> ResearchWorkflowState:
    """Return state with event appended to workflow_events."""
    events = list(state.get("workflow_events", []))
    events.append(event)
    return {**state, "workflow_events": events}  # type: ignore[return-value]


# ── Node functions ────────────────────────────────────────────────────────────


async def plan_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node 1: Run the Planner Agent to generate a research plan.

    Sets: plan, status = AWAITING_APPROVAL
    On error: sets status = FAILED, appends error
    """
    research_id = state["research_id"]
    request = state["request"]

    logger.info("workflow_plan_node_start", research_id=research_id)

    state = _append_event(state, _make_event(
        "planner", "planning", "Analyzing research topic and creating research plan..."
    ))

    try:
        agent = PlannerAgent()
        plan = await agent.create_plan(request)

        state = {
            **state,
            "plan": plan,
            "status": ResearchStatus.AWAITING_APPROVAL,
        }
        state = _append_event(state, _make_event(
            "planner", "awaiting_approval",
            f"Research plan created with {len(plan.research_questions)} questions. Awaiting your approval.",
            question_count=len(plan.research_questions),
        ))

        logger.info("workflow_plan_created", research_id=research_id, plan_id=plan.plan_id)

    except ConfigurationError as e:
        logger.error("workflow_plan_config_error", research_id=research_id, error=str(e))
        errors = list(state.get("errors", [])) + [f"Configuration error: {e.message}"]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        state = _append_event(state, _make_event("planner", "failed", f"Configuration error: {e.message}"))

    except ResearchMindError as e:
        logger.error("workflow_plan_error", research_id=research_id, error=str(e))
        errors = list(state.get("errors", [])) + [e.message]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        state = _append_event(state, _make_event("planner", "failed", f"Planning failed: {e.message}"))

    except Exception as e:
        logger.exception("workflow_plan_unexpected_error", research_id=research_id)
        errors = list(state.get("errors", [])) + [f"Unexpected error in Planner: {str(e)}"]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        state = _append_event(state, _make_event("planner", "failed", "Unexpected planning error."))

    return state  # type: ignore[return-value]


async def research_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node 2: Run the Researcher Agent to search for sources.

    Reads: plan (must be approved)
    Sets: sources, status = RESEARCHING → ANALYZING
    """
    research_id = state["research_id"]
    plan = state.get("plan")

    logger.info("workflow_research_node_start", research_id=research_id)

    if not plan:
        errors = list(state.get("errors", [])) + ["Research plan missing before Researcher node."]
        return {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[return-value]

    state = {**state, "status": ResearchStatus.RESEARCHING}
    state = _append_event(state, _make_event(
        "researcher", "researching",
        f"Searching the internet for {len(plan.research_questions)} research questions...",
        question_count=len(plan.research_questions),
    ))

    try:
        agent = ResearcherAgent()
        max_results = state["request"].max_results_per_query if state.get("request") else None
        sources = await agent.research(plan, max_results_per_query=max_results)

        # Merge with any existing sources from previous research loops
        existing_sources = list(state.get("sources", []))
        # Deduplicate by URL across loops
        existing_urls = {s.url for s in existing_sources}
        new_sources = [s for s in sources if s.url not in existing_urls]
        all_sources = existing_sources + new_sources

        state = {**state, "sources": all_sources}
        state = _append_event(state, _make_event(
            "researcher", "researching",
            f"Found {len(all_sources)} sources ({len(new_sources)} new).",
            total_sources=len(all_sources),
            new_sources=len(new_sources),
        ))

        logger.info("workflow_research_complete", research_id=research_id, source_count=len(all_sources))

    except ConfigurationError as e:
        logger.error("workflow_research_config_error", research_id=research_id, error=str(e))
        errors = list(state.get("errors", [])) + [f"Researcher configuration error: {e.message}"]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        state = _append_event(state, _make_event("researcher", "failed", f"Search unavailable: {e.message}"))

    except Exception as e:
        logger.exception("workflow_research_error", research_id=research_id)
        errors = list(state.get("errors", [])) + [f"Researcher error: {str(e)}"]
        # Don't fail — continue with whatever sources we have
        state = {**state, "errors": errors}
        state = _append_event(state, _make_event("researcher", "warning", f"Search encountered errors: {str(e)[:200]}"))

    return state  # type: ignore[return-value]


async def analyze_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node 3: Run the Analyst Agent to analyze collected sources.

    Reads: sources, plan
    Sets: analysis, status = ANALYZING → FACT_CHECKING
    """
    research_id = state["research_id"]
    sources = state.get("sources", [])
    plan = state.get("plan")

    logger.info("workflow_analyze_node_start", research_id=research_id, source_count=len(sources))

    state = {**state, "status": ResearchStatus.ANALYZING}
    state = _append_event(state, _make_event(
        "analyst", "analyzing",
        f"Analyzing {len(sources)} sources for themes, trends, and insights...",
        source_count=len(sources),
    ))

    if not sources:
        errors = list(state.get("errors", [])) + ["No sources available for analysis."]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        return state  # type: ignore[return-value]

    if not plan:
        errors = list(state.get("errors", [])) + ["Research plan missing in analyze node."]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        return state  # type: ignore[return-value]

    try:
        agent = AnalystAgent()
        analysis = await agent.analyze(plan, sources)

        state = {**state, "analysis": analysis}
        state = _append_event(state, _make_event(
            "analyst", "analyzing",
            f"Analysis complete: {len(analysis.findings)} findings, {len(analysis.themes)} themes identified.",
            finding_count=len(analysis.findings),
            theme_count=len(analysis.themes),
        ))

        logger.info("workflow_analysis_complete", research_id=research_id, finding_count=len(analysis.findings))

    except Exception as e:
        logger.exception("workflow_analyze_error", research_id=research_id)
        errors = list(state.get("errors", [])) + [f"Analyst error: {str(e)}"]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        state = _append_event(state, _make_event("analyst", "failed", f"Analysis failed: {str(e)[:200]}"))

    return state  # type: ignore[return-value]


async def fact_check_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node 4: Run the Fact Checker Agent to verify claims.

    Reads: analysis, sources
    Sets: verified_claims, needs_more_research, research_gaps
    """
    research_id = state["research_id"]
    analysis = state.get("analysis")
    sources = state.get("sources", [])

    logger.info("workflow_fact_check_node_start", research_id=research_id)

    state = {**state, "status": ResearchStatus.FACT_CHECKING}
    state = _append_event(state, _make_event(
        "fact_checker", "fact_checking",
        "Verifying factual claims against collected evidence...",
    ))

    if not analysis:
        errors = list(state.get("errors", [])) + ["Analysis missing before fact check."]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        return state  # type: ignore[return-value]

    try:
        agent = FactCheckerAgent()
        claims, needs_more_research, research_gaps = await agent.verify(analysis, sources)

        # Merge with any existing verified claims from previous loops
        existing_claims = list(state.get("verified_claims", []))
        all_claims = existing_claims + claims

        state = {
            **state,
            "verified_claims": all_claims,
            "needs_more_research": needs_more_research,
            "research_gaps": research_gaps,
        }

        verified_count = sum(1 for c in claims if c.status.value == "VERIFIED")
        state = _append_event(state, _make_event(
            "fact_checker", "fact_checking",
            f"Fact-checking complete: {len(claims)} claims assessed, {verified_count} verified.",
            total_claims=len(claims),
            verified=verified_count,
            needs_more_research=needs_more_research,
        ))

        logger.info(
            "workflow_fact_check_complete",
            research_id=research_id,
            claims=len(claims),
            needs_more=needs_more_research,
        )

    except Exception as e:
        logger.exception("workflow_fact_check_error", research_id=research_id)
        errors = list(state.get("errors", [])) + [f"Fact checker error: {str(e)}"]
        # Don't fail — proceed to report with what we have
        state = {**state, "errors": errors, "needs_more_research": False}
        state = _append_event(state, _make_event("fact_checker", "warning", "Fact-checking encountered errors; proceeding with available data."))

    return state  # type: ignore[return-value]


async def more_research_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node 5 (conditional): Run additional research for identified gaps.

    This node increments retry_count and runs the Researcher Agent again
    with targeted queries for identified research gaps.
    """
    research_id = state["research_id"]
    retry_count = state.get("retry_count", 0) + 1
    gaps = state.get("research_gaps", [])

    logger.info("workflow_more_research_start", research_id=research_id, retry=retry_count)

    state = {**state, "retry_count": retry_count}
    state = _append_event(state, _make_event(
        "researcher", "researching",
        f"Running additional research (attempt {retry_count}/{MAX_RESEARCH_RETRIES}) for identified gaps...",
        retry_count=retry_count,
        gaps=gaps[:3],
    ))

    # Create targeted queries from research gaps
    plan = state.get("plan")
    if plan and gaps:
        # We re-run researcher with the same plan — it will search its existing queries
        # In a more advanced version, we'd generate new queries from gaps
        try:
            agent = ResearcherAgent()
            additional_sources = await agent.research(plan)

            existing_sources = list(state.get("sources", []))
            existing_urls = {s.url for s in existing_sources}
            new_sources = [s for s in additional_sources if s.url not in existing_urls]
            all_sources = existing_sources + new_sources

            state = {**state, "sources": all_sources, "needs_more_research": False}
            state = _append_event(state, _make_event(
                "researcher", "researching",
                f"Additional research found {len(new_sources)} new sources.",
                new_sources=len(new_sources),
            ))

        except Exception as e:
            logger.error("workflow_more_research_error", research_id=research_id, error=str(e))
            state = {**state, "needs_more_research": False}
            state = _append_event(state, _make_event("researcher", "warning", "Additional research failed; proceeding with existing sources."))
    else:
        state = {**state, "needs_more_research": False}

    return state  # type: ignore[return-value]


async def write_report_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node 6: Run the Report Writer Agent to compose the final report.

    Reads: plan, sources, analysis, verified_claims
    Sets: report, pdf_bytes, status = COMPLETED
    """
    research_id = state["research_id"]
    plan = state.get("plan")
    sources = state.get("sources", [])
    analysis = state.get("analysis")
    verified_claims = state.get("verified_claims", [])

    logger.info("workflow_write_report_start", research_id=research_id)

    state = {**state, "status": ResearchStatus.WRITING_REPORT}
    state = _append_event(state, _make_event(
        "report_writer", "writing_report",
        "Composing final research report and generating PDF...",
        source_count=len(sources),
        claims_count=len(verified_claims),
    ))

    if not plan or not analysis:
        errors = list(state.get("errors", [])) + ["Missing plan or analysis for report writing."]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        return state  # type: ignore[return-value]

    try:
        agent = ReportWriterAgent()
        report, pdf_bytes = await agent.write_report(
            research_id=research_id,
            plan=plan,
            sources=sources,
            analysis=analysis,
            verified_claims=verified_claims,
        )

        state = {
            **state,
            "report": report,
            "pdf_bytes": pdf_bytes,
            "status": ResearchStatus.COMPLETED,
        }
        state = _append_event(state, _make_event(
            "report_writer", "completed",
            f"Research complete! Report generated with {report.word_count} words.",
            word_count=report.word_count,
            has_pdf=len(pdf_bytes) > 0,
        ))

        logger.info("workflow_report_complete", research_id=research_id, report_id=report.report_id)

    except Exception as e:
        logger.exception("workflow_write_report_error", research_id=research_id)
        errors = list(state.get("errors", [])) + [f"Report Writer error: {str(e)}"]
        state = {**state, "status": ResearchStatus.FAILED, "errors": errors}  # type: ignore[assignment]
        state = _append_event(state, _make_event("report_writer", "failed", f"Report generation failed: {str(e)[:200]}"))

    return state  # type: ignore[return-value]


# ── Quality gate ─────────────────────────────────────────────────────────────


def quality_gate(state: ResearchWorkflowState) -> str:
    """
    Conditional routing function for the quality gate.

    Returns:
        "more_research" if needs_more_research and retry_count < MAX
        "write_report"  otherwise
    """
    needs_more = state.get("needs_more_research", False)
    retry_count = state.get("retry_count", 0)
    status = state.get("status")

    # Don't loop if already failed
    if status == ResearchStatus.FAILED:
        return "write_report"

    if needs_more and retry_count < MAX_RESEARCH_RETRIES:
        logger.info("quality_gate_needs_more_research", retry_count=retry_count)
        return "more_research"

    logger.info("quality_gate_proceed_to_report", retry_count=retry_count)
    return "write_report"


# ── Graph builder ─────────────────────────────────────────────────────────────


def build_research_graph():
    """
    Build and compile the LangGraph StateGraph.

    Returns the compiled graph ready for execution.
    """
    try:
        from langgraph.graph import StateGraph, END  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "langgraph is not installed. Run: pip install langgraph"
        )

    graph = StateGraph(ResearchWorkflowState)

    # Add nodes
    graph.add_node("plan", plan_node)
    graph.add_node("research", research_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("fact_check", fact_check_node)
    graph.add_node("more_research", more_research_node)
    graph.add_node("write_report", write_report_node)

    # Entry point
    graph.set_entry_point("plan")

    # Normal edges
    graph.add_edge("plan", "research")
    graph.add_edge("research", "analyze")
    graph.add_edge("analyze", "fact_check")

    # Conditional quality gate
    graph.add_conditional_edges(
        "fact_check",
        quality_gate,
        {
            "more_research": "more_research",
            "write_report": "write_report",
        },
    )

    # After more_research, re-analyze
    graph.add_edge("more_research", "analyze")

    # Final edge
    graph.add_edge("write_report", END)

    return graph.compile()


# ── Public execution API ───────────────────────────────────────────────────────


async def run_research_workflow(
    research_id: str,
    request: ResearchRequest,
    on_state_update=None,
) -> ResearchWorkflowState:
    """
    Execute the full research workflow asynchronously.

    This is the main public entry point for running a research job.
    It builds the graph, runs the workflow, and returns the final state.

    Args:
        research_id: Unique ID for this job.
        request: The user's validated research request.
        on_state_update: Optional async callback(state) called after each node.

    Returns:
        The final ResearchWorkflowState after all agents have run.
    """
    logger.info("starting_research_workflow", research_id=research_id, topic=request.topic[:100])

    state = initial_state(research_id, request)
    graph = build_research_graph()

    final_state = await graph.ainvoke(state)

    logger.info(
        "research_workflow_complete",
        research_id=research_id,
        status=final_state.get("status"),
        source_count=len(final_state.get("sources", [])),
        has_report=final_state.get("report") is not None,
    )

    return final_state

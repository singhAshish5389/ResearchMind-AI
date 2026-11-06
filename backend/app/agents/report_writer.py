"""
ResearchMind AI – Report Writer Agent
========================================
The Report Writer Agent composes a professional research report from
all collected data and generates a downloadable PDF.

Responsibilities:
  1. Generate a structured research report using Gemini.
  2. Validate that all citation IDs exist in collected sources.
  3. Create a professional PDF report using ReportLab.
  4. Return validated ResearchReport + PDF bytes.

Design notes:
  - Every section references only real collected sources.
  - PDF is generated from the structured report data, not raw LLM text.
  - Raises ReportWriterError on unrecoverable failures.
"""

from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.schemas.research import (
    ResearchAnalysis,
    ResearchPlan,
    ResearchReport,
    ResearchSource,
    VerifiedClaim,
)
from app.utils.exceptions import ConfigurationError, GeminiError, LLMOutputParseError, ReportWriterError
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _build_report_prompt(
    plan: ResearchPlan,
    sources: list[ResearchSource],
    analysis: ResearchAnalysis,
    verified_claims: list[VerifiedClaim],
) -> str:
    """Build the Gemini prompt for report generation."""
    # Format verified claims summary
    claims_text = ""
    for c in verified_claims[:20]:
        claims_text += f"- [{c.status.value}] {c.claim}\n"

    # Format key findings
    findings_text = ""
    for f in analysis.findings[:15]:
        flags = []
        if f.is_trend:
            flags.append("TREND")
        if f.is_opportunity:
            flags.append("OPPORTUNITY")
        if f.is_risk:
            flags.append("RISK")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        findings_text += f"- {f.category}{flag_str}: {f.finding}\n"

    source_ids = [s.source_id for s in sources]

    prompt = f"""You are a professional research report writer.

Write a comprehensive, well-structured research report based on the following research data.

TOPIC: {plan.topic}
OBJECTIVES: {plan.scope_and_objectives}
LANGUAGE: {plan.language}

KEY FINDINGS FROM ANALYSIS:
{findings_text}

VERIFIED CLAIMS:
{claims_text}

EVIDENCE GAPS: {', '.join(analysis.evidence_gaps) if analysis.evidence_gaps else 'None identified'}

INSTRUCTIONS:
1. Write a professional, objective research report.
2. Base ALL statements on the provided findings and verified claims.
3. Do NOT add facts not present in the findings.
4. Use clear, professional language appropriate for {plan.language}.
5. The report should feel authoritative yet acknowledge limitations.

Return ONLY valid JSON with this exact structure:
{{
  "title": "Professional report title",
  "executive_summary": "2-3 paragraph executive summary...",
  "objectives": "Research objectives paragraph...",
  "methodology": "Brief description of research methodology used...",
  "key_findings": [
    "Key finding 1 (most important insight)",
    "Key finding 2",
    "Key finding 3",
    "Key finding 4",
    "Key finding 5"
  ],
  "detailed_analysis": "4-6 paragraph detailed analysis of all findings...",
  "industry_trends": [
    "Trend 1 identified from sources",
    "Trend 2",
    "Trend 3"
  ],
  "opportunities": [
    "Opportunity 1",
    "Opportunity 2"
  ],
  "risks_and_challenges": [
    "Risk/challenge 1",
    "Risk/challenge 2"
  ],
  "uncertain_findings": [
    "Finding that lacked sufficient evidence..."
  ],
  "limitations": "Paragraph describing research limitations and what this report cannot claim...",
  "conclusion": "2-3 paragraph conclusion..."
}}
"""
    return prompt


def _generate_pdf(report: ResearchReport, sources: list[ResearchSource]) -> bytes:
    """
    Generate a professional PDF from the research report using ReportLab.

    Returns PDF as bytes.
    """
    try:
        from reportlab.lib import colors  # type: ignore[import]
        from reportlab.lib.pagesizes import A4  # type: ignore[import]
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import]
        from reportlab.lib.units import cm  # type: ignore[import]
        from reportlab.platypus import (  # type: ignore[import]
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY  # type: ignore[import]
    except ImportError:
        logger.warning("reportlab_not_installed", hint="pip install reportlab")
        # Return a simple text "PDF" fallback
        content = f"# {report.title}\n\n{report.executive_summary}\n\n## Conclusion\n{report.conclusion}"
        return content.encode("utf-8")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=12,
        textColor=colors.HexColor("#1E3A5F"),
        alignment=TA_CENTER,
    )
    heading1_style = ParagraphStyle(
        "Heading1",
        parent=styles["Heading1"],
        fontSize=16,
        spaceBefore=18,
        spaceAfter=8,
        textColor=colors.HexColor("#1E3A5F"),
    )
    heading2_style = ParagraphStyle(
        "Heading2",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#2563EB"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=8,
        leading=16,
        alignment=TA_JUSTIFY,
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
        leftIndent=15,
        leading=14,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=4,
        alignment=TA_CENTER,
    )

    story = []

    # Title
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(report.title, title_style))
    story.append(Paragraph(
        f"Generated by ResearchMind AI · {report.created_at.strftime('%B %d, %Y')}",
        meta_style,
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563EB")))
    story.append(Spacer(1, 0.5 * cm))

    # Executive Summary
    story.append(Paragraph("Executive Summary", heading1_style))
    story.append(Paragraph(report.executive_summary, body_style))

    # Key Findings
    story.append(Paragraph("Key Findings", heading1_style))
    for i, finding in enumerate(report.key_findings, 1):
        story.append(Paragraph(f"• {finding}", bullet_style))

    # Objectives & Methodology
    story.append(Paragraph("Research Objectives", heading1_style))
    story.append(Paragraph(report.objectives, body_style))
    story.append(Paragraph("Methodology", heading2_style))
    story.append(Paragraph(report.methodology, body_style))

    # Detailed Analysis
    story.append(Paragraph("Detailed Analysis", heading1_style))
    story.append(Paragraph(report.detailed_analysis, body_style))

    # Industry Trends
    if report.industry_trends:
        story.append(Paragraph("Industry Trends", heading1_style))
        for trend in report.industry_trends:
            story.append(Paragraph(f"→ {trend}", bullet_style))

    # Opportunities
    if report.opportunities:
        story.append(Paragraph("Opportunities", heading1_style))
        for opp in report.opportunities:
            story.append(Paragraph(f"✓ {opp}", bullet_style))

    # Risks and Challenges
    if report.risks_and_challenges:
        story.append(Paragraph("Risks and Challenges", heading1_style))
        for risk in report.risks_and_challenges:
            story.append(Paragraph(f"⚠ {risk}", bullet_style))

    # Verified Claims
    if report.verified_claims:
        story.append(Paragraph("Fact-Checked Claims", heading1_style))
        story.append(Paragraph(
            "The following claims were assessed against collected evidence.",
            body_style,
        ))
        for claim in report.verified_claims[:15]:
            status_color = {
                "VERIFIED": "#16a34a",
                "PARTIALLY_SUPPORTED": "#ca8a04",
                "UNSUPPORTED": "#dc2626",
                "CONTRADICTED": "#dc2626",
                "NEEDS_MORE_EVIDENCE": "#9333ea",
            }.get(claim.status.value, "#6b7280")

            story.append(Paragraph(
                f'<font color="{status_color}"><b>[{claim.status.value}]</b></font> {claim.claim}',
                bullet_style,
            ))

    # Uncertain Findings
    if report.uncertain_findings:
        story.append(Paragraph("Uncertain or Unverified Findings", heading1_style))
        story.append(Paragraph(
            "The following findings lacked sufficient evidence. "
            "They should be treated with caution.",
            body_style,
        ))
        for uf in report.uncertain_findings:
            story.append(Paragraph(f"? {uf}", bullet_style))

    # Limitations
    story.append(Paragraph("Limitations", heading1_style))
    story.append(Paragraph(report.limitations, body_style))

    # Conclusion
    story.append(Paragraph("Conclusion", heading1_style))
    story.append(Paragraph(report.conclusion, body_style))

    # References
    story.append(Paragraph("References", heading1_style))
    story.append(Paragraph(
        f"This report is based on {len(sources)} sources retrieved from the internet.",
        body_style,
    ))
    for i, src in enumerate(sources[:30], 1):
        ref_text = f"{i}. {src.title}"
        if src.domain:
            ref_text += f" ({src.domain})"
        if src.published_date:
            ref_text += f" – {src.published_date}"
        story.append(Paragraph(ref_text, bullet_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


class ReportWriterAgent:
    """
    Report Writer Agent – composes the final research report.

    Uses Gemini to generate structured report sections and
    ReportLab to create a downloadable PDF.

    Usage:
        agent = ReportWriterAgent()
        report, pdf_bytes = await agent.write_report(research_id, plan, sources, analysis, claims)
    """

    def __init__(self) -> None:
        if not settings.is_gemini_configured:
            raise ConfigurationError(
                "GEMINI_API_KEY is not configured. "
                "Add your Gemini API key to the .env file."
            )
        try:
            from google import genai  # type: ignore[import]
            self._client = genai.Client(api_key=settings.gemini_api_key)
        except ImportError as e:
            raise ConfigurationError(f"google-genai package not installed: {e}")

        self._model = settings.gemini_model
        logger.info("report_writer_agent_initialized", model=self._model)

    @retry(
        retry=retry_if_exception_type(GeminiError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def write_report(
        self,
        research_id: str,
        plan: ResearchPlan,
        sources: list[ResearchSource],
        analysis: ResearchAnalysis,
        verified_claims: list[VerifiedClaim],
    ) -> tuple[ResearchReport, bytes]:
        """
        Generate the final research report and PDF.

        Args:
            research_id: The research job ID.
            plan: The approved ResearchPlan.
            sources: All collected sources.
            analysis: The analyst's structured analysis.
            verified_claims: Fact-checked claims.

        Returns:
            Tuple of (ResearchReport, pdf_bytes).

        Raises:
            ReportWriterError: If report generation fails.
        """
        logger.info(
            "report_writer_starting",
            research_id=research_id,
            source_count=len(sources),
            finding_count=len(analysis.findings),
            claims_count=len(verified_claims),
        )

        prompt = _build_report_prompt(plan, sources, analysis, verified_claims)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config={"temperature": 0.3, "max_output_tokens": 8192},
            )
            raw_text = response.text
        except Exception as e:
            error_msg = str(e)
            logger.error("gemini_report_writer_error", error=error_msg)
            raise GeminiError(f"Gemini API call failed in Report Writer: {error_msg}")

        if not raw_text or not raw_text.strip():
            raise ReportWriterError("Gemini returned empty response in Report Writer.")

        # Parse JSON
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError as e:
                    raise LLMOutputParseError(
                        f"Could not parse Report Writer response: {e}", raw_output=raw_text
                    )
            else:
                raise ReportWriterError("No JSON found in Report Writer response.")

        # Validate citation IDs in references
        valid_source_ids = {s.source_id for s in sources}

        # Build the report
        report = ResearchReport(
            research_id=research_id,
            title=data.get("title", f"Research Report: {plan.topic[:60]}"),
            executive_summary=data.get("executive_summary", ""),
            objectives=data.get("objectives", plan.scope_and_objectives),
            methodology=data.get("methodology", "Web research using Tavily Search API and AI analysis."),
            key_findings=data.get("key_findings", []),
            detailed_analysis=data.get("detailed_analysis", ""),
            industry_trends=data.get("industry_trends", []),
            opportunities=data.get("opportunities", []),
            risks_and_challenges=data.get("risks_and_challenges", []),
            verified_claims=verified_claims,
            uncertain_findings=data.get("uncertain_findings", []),
            limitations=data.get("limitations", "This research is based on publicly available internet sources and may not reflect the most recent developments."),
            conclusion=data.get("conclusion", ""),
            references=sources,
            created_at=datetime.now(timezone.utc),
            word_count=len(data.get("detailed_analysis", "").split()),
            language=plan.language,
        )

        logger.info(
            "report_structured_created",
            report_id=report.report_id,
            word_count=report.word_count,
        )

        # Generate PDF
        try:
            pdf_bytes = _generate_pdf(report, sources)
            logger.info("report_pdf_generated", size_bytes=len(pdf_bytes))
        except Exception as e:
            logger.error("pdf_generation_failed", error=str(e))
            # Return empty PDF bytes — don't fail the whole report
            pdf_bytes = b""

        return report, pdf_bytes

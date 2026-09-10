"""Generates a downloadable PDF report summarizing a verification result."""
from io import BytesIO
from typing import Any, Dict
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

VERDICT_COLORS = {
    "true": colors.HexColor("#16a34a"),
    "false": colors.HexColor("#dc2626"),
    "misleading": colors.HexColor("#d97706"),
    "unverified": colors.HexColor("#6b7280"),
}


def build_verification_pdf(verification: Dict[str, Any]) -> BytesIO:
    """Build a PDF report for a single verification and return it as an
    in-memory buffer, ready to stream back to the client."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=20, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], textColor=colors.HexColor("#6b7280"), spaceAfter=16
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, leading=14
    )

    verdict = (verification.get("verdict") or "unverified").lower()
    verdict_color = VERDICT_COLORS.get(verdict, colors.grey)
    trust_score = verification.get("trust_score")
    trust_score_display = f"{trust_score:.0f}/100" if trust_score is not None else "N/A"

    elements = []

    elements.append(Paragraph("Fake News Verification Report", title_style))
    created_at = verification.get("created_at")
    created_display = created_at.strftime("%B %d, %Y at %H:%M UTC") if isinstance(created_at, datetime) else str(created_at)
    elements.append(Paragraph(
        f"Verification #{verification.get('id')} &bull; Generated {created_display}",
        subtitle_style
    ))

    # Verdict summary table
    summary_data = [
        ["Verdict", "Trust Score", "Confidence", "Input Type"],
        [
            verdict.upper(),
            trust_score_display,
            f"{(verification.get('confidence') or 0) * 100:.0f}%" if verification.get('confidence') is not None else "N/A",
            (verification.get("input_type") or "text").upper(),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[1.6 * inch] * 4)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR", (0, 1), (0, 1), verdict_color),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb")))

    # AI-generated narrative summary (Groq)
    ai_summary = verification.get("ai_summary")
    if ai_summary:
        elements.append(Paragraph("AI Analysis", heading_style))
        elements.append(Paragraph(_escape(ai_summary), body_style))

    # Extracted content
    elements.append(Paragraph("Extracted Content", heading_style))
    extracted_text = (verification.get("extracted_text") or "No text extracted")[:3000]
    elements.append(Paragraph(_escape(extracted_text), body_style))

    # Explanation factors
    explanation = verification.get("explanation") or []
    if explanation:
        elements.append(Paragraph("Trust Factor Breakdown", heading_style))
        factor_rows = [["Factor", "Weight", "Description"]]
        for item in explanation:
            factor_rows.append([
                item.get("factor", ""),
                f"{int(item.get('weight', 0) * 100)}%",
                Paragraph(_escape(item.get("description", "")), body_style),
            ])
        factor_table = Table(factor_rows, colWidths=[1.3 * inch, 0.7 * inch, 4.2 * inch])
        factor_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(factor_table)

    # Sources
    sources = verification.get("sources") or []
    if sources:
        elements.append(Paragraph("Sources & Evidence", heading_style))
        for source in sources[:15]:
            title = _escape(source.get("title", "Untitled source"))
            publisher = _escape(source.get("publisher") or "")
            rating = _escape(source.get("textual_rating") or "")
            url = source.get("url") or ""
            line = f"<b>{title}</b>"
            if publisher:
                line += f" &mdash; {publisher}"
            if rating:
                line += f" <i>({rating})</i>"
            elements.append(Paragraph(line, body_style))
            if url:
                elements.append(Paragraph(f"<font size=8 color='#6b7280'>{_escape(url)}</font>", body_style))
            elements.append(Spacer(1, 4))

    # Recommendations
    recommendations = verification.get("recommendations") or []
    if recommendations:
        elements.append(Paragraph("Recommendations", heading_style))
        for rec in recommendations:
            elements.append(Paragraph(f"&bull; {_escape(rec)}", body_style))
            elements.append(Spacer(1, 2))

    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb")))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "<font size=8 color='#9ca3af'>This report is generated by an automated multi-agent "
        "AI system. Trust scores are probabilistic assessments and should not be considered "
        "definitive legal or journalistic proof. Always verify critical information through "
        "multiple authoritative sources.</font>",
        body_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _escape(text: str) -> str:
    """Minimal XML escaping for reportlab Paragraph markup."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

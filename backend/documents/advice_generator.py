"""
PDF generator for Legal Advice / Guidance document for Conciliation Court.
"""
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from backend.documents.templates import (
    create_footer_with_page_numbers,
    create_mn_court_header,
    get_court_document_styles,
    get_page_size,
    safe_parse_json_content,
)

if TYPE_CHECKING:
    from backend.database.models import GeneratedDocument

# Minnesota court system links for additional resources
MN_COURT_RESOURCES = (
    "Minnesota Judicial Branch: https://www.mncourts.gov<br/>"
    "Conciliation Court: https://www.mncourts.gov/conciliationcourt<br/>"
    "Self-Help: https://www.mncourts.gov/self-help"
)


def _parse_content(generated_doc: "GeneratedDocument") -> Dict[str, Any]:
    """Extract legal_advice structure from content; fallback to full_text."""
    data = safe_parse_json_content(generated_doc.content or "")
    if not data:
        return {"full_text": (generated_doc.content or "").strip()}
    if "legal_advice" in data and isinstance(data["legal_advice"], dict):
        return data["legal_advice"]
    return data


def _ensure_list(val: Any) -> List[str]:
    """Return list of strings from array or single string."""
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def generate_advice_pdf(generated_doc: "GeneratedDocument", output_path: str) -> str:
    """
    Generate a Legal Guidance PDF from a GeneratedDocument.
    Uses parsed JSON when available; falls back to full_text.
    Returns the output file path.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=get_page_size(),
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch + 20,
        bottomMargin=inch,
    )
    court_styles = get_court_document_styles()
    story = []

    data = _parse_content(generated_doc)
    full_text = (data.get("full_text") or "").strip()

    # Title
    story.append(Paragraph("LEGAL GUIDANCE FOR YOUR CONCILIATION COURT CASE", court_styles["CourtTitle"]))
    story.append(Spacer(1, 12))

    # Disclaimer
    story.append(
        Paragraph(
            "This document provides general information and is not legal advice. "
            "Consult an attorney for specific legal guidance.",
            court_styles["Disclaimer"],
        )
    )
    story.append(Spacer(1, 12))

    # Case summary
    case_summary = (data.get("case_summary") or "").strip()
    if case_summary:
        story.append(Paragraph("CASE SUMMARY", court_styles["SectionHeader"]))
        story.append(Paragraph(case_summary.replace("\n", "<br/>"), court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    # Strengths and weaknesses
    strengths = (data.get("strengths_and_weaknesses") or data.get("strengths_and_weaknesses_text") or "").strip()
    if strengths:
        story.append(Paragraph("STRENGTHS AND WEAKNESSES", court_styles["SectionHeader"]))
        story.append(Paragraph(strengths.replace("\n", "<br/>"), court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    # Recommended actions (bulleted)
    recommended = _ensure_list(data.get("recommended_actions"))
    if recommended:
        story.append(Paragraph("RECOMMENDED ACTIONS", court_styles["SectionHeader"]))
        for item in recommended:
            story.append(Paragraph(f"• {item.replace(chr(10), ' ')}", court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    # Procedural guidance
    procedural = (data.get("procedural_guidance") or "").strip()
    if procedural:
        story.append(Paragraph("PROCEDURAL GUIDANCE", court_styles["SectionHeader"]))
        story.append(Paragraph(procedural.replace("\n", "<br/>"), court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    if not (case_summary or strengths or recommended or procedural):
        story.append(Paragraph(full_text or "No content.", court_styles["BodyText"]))

    # Additional resources
    story.append(Paragraph("ADDITIONAL RESOURCES", court_styles["SectionHeader"]))
    story.append(Paragraph(MN_COURT_RESOURCES, court_styles["BodyText"]))

    def add_header_footer(canvas, doc):
        create_mn_court_header(canvas, doc)
        create_footer_with_page_numbers(canvas, doc)

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return output_path

"""
PDF generator for Minnesota Conciliation Court Hearing Script.
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


def _parse_content(generated_doc: "GeneratedDocument") -> Dict[str, Any]:
    """Extract hearing_script structure from content; fallback to full_text."""
    data = safe_parse_json_content(generated_doc.content or "")
    if not data:
        return {"full_text": (generated_doc.content or "").strip()}
    if "hearing_script" in data and isinstance(data["hearing_script"], dict):
        return data["hearing_script"]
    return data


def _ensure_list(val: Any) -> List[str]:
    """Return list of strings from array or single string."""
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def generate_hearing_script_pdf(generated_doc: "GeneratedDocument", output_path: str) -> str:
    """
    Generate a Hearing Script PDF from a GeneratedDocument.
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
    story.append(Paragraph("HEARING SCRIPT FOR CONCILIATION COURT", court_styles["CourtTitle"]))
    story.append(Spacer(1, 12))

    # Case reference
    story.append(Paragraph("Case reference: ___________", court_styles["BodyText"]))
    story.append(Spacer(1, 16))

    # Introduction
    intro = (data.get("introduction") or "").strip()
    if intro:
        story.append(Paragraph("INTRODUCTION", court_styles["SectionHeader"]))
        story.append(Paragraph(intro.replace("\n", "<br/>"), court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    # Key points
    key_points = _ensure_list(data.get("key_points"))
    if key_points:
        story.append(Paragraph("KEY POINTS TO COVER", court_styles["SectionHeader"]))
        for i, point in enumerate(key_points, 1):
            story.append(Paragraph(f"{i}. {point.replace(chr(10), ' ')}", court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    # Evidence presentation order
    evidence_order = _ensure_list(data.get("evidence_presentation_order"))
    if evidence_order:
        story.append(Paragraph("EVIDENCE PRESENTATION ORDER", court_styles["SectionHeader"]))
        for i, item in enumerate(evidence_order, 1):
            story.append(Paragraph(f"{i}. {item.replace(chr(10), ' ')}", court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    # Closing statement
    closing = (data.get("closing_statement") or "").strip()
    if closing:
        story.append(Paragraph("CLOSING STATEMENT", court_styles["SectionHeader"]))
        story.append(Paragraph(closing.replace("\n", "<br/>"), court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    if not (intro or key_points or evidence_order or closing):
        story.append(Paragraph(full_text or "No content.", court_styles["BodyText"]))

    # Helpful note
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Remember to speak clearly and address the judge respectfully.",
            court_styles["Note"],
        )
    )

    def add_header_footer(canvas, doc):
        create_mn_court_header(canvas, doc)
        create_footer_with_page_numbers(canvas, doc)

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return output_path

"""
PDF generator for Minnesota Conciliation Court Statement of Claim.
"""
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from backend.documents.templates import (
    add_signature_block,
    create_footer_with_page_numbers,
    create_mn_court_header,
    format_currency,
    format_party_names,
    get_court_document_styles,
    get_page_size,
    safe_parse_json_content,
)

if TYPE_CHECKING:
    from backend.database.models import GeneratedDocument


def _parse_content(generated_doc: "GeneratedDocument") -> Dict[str, Any]:
    """Extract statement_of_claim structure from content; fallback to full_text."""
    data = safe_parse_json_content(generated_doc.content or "")
    if not data:
        return {"full_text": (generated_doc.content or "").strip()}
    # Drafting agent may store full response with statement_of_claim key
    if "statement_of_claim" in data and isinstance(data["statement_of_claim"], dict):
        return data["statement_of_claim"]
    return data


def generate_statement_of_claim_pdf(generated_doc: "GeneratedDocument", output_path: str) -> str:
    """
    Generate a Statement of Claim PDF from a GeneratedDocument.
    Uses parsed JSON sections when available; falls back to full_text.
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
    county = (data.get("county") or data.get("court_county") or "__________").strip()

    # Title
    story.append(Paragraph("STATEMENT OF CLAIM", court_styles["CourtTitle"]))
    story.append(Spacer(1, 12))

    # Court information
    court_line = f"STATE OF MINNESOTA, COUNTY OF {county.upper()}, CONCILIATION COURT"
    story.append(Paragraph(court_line, court_styles["BodyText"]))
    story.append(Spacer(1, 12))

    # Parties
    parties = data.get("parties") or data.get("party_names")
    if parties:
        party_text = format_party_names(parties)
        if party_text:
            story.append(Paragraph(party_text, court_styles["BodyText"]))
            story.append(Spacer(1, 8))
    story.append(Paragraph("Case No. ___________", court_styles["BodyText"]))
    story.append(Spacer(1, 16))

    # Claim amount
    claim_amount = data.get("claim_amount") or data.get("amount")
    if claim_amount is not None:
        story.append(Paragraph(f"<b>Claim Amount: {format_currency(claim_amount)}</b>", court_styles["BodyText"]))
        story.append(Spacer(1, 12))

    # If we have structured sections, use them
    facts = (data.get("facts_section") or data.get("facts") or "").strip()
    legal_basis = (data.get("legal_basis_section") or data.get("legal_basis") or "").strip()
    relief = (data.get("relief_requested") or data.get("relief") or "").strip()

    if facts or legal_basis or relief or full_text:
        if facts:
            story.append(Paragraph("FACTS", court_styles["SectionHeader"]))
            story.append(Paragraph(facts.replace("\n", "<br/>"), court_styles["BodyText"]))
            story.append(Spacer(1, 8))
        if legal_basis:
            story.append(Paragraph("LEGAL BASIS", court_styles["SectionHeader"]))
            story.append(Paragraph(legal_basis.replace("\n", "<br/>"), court_styles["BodyText"]))
            story.append(Spacer(1, 8))
        if relief:
            story.append(Paragraph("RELIEF REQUESTED", court_styles["SectionHeader"]))
            story.append(Paragraph(relief.replace("\n", "<br/>"), court_styles["BodyText"]))
            story.append(Spacer(1, 8))
        if full_text and not (facts or legal_basis or relief):
            story.append(Paragraph(full_text.replace("\n", "<br/>"), court_styles["BodyText"]))
    else:
        story.append(Paragraph(full_text or "No content.", court_styles["BodyText"]))

    # Signature
    add_signature_block(story, "Plaintiff")

    def add_header_footer(canvas, doc):
        create_mn_court_header(canvas, doc)
        create_footer_with_page_numbers(canvas, doc)

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return output_path

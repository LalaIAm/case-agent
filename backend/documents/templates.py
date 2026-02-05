"""
Shared PDF template utilities for Minnesota Conciliation Court documents.
"""
import json
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer

from pydantic import ValidationError

from backend.config import Settings, get_settings

# Minnesota court document constants (margins, spacing)
MARGIN = inch
LINE_SPACING = 1.5
COURT_HEADER_COLOR = colors.HexColor("#1a1a1a")

_PAGE_SIZE_MAP = {"LETTER": letter, "A4": A4}
_DEFAULT_FONT_NAME = "Times-Roman"
_DEFAULT_FONT_SIZE = 12


def _get_pdf_settings() -> "Settings | None":
    """Return settings if available; None when validation fails (e.g. tests without .env)."""
    try:
        return get_settings()
    except ValidationError:
        return None


def get_page_size():
    """Return reportlab pagesize from config (PDF_PAGE_SIZE maps to letter or A4)."""
    s = _get_pdf_settings()
    if s is None:
        return letter
    return _PAGE_SIZE_MAP.get(s.PDF_PAGE_SIZE.upper(), letter)


def create_mn_court_header(canvas, doc):
    """Draw consistent Minnesota Conciliation Court header on each page."""
    s = _get_pdf_settings()
    font_name = s.PDF_FONT_NAME if s else _DEFAULT_FONT_NAME
    font_size = max(8, (s.PDF_FONT_SIZE if s else _DEFAULT_FONT_SIZE) - 2)
    canvas.saveState()
    canvas.setFont(font_name, font_size)
    canvas.setFillColor(COURT_HEADER_COLOR)
    canvas.drawCentredString(
        doc.width / 2.0 + doc.leftMargin,
        doc.height + doc.topMargin - 20,
        "STATE OF MINNESOTA — CONCILIATION COURT",
    )
    canvas.restoreState()


def create_footer_with_page_numbers(canvas, doc):
    """Draw footer with page numbers."""
    s = _get_pdf_settings()
    font_name = s.PDF_FONT_NAME if s else _DEFAULT_FONT_NAME
    font_size = max(8, (s.PDF_FONT_SIZE if s else _DEFAULT_FONT_SIZE) - 3)
    canvas.saveState()
    canvas.setFont(font_name, font_size)
    canvas.setFillColor(colors.grey)
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(
        doc.width / 2.0 + doc.leftMargin,
        30,
        f"Page {page_num}",
    )
    canvas.restoreState()


def get_court_document_styles() -> Dict[str, ParagraphStyle]:
    """Return custom ParagraphStyle objects for headers, body, signatures, disclaimers."""
    s = _get_pdf_settings()
    font_name = s.PDF_FONT_NAME if s else _DEFAULT_FONT_NAME
    font_size = s.PDF_FONT_SIZE if s else _DEFAULT_FONT_SIZE
    heading_font_size = min(20, font_size + 2)
    styles = getSampleStyleSheet()
    custom = {
        "CourtTitle": ParagraphStyle(
            name="CourtTitle",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=heading_font_size + 2,
            spaceAfter=12,
            alignment=1,  # TA_CENTER
            textColor=COURT_HEADER_COLOR,
        ),
        "SectionHeader": ParagraphStyle(
            name="SectionHeader",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=heading_font_size,
            spaceBefore=14,
            spaceAfter=8,
            textColor=COURT_HEADER_COLOR,
        ),
        "BodyText": ParagraphStyle(
            name="BodyText",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=font_size,
            leading=font_size * LINE_SPACING,
            spaceAfter=8,
        ),
        "Signature": ParagraphStyle(
            name="Signature",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=font_size,
            spaceBefore=24,
            spaceAfter=4,
        ),
        "Disclaimer": ParagraphStyle(
            name="Disclaimer",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=max(8, font_size - 2),
            textColor=colors.grey,
            spaceBefore=8,
            spaceAfter=8,
            leftIndent=20,
            rightIndent=20,
        ),
        "Note": ParagraphStyle(
            name="Note",
            parent=styles["Normal"],
            fontName="Times-Italic" if "Times" in font_name else font_name,
            fontSize=max(8, font_size - 2),
            textColor=colors.grey,
            spaceAfter=6,
        ),
    }
    return custom


def format_party_names(parties: dict) -> str:
    """Format plaintiff and defendant names from parties dict for display."""
    if not isinstance(parties, dict):
        return ""
    plaintiff = parties.get("plaintiff") or parties.get("plaintiff_name") or ""
    defendant = parties.get("defendant") or parties.get("defendant_name") or ""
    if isinstance(plaintiff, dict):
        plaintiff = plaintiff.get("name", "") or ""
    if isinstance(defendant, dict):
        defendant = defendant.get("name", "") or ""
    plaintiff = str(plaintiff).strip()
    defendant = str(defendant).strip()
    lines = []
    if plaintiff:
        lines.append(f"Plaintiff: {plaintiff}")
    if defendant:
        lines.append(f"Defendant: {defendant}")
    return "<br/>".join(lines) if lines else ""


def format_currency(amount: float | str) -> str:
    """Format claim amount for display (e.g. $1,234.56)."""
    if amount is None:
        return "$0.00"
    try:
        if isinstance(amount, str):
            amount = float(amount.replace(",", "").replace("$", "").strip())
        return f"${amount:,.2f}"
    except (ValueError, TypeError):
        return str(amount)


def add_signature_block(story: List, signer_label: str) -> None:
    """Append signature line and date to story list."""
    styles = get_court_document_styles()
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"{signer_label}: _______________________________", styles["Signature"]))
    story.append(Paragraph("Date: _______________________________", styles["Signature"]))


def safe_parse_json_content(content: str) -> dict:
    """
    Parse JSON from document content with error recovery.
    Returns parsed dict or empty dict on failure.
    """
    if not content or not isinstance(content, str):
        return {}
    raw = content.strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}

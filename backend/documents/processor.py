"""
Document text extraction for PDFs and images.
Uses pdfplumber (primary) with PyPDF2 fallback for PDFs; Pillow for image handling;
pytesseract for OCR on PNG/JPG/JPEG images.
"""
import logging
import re
from pathlib import Path

import pdfplumber
import PyPDF2
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Remove excessive whitespace and normalize line breaks."""
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    if not text:
        return ""
    # Collapse multiple spaces/newlines to single space, then normalize line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file. Uses pdfplumber first, falls back to PyPDF2.
    Raises ValueError on corrupted or unsupported files.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Not a PDF file: {file_path}")

    text_parts: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                raw = page.extract_text()
                if raw:
                    text_parts.append(raw)
    except Exception as e:
        logger.warning("pdfplumber failed for %s: %s; trying PyPDF2", file_path, e)
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    raw = page.extract_text()
                    if raw:
                        text_parts.append(raw)
        except Exception as e2:
            logger.exception("PDF extraction failed for %s", file_path)
            raise ValueError(f"Could not extract text from PDF: {e2}") from e2

    combined = "\n\n".join(text_parts) if text_parts else ""
    return _normalize_text(combined)


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from an image using OCR. Uses Pillow for validation and loading;
    pytesseract for text extraction. Returns normalized text (or empty string if OCR finds none).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")
    ext = path.suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        raise ValueError(f"Unsupported image type: {file_path}")

    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as e:
        logger.exception("Invalid or corrupted image: %s", file_path)
        raise ValueError(f"Could not open image: {e}") from e

    try:
        with Image.open(path) as img:
            # Convert to RGB if necessary (e.g. palette or RGBA) for consistent OCR
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            raw_text = pytesseract.image_to_string(img)
    except Exception as e:
        logger.exception("OCR failed for image: %s", file_path)
        raise ValueError(f"Could not extract text from image: {e}") from e

    return _normalize_text(raw_text or "")


def process_document(file_path: str, file_type: str) -> str:
    """
    Dispatcher: route to the appropriate extractor based on file_type.
    file_type should be a lowercase extension (e.g. 'pdf', 'png', 'jpg', 'jpeg').
    """
    if not file_path or not file_type:
        return ""
    ft = file_type.lower().strip()
    if ft == "pdf":
        return extract_text_from_pdf(file_path)
    if ft in ("png", "jpg", "jpeg"):
        return extract_text_from_image(file_path)
    raise ValueError(f"Unsupported file type for text extraction: {file_type}")

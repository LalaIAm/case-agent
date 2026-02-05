"""
Reusable validation functions for file uploads, text content, and dates.
"""
import re
import uuid
from datetime import datetime
from typing import List, Optional, Set

from backend.config import get_settings

# Common dangerous filename characters
UNSAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Default allowed file extensions (can be overridden by config)
DEFAULT_ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


def strip_str(v: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
    """Strip whitespace from string; optionally enforce max length. Returns None for None."""
    if v is None:
        return None
    s = str(v).strip()
    if max_length is not None and len(s) > max_length:
        raise ValueError(f"Must be at most {max_length} characters")
    return s if s else None


def strip_str_required(v: str, max_length: Optional[int] = None) -> str:
    """Strip whitespace; require non-empty. Optionally enforce max length."""
    if not isinstance(v, str):
        raise ValueError("Must be a string")
    s = v.strip()
    if not s:
        raise ValueError("Must not be empty after trimming")
    if max_length is not None and len(s) > max_length:
        raise ValueError(f"Must be at most {max_length} characters")
    return s


def validate_filename(filename: str) -> str:
    """Validate filename: non-empty, no path components, no dangerous characters."""
    if not filename or not filename.strip():
        raise ValueError("Filename must not be empty")
    name = filename.strip()
    if "/" in name or "\\" in name:
        raise ValueError("Filename must not contain path separators")
    if UNSAFE_FILENAME_RE.search(name):
        raise ValueError("Filename contains invalid characters")
    if len(name) > 255:
        raise ValueError("Filename too long")
    return name


def validate_file_extension(filename: str, allowed: Optional[Set[str]] = None) -> str:
    """Ensure file extension is in the allowed set (e.g. pdf, png, jpg)."""
    allowed = allowed or set(ext.lower() for ext in get_settings().ALLOWED_FILE_TYPES)
    if not filename or "." not in filename:
        raise ValueError("Filename must have an extension")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        raise ValueError(f"File type not allowed. Allowed: {', '.join(sorted(allowed))}")
    return filename


def validate_file_size(size_bytes: int) -> int:
    """Ensure file size is within configured max upload size."""
    settings = get_settings()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes < 0:
        raise ValueError("File size must be non-negative")
    if size_bytes > max_bytes:
        raise ValueError(f"File size exceeds maximum of {settings.MAX_UPLOAD_SIZE_MB} MB")
    return size_bytes


def validate_content_length(content: str, max_chars: Optional[int] = 100_000) -> str:
    """Validate text content length (e.g. for document content)."""
    s = content.strip() if content else ""
    if max_chars is not None and len(s) > max_chars:
        raise ValueError(f"Content must be at most {max_chars} characters")
    return s


def validate_uuid_format(value: str) -> str:
    """Ensure string is a valid UUID format (hex with hyphens)."""
    s = (value or "").strip()
    try:
        uuid.UUID(s)
        return s
    except (ValueError, TypeError):
        raise ValueError("Invalid UUID format")


def validate_date_range(start: Optional[datetime], end: Optional[datetime]) -> None:
    """Raise if start > end."""
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must be before or equal to end_date")

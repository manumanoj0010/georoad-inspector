"""File validation utilities for uploaded images."""

import logging
from pathlib import Path

from PIL import Image as PILImage

from app.config import settings

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when file validation fails."""

    def __init__(self, filename: str, reason: str):
        self.filename = filename
        self.reason = reason
        super().__init__(f"{filename}: {reason}")


def validate_upload(filename: str, file_size: int, content: bytes) -> None:
    """
    Validate an uploaded file before saving.

    Raises ValidationError if the file is invalid.
    """
    # Check extension
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_extensions_set:
        raise ValidationError(
            filename,
            f"Unsupported file type '{suffix}'. Allowed: {settings.allowed_extensions}",
        )

    # Check file size
    if file_size > settings.max_upload_size_bytes:
        raise ValidationError(
            filename,
            f"File too large ({file_size / (1024*1024):.1f} MB). Max: {settings.max_upload_size_mb} MB",
        )

    if file_size == 0:
        raise ValidationError(filename, "File is empty")

    # Verify it's a readable image (catches corrupt files)
    try:
        import io
        img = PILImage.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise ValidationError(filename, "File is not a valid image or is corrupt")


def generate_stored_filename(original: str, run_id: int, index: int) -> str:
    """
    Generate a unique stored filename to avoid collisions.

    Format: run_{run_id}_{index:04d}_{original_stem}{ext}
    """
    path = Path(original)
    stem = path.stem[:50]  # Truncate long filenames
    suffix = path.suffix.lower()
    # Sanitize: keep only alphanumeric, dash, underscore
    safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    return f"run_{run_id}_{index:04d}_{safe_stem}{suffix}"

"""Unique ID generation for detections."""

import time
from datetime import datetime


_counter = 0


def generate_detection_id() -> str:
    """
    Generate a unique detection ID.

    Format: RD-{year}-{sequential_number:06d}
    Example: RD-2026-000123
    """
    global _counter
    _counter += 1
    year = datetime.now().year
    return f"RD-{year}-{_counter:06d}"


def reset_counter() -> None:
    """Reset counter (for testing)."""
    global _counter
    _counter = 0

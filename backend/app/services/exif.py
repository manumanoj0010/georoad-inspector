"""EXIF metadata extraction service.

Extracts GPS coordinates, timestamps, and camera info from image files.
Adapted from the original geotag.py module.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import exifread
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


@dataclass
class ImageMetadata:
    """Structured EXIF metadata extracted from an image."""

    width: int | None = None
    height: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    captured_at: datetime | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    orientation: int | None = None
    has_gps: bool = False


def extract_metadata(image_path: str | Path) -> ImageMetadata:
    """
    Extract all available EXIF metadata from an image file.

    Returns an ImageMetadata dataclass with whatever data is available.
    Fields that can't be extracted are left as None.
    """
    path = Path(image_path)
    meta = ImageMetadata()

    # Get image dimensions via Pillow (works even without EXIF)
    try:
        with PILImage.open(path) as img:
            meta.width = img.width
            meta.height = img.height
    except Exception as e:
        logger.warning(f"Could not read image dimensions: {path.name} — {e}")

    # Read EXIF tags
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False)
    except Exception as e:
        logger.warning(f"Could not read EXIF data: {path.name} — {e}")
        return meta

    # GPS extraction
    gps_tags = [
        "GPS GPSLatitude", "GPS GPSLatitudeRef",
        "GPS GPSLongitude", "GPS GPSLongitudeRef",
    ]
    if all(tag in tags for tag in gps_tags):
        try:
            meta.latitude = _dms_to_decimal(tags["GPS GPSLatitude"], tags["GPS GPSLatitudeRef"])
            meta.longitude = _dms_to_decimal(tags["GPS GPSLongitude"], tags["GPS GPSLongitudeRef"])
            meta.has_gps = True
        except Exception as e:
            logger.warning(f"GPS conversion failed: {path.name} — {e}")

    # Altitude
    if "GPS GPSAltitude" in tags:
        try:
            alt_val = tags["GPS GPSAltitude"].values[0]
            meta.altitude = alt_val.num / alt_val.den
        except Exception:
            pass

    # Camera info
    if "Image Make" in tags:
        meta.camera_make = str(tags["Image Make"]).strip()
    if "Image Model" in tags:
        meta.camera_model = str(tags["Image Model"]).strip()

    # Orientation
    if "Image Orientation" in tags:
        try:
            meta.orientation = int(str(tags["Image Orientation"]))
        except (ValueError, TypeError):
            pass

    # Capture timestamp
    for date_tag in ["EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"]:
        if date_tag in tags:
            try:
                dt_str = str(tags[date_tag])
                meta.captured_at = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                break
            except (ValueError, TypeError):
                continue

    return meta


def _dms_to_decimal(dms_tag, ref_tag) -> float:
    """Convert EXIF GPS DMS (degrees/minutes/seconds) to decimal degrees."""
    values = dms_tag.values
    degrees = values[0].num / values[0].den
    minutes = values[1].num / values[1].den
    seconds = values[2].num / values[2].den

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

    ref = str(ref_tag)
    if ref in ("S", "W"):
        decimal = -decimal

    return round(decimal, 6)

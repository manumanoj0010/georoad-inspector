"""GeoJSON generation service.

Converts detection records from the database into standards-compliant
GeoJSON FeatureCollections with Point geometry.

IMPORTANT: GeoJSON coordinate order is [longitude, latitude].
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection import Detection, ReviewStatus
from app.models.inspection_run import InspectionRun

logger = logging.getLogger(__name__)


def detection_to_feature(detection: Detection, image_url: str | None = None) -> dict[str, Any]:
    """
    Convert a single Detection record into a GeoJSON Feature.

    Returns None-geometry feature if detection has no coordinates.
    """
    # GeoJSON uses [longitude, latitude] order
    geometry = None
    if detection.latitude is not None and detection.longitude is not None:
        geometry = {
            "type": "Point",
            "coordinates": [detection.longitude, detection.latitude],
        }

    return {
        "type": "Feature",
        "id": detection.detection_id,
        "geometry": geometry,
        "properties": {
            "detectionId": detection.detection_id,
            "damageType": detection.damage_type,
            "confidence": round(detection.confidence, 4),
            "reviewStatus": detection.review_status.value if isinstance(detection.review_status, ReviewStatus) else detection.review_status,
            "locationMethod": detection.location_method,
            "imageId": detection.image_id,
            "imageUrl": image_url,
            "boundingBox": {
                "xMin": detection.x_min,
                "yMin": detection.y_min,
                "xMax": detection.x_max,
                "yMax": detection.y_max,
            },
            "modelVersion": detection.model_version,
            "createdAt": detection.created_at.isoformat() if detection.created_at else None,
        },
    }


def build_feature_collection(
    detections: list[Detection],
    image_urls: dict[int, str] | None = None,
) -> dict[str, Any]:
    """
    Build a complete GeoJSON FeatureCollection from a list of detections.

    Parameters
    ----------
    detections : list of Detection model instances
    image_urls : optional mapping of image_id → URL for image references
    """
    urls = image_urls or {}
    features = []

    for det in detections:
        # Skip detections without GPS for GeoJSON (they have no valid geometry)
        if det.latitude is None or det.longitude is None:
            continue
        feature = detection_to_feature(det, image_url=urls.get(det.image_id))
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


async def generate_geojson(
    run_id: int,
    db: AsyncSession,
    confirmed_only: bool = False,
    min_confidence: float | None = None,
    damage_type: str | None = None,
) -> dict[str, Any]:
    """
    Generate a GeoJSON FeatureCollection for an inspection run.

    Parameters
    ----------
    run_id : inspection run ID
    db : database session
    confirmed_only : if True, only include confirmed detections
    min_confidence : filter by minimum confidence
    damage_type : filter by damage type
    """
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise ValueError(f"Inspection run {run_id} not found")

    # Build query with filters
    query = select(Detection).where(
        Detection.inspection_run_id == run_id,
        Detection.latitude.isnot(None),
        Detection.longitude.isnot(None),
    )

    if confirmed_only:
        query = query.where(Detection.review_status == ReviewStatus.CONFIRMED)

    if min_confidence is not None:
        query = query.where(Detection.confidence >= min_confidence)

    if damage_type:
        query = query.where(Detection.damage_type == damage_type)

    query = query.order_by(Detection.confidence.desc())
    result = await db.execute(query)
    detections = list(result.scalars().all())

    logger.info(f"GeoJSON export: run={run_id}, features={len(detections)}, confirmed_only={confirmed_only}")

    return build_feature_collection(detections)

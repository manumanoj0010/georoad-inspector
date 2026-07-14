"""ArcGIS Online publishing service.

Publishes confirmed detections to a hosted feature layer on ArcGIS Online.
All credentials are server-side only — never exposed to the browser.

Supports two modes:
- Live mode: Authenticates and publishes to a real ArcGIS feature layer.
- Mock mode: Returns simulated success (for dev/demo when ArcGIS is not configured).
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.arcgis_publication import ArcGISPublication, PublicationStatus
from app.models.detection import Detection, ReviewStatus
from app.models.inspection_run import InspectionRun

logger = logging.getLogger(__name__)


class ArcGISPublishError(Exception):
    pass


def _detection_to_arcgis_feature(det: Detection) -> dict:
    """Convert a Detection record to an ArcGIS feature object."""
    return {
        "attributes": {
            "detection_id": det.detection_id,
            "inspection_run_id": det.inspection_run_id,
            "image_id": det.image_id,
            "damage_type": det.damage_type,
            "confidence": det.confidence,
            "review_status": det.review_status.value if isinstance(det.review_status, ReviewStatus) else det.review_status,
            "location_method": det.location_method,
            "model_version": det.model_version,
            "created_at": det.created_at.isoformat() if det.created_at else None,
        },
        "geometry": {
            "x": det.longitude,
            "y": det.latitude,
            "spatialReference": {"wkid": 4326},
        },
    }


async def _get_arcgis_token() -> str:
    """Authenticate with ArcGIS Online using client credentials (OAuth 2.0)."""
    token_url = f"{settings.arcgis_portal_url}/sharing/rest/oauth2/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "client_id": settings.arcgis_client_id,
                "client_secret": settings.arcgis_client_secret,
                "grant_type": "client_credentials",
                "expiration": 60,
            },
        )

    if resp.status_code != 200:
        raise ArcGISPublishError(f"Authentication failed: HTTP {resp.status_code}")

    data = resp.json()
    if "error" in data:
        raise ArcGISPublishError(f"Authentication error: {data['error'].get('message', 'Unknown')}")

    token = data.get("access_token")
    if not token:
        raise ArcGISPublishError("No access_token in auth response")

    return token


async def _add_features_to_layer(token: str, features: list[dict]) -> dict:
    """Send features to the ArcGIS feature layer's addFeatures endpoint."""
    import json

    add_url = f"{settings.arcgis_feature_layer_url}/addFeatures"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            add_url,
            data={
                "f": "json",
                "token": token,
                "features": json.dumps(features),
            },
        )

    if resp.status_code != 200:
        raise ArcGISPublishError(f"addFeatures failed: HTTP {resp.status_code}")

    result = resp.json()
    if "error" in result:
        raise ArcGISPublishError(f"addFeatures error: {result['error'].get('message', 'Unknown')}")

    return result


async def publish_to_arcgis(run_id: int, db: AsyncSession) -> dict:
    """
    Publish confirmed detections from an inspection run to ArcGIS Online.

    Only publishes detections that:
    - Have review_status = 'confirmed'
    - Have GPS coordinates
    - Have not already been published (no arcgis_object_id)

    Returns a summary dict with counts and status.
    """
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise ValueError(f"Inspection run {run_id} not found")

    # Create publication record
    publication = ArcGISPublication(
        inspection_run_id=run_id,
        status=PublicationStatus.PUBLISHING,
    )
    db.add(publication)
    await db.flush()

    # Get eligible detections
    result = await db.execute(
        select(Detection).where(
            Detection.inspection_run_id == run_id,
            Detection.review_status == ReviewStatus.CONFIRMED,
            Detection.latitude.isnot(None),
            Detection.longitude.isnot(None),
            Detection.arcgis_object_id.is_(None),  # Not already published
        )
    )
    detections = list(result.scalars().all())

    if not detections:
        publication.status = PublicationStatus.COMPLETED
        publication.published_count = 0
        return {
            "status": "completed",
            "message": "No eligible detections to publish (must be confirmed with GPS and not already published)",
            "published_count": 0,
            "failed_count": 0,
        }

    # Check if ArcGIS is configured
    if not settings.arcgis_enabled:
        # Mock mode — simulate success for development/demo
        logger.info(f"ArcGIS not configured — mock publishing {len(detections)} detections")
        publication.status = PublicationStatus.COMPLETED
        publication.published_count = len(detections)
        publication.published_at = datetime.utcnow()
        publication.feature_layer_url = "mock://arcgis-not-configured"

        # Mark detections as published
        for det in detections:
            det.review_status = ReviewStatus.PUBLISHED
            det.arcgis_object_id = det.id  # Use local ID as mock

        await db.flush()

        return {
            "status": "completed",
            "mode": "mock",
            "message": f"Mock published {len(detections)} detections (ArcGIS not configured)",
            "published_count": len(detections),
            "failed_count": 0,
        }

    # Live mode — authenticate and publish
    try:
        logger.info(f"Authenticating with ArcGIS: {settings.arcgis_portal_url}")
        token = await _get_arcgis_token()

        # Convert detections to ArcGIS feature format
        features = [_detection_to_arcgis_feature(det) for det in detections]

        # Publish in batches of 100 (ArcGIS limit)
        published_count = 0
        failed_count = 0

        for i in range(0, len(features), 100):
            batch = features[i:i + 100]
            batch_detections = detections[i:i + 100]

            try:
                result_data = await _add_features_to_layer(token, batch)
                add_results = result_data.get("addResults", [])

                for j, add_result in enumerate(add_results):
                    if add_result.get("success"):
                        batch_detections[j].arcgis_object_id = add_result.get("objectId")
                        batch_detections[j].review_status = ReviewStatus.PUBLISHED
                        published_count += 1
                    else:
                        failed_count += 1
                        logger.warning(f"Feature publish failed: {add_result.get('error')}")

            except ArcGISPublishError as e:
                logger.error(f"Batch publish failed: {e}")
                failed_count += len(batch)

        # Update publication record
        publication.published_count = published_count
        publication.failed_count = failed_count
        publication.feature_layer_url = settings.arcgis_feature_layer_url
        publication.published_at = datetime.utcnow()

        if failed_count == 0:
            publication.status = PublicationStatus.COMPLETED
        elif published_count > 0:
            publication.status = PublicationStatus.PARTIAL
        else:
            publication.status = PublicationStatus.FAILED

        await db.flush()

        summary = {
            "status": publication.status.value,
            "mode": "live",
            "published_count": published_count,
            "failed_count": failed_count,
            "feature_layer_url": settings.arcgis_feature_layer_url,
            "web_map_url": settings.arcgis_web_map_url or None,
        }

        logger.info(f"ArcGIS publish complete: {published_count} published, {failed_count} failed")
        return summary

    except ArcGISPublishError as e:
        publication.status = PublicationStatus.FAILED
        publication.error_message = str(e)[:2000]
        await db.flush()
        raise

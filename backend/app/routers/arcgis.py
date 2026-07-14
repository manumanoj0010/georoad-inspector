"""ArcGIS Online publishing API router."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.arcgis_publication import ArcGISPublication
from app.models.inspection_run import InspectionRun
from app.services.arcgis import ArcGISPublishError, publish_to_arcgis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["arcgis"])


@router.post("/api/inspection-runs/{run_id}/publish/arcgis")
async def publish_arcgis(run_id: int, db: AsyncSession = Depends(get_db)):
    """
    Publish confirmed detections from an inspection run to ArcGIS Online.

    Only publishes detections that are:
    - Confirmed by a reviewer
    - Have GPS coordinates
    - Not already published

    If ArcGIS credentials are not configured, runs in mock mode
    (suitable for development and demos).
    """
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    try:
        result = await publish_to_arcgis(run_id, db)
        return result
    except ArcGISPublishError as e:
        raise HTTPException(status_code=502, detail=f"ArcGIS publishing failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error publishing to ArcGIS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error during ArcGIS publishing")


@router.get("/api/inspection-runs/{run_id}/publish/arcgis/status")
async def get_arcgis_status(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get the ArcGIS publication status for an inspection run."""
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    result = await db.execute(
        select(ArcGISPublication)
        .where(ArcGISPublication.inspection_run_id == run_id)
        .order_by(ArcGISPublication.id.desc())
    )
    publications = result.scalars().all()

    if not publications:
        return {
            "run_id": run_id,
            "published": False,
            "publications": [],
            "arcgis_configured": settings.arcgis_enabled,
        }

    return {
        "run_id": run_id,
        "published": True,
        "arcgis_configured": settings.arcgis_enabled,
        "publications": [
            {
                "id": pub.id,
                "status": pub.status.value,
                "published_count": pub.published_count,
                "failed_count": pub.failed_count,
                "feature_layer_url": pub.feature_layer_url,
                "published_at": pub.published_at.isoformat() if pub.published_at else None,
                "error_message": pub.error_message,
            }
            for pub in publications
        ],
    }

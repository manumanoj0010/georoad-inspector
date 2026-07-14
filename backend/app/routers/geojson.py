"""GeoJSON API router — generate, preview, and download GeoJSON."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.inspection_run import InspectionRun
from app.services.geojson import generate_geojson

logger = logging.getLogger(__name__)
router = APIRouter(tags=["geojson"])


@router.get("/api/inspection-runs/{run_id}/geojson")
async def get_geojson(
    run_id: int,
    confirmed_only: bool = Query(False, description="Only include confirmed detections"),
    min_confidence: float | None = Query(None, ge=0, le=1),
    damage_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate GeoJSON FeatureCollection for an inspection run.

    Returns JSON response suitable for Leaflet or other map clients.
    """
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    geojson = await generate_geojson(
        run_id, db,
        confirmed_only=confirmed_only,
        min_confidence=min_confidence,
        damage_type=damage_type,
    )

    return geojson


@router.get("/api/inspection-runs/{run_id}/geojson/download")
async def download_geojson(
    run_id: int,
    confirmed_only: bool = Query(False),
    min_confidence: float | None = Query(None, ge=0, le=1),
    damage_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Download GeoJSON as a .geojson file attachment.

    Suitable for importing into ArcGIS Online, ArcGIS Pro, QGIS, or geojson.io.
    """
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    geojson = await generate_geojson(
        run_id, db,
        confirmed_only=confirmed_only,
        min_confidence=min_confidence,
        damage_type=damage_type,
    )

    # Sanitize run name for filename
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in run.name)
    safe_name = safe_name.strip().replace(" ", "_")[:50] or "detections"
    filename = f"{safe_name}_run{run_id}.geojson"

    content = json.dumps(geojson, indent=2)

    return Response(
        content=content,
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

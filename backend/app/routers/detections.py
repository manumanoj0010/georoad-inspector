"""Detections API router — list, filter, review detections."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.detection import Detection, ReviewStatus
from app.models.inspection_run import InspectionRun
from app.models.review_action import ReviewAction
from app.schemas.detection import DetectionResponse, DetectionUpdate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["detections"])


@router.get("/api/inspection-runs/{run_id}/detections", response_model=list[DetectionResponse])
async def list_detections(
    run_id: int,
    damage_type: str | None = Query(None),
    min_confidence: float | None = Query(None, ge=0, le=1),
    max_confidence: float | None = Query(None, ge=0, le=1),
    review_status: str | None = Query(None),
    has_gps: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List detections for a run with optional filters."""
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    query = select(Detection).where(Detection.inspection_run_id == run_id)

    if damage_type:
        query = query.where(Detection.damage_type == damage_type)
    if min_confidence is not None:
        query = query.where(Detection.confidence >= min_confidence)
    if max_confidence is not None:
        query = query.where(Detection.confidence <= max_confidence)
    if review_status:
        query = query.where(Detection.review_status == review_status)
    if has_gps is True:
        query = query.where(Detection.latitude.isnot(None))
    elif has_gps is False:
        query = query.where(Detection.latitude.is_(None))

    query = query.order_by(Detection.confidence.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/api/detections/{detection_id}", response_model=DetectionResponse)
async def get_detection(detection_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single detection by database ID."""
    detection = await db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    return detection


@router.patch("/api/detections/{detection_id}", response_model=DetectionResponse)
async def update_detection(
    detection_id: int,
    data: DetectionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a detection (review status, notes)."""
    detection = await db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    if data.review_status:
        # Validate status
        try:
            new_status = ReviewStatus(data.review_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid review_status. Must be one of: {[s.value for s in ReviewStatus]}",
            )

        # Create audit trail
        action = ReviewAction(
            detection_id=detection.id,
            previous_status=detection.review_status.value,
            new_status=new_status.value,
            notes=data.review_notes,
        )
        db.add(action)
        detection.review_status = new_status

    if data.review_notes is not None:
        detection.review_notes = data.review_notes

    await db.flush()
    await db.refresh(detection)
    return detection


@router.post("/api/detections/{detection_id}/confirm", response_model=DetectionResponse)
async def confirm_detection(detection_id: int, db: AsyncSession = Depends(get_db)):
    """Shortcut to confirm a detection."""
    detection = await db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    action = ReviewAction(
        detection_id=detection.id,
        previous_status=detection.review_status.value,
        new_status=ReviewStatus.CONFIRMED.value,
    )
    db.add(action)
    detection.review_status = ReviewStatus.CONFIRMED
    await db.flush()
    await db.refresh(detection)
    return detection


@router.post("/api/detections/{detection_id}/reject", response_model=DetectionResponse)
async def reject_detection(detection_id: int, db: AsyncSession = Depends(get_db)):
    """Shortcut to reject a detection."""
    detection = await db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    action = ReviewAction(
        detection_id=detection.id,
        previous_status=detection.review_status.value,
        new_status=ReviewStatus.REJECTED.value,
    )
    db.add(action)
    detection.review_status = ReviewStatus.REJECTED
    await db.flush()
    await db.refresh(detection)
    return detection

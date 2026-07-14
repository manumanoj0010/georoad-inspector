"""Processing API router — trigger and monitor inference."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.inspection_run import InspectionRun, RunStatus
from app.services.processing import process_inspection_run

logger = logging.getLogger(__name__)
router = APIRouter(tags=["processing"])


@router.post("/api/inspection-runs/{run_id}/process")
async def start_processing(run_id: int, db: AsyncSession = Depends(get_db)):
    """
    Process all pending images in an inspection run through the YOLO model.

    This runs inference synchronously (suitable for small batches).
    For large datasets, consider async task queues.
    """
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    if run.status == RunStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Run is already being processed")

    if run.total_images == 0:
        raise HTTPException(status_code=400, detail="No images uploaded to this run")

    try:
        summary = await process_inspection_run(run_id, db)
        return {
            "status": "completed",
            "run_id": run_id,
            **summary,
        }
    except Exception as e:
        logger.error(f"Processing failed for run {run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/api/inspection-runs/{run_id}/status")
async def get_processing_status(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get the current processing status of an inspection run."""
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    return {
        "run_id": run_id,
        "status": run.status.value,
        "total_images": run.total_images,
        "processed_images": run.processed_images,
        "failed_images": run.failed_images,
        "total_detections": run.total_detections,
        "model_version": run.model_version,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }

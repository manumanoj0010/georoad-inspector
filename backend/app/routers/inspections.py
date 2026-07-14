"""Inspection runs API router."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.inspection_run import InspectionRun, RunStatus
from app.schemas.inspection import InspectionRunCreate, InspectionRunResponse, InspectionRunSummary

router = APIRouter(prefix="/api/inspection-runs", tags=["inspections"])


@router.post("", response_model=InspectionRunResponse, status_code=201)
async def create_inspection_run(
    data: InspectionRunCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new inspection run."""
    run = InspectionRun(name=data.name, status=RunStatus.CREATED)
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


@router.get("", response_model=list[InspectionRunSummary])
async def list_inspection_runs(db: AsyncSession = Depends(get_db)):
    """List all inspection runs."""
    result = await db.execute(
        select(InspectionRun).order_by(InspectionRun.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{run_id}", response_model=InspectionRunResponse)
async def get_inspection_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single inspection run by ID."""
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")
    return run


@router.delete("/{run_id}", status_code=204)
async def delete_inspection_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an inspection run and all associated data."""
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")
    await db.delete(run)

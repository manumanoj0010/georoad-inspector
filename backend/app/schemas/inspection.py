"""Pydantic schemas for inspection runs."""

from datetime import datetime

from pydantic import BaseModel, Field


class InspectionRunCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Highway 101 Inspection"])


class InspectionRunResponse(BaseModel):
    id: int
    name: str
    status: str
    total_images: int
    processed_images: int
    failed_images: int
    total_detections: int
    model_version: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InspectionRunSummary(BaseModel):
    id: int
    name: str
    status: str
    total_images: int
    total_detections: int
    created_at: datetime

    model_config = {"from_attributes": True}

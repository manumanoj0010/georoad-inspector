"""Pydantic schemas for detections."""

from datetime import datetime

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    center_x: float
    center_y: float


class DetectionResponse(BaseModel):
    id: int
    detection_id: str
    inspection_run_id: int
    image_id: int
    damage_type: str
    class_id: int
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    center_x: float
    center_y: float
    latitude: float | None
    longitude: float | None
    location_method: str
    review_status: str
    review_notes: str | None
    model_version: str | None
    arcgis_object_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DetectionUpdate(BaseModel):
    review_status: str | None = None
    review_notes: str | None = Field(None, max_length=1000)


class DetectionFilter(BaseModel):
    damage_type: str | None = None
    min_confidence: float | None = None
    max_confidence: float | None = None
    review_status: str | None = None
    has_gps: bool | None = None
    model_version: str | None = None

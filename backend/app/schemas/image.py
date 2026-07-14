"""Pydantic schemas for images."""

from datetime import datetime

from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: int
    inspection_run_id: int
    original_filename: str
    stored_filename: str
    storage_url: str | None
    width: int | None
    height: int | None
    latitude: float | None
    longitude: float | None
    altitude: float | None
    captured_at: datetime | None
    camera_make: str | None
    camera_model: str | None
    location_method: str
    processing_status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImageUploadResult(BaseModel):
    uploaded: int
    failed: int
    errors: list[str]
    images: list[ImageResponse]

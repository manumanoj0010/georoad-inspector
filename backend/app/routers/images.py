"""Image upload and listing API router."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.image import Image, LocationMethod, ProcessingStatus
from app.models.inspection_run import InspectionRun, RunStatus
from app.schemas.image import ImageResponse, ImageUploadResult
from app.services.exif import extract_metadata
from app.utils.file_validation import ValidationError, generate_stored_filename, validate_upload

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


@router.post(
    "/api/inspection-runs/{run_id}/images",
    response_model=ImageUploadResult,
)
async def upload_images(
    run_id: int,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more images to an inspection run."""
    # Verify the run exists
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    # Ensure upload directory exists
    upload_dir = settings.upload_dir / str(run_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded_images: list[Image] = []
    errors: list[str] = []

    # Get current image count for this run (for filename indexing)
    result = await db.execute(
        select(Image).where(Image.inspection_run_id == run_id)
    )
    current_count = len(result.scalars().all())

    for i, file in enumerate(files):
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)

            # Validate
            validate_upload(file.filename or "unknown", file_size, content)

            # Generate unique stored filename
            stored_name = generate_stored_filename(
                file.filename or "image.jpg",
                run_id,
                current_count + i,
            )

            # Save to disk
            file_path = upload_dir / stored_name
            file_path.write_bytes(content)

            # Extract EXIF metadata
            meta = extract_metadata(str(file_path))

            # Determine location method
            if meta.has_gps:
                location_method = LocationMethod.CAMERA_EXIF
            else:
                location_method = LocationMethod.UNMAPPED

            # Create database record
            image = Image(
                inspection_run_id=run_id,
                original_filename=file.filename or "unknown",
                stored_filename=stored_name,
                storage_url=f"/uploads/{run_id}/{stored_name}",
                width=meta.width,
                height=meta.height,
                latitude=meta.latitude,
                longitude=meta.longitude,
                altitude=meta.altitude,
                captured_at=meta.captured_at,
                camera_make=meta.camera_make,
                camera_model=meta.camera_model,
                location_method=location_method,
                processing_status=ProcessingStatus.PENDING,
            )
            db.add(image)
            uploaded_images.append(image)

            logger.info(f"Uploaded: {file.filename} → {stored_name} (GPS: {meta.has_gps})")

        except ValidationError as e:
            errors.append(str(e))
            logger.warning(f"Upload validation failed: {e}")
        except Exception as e:
            errors.append(f"{file.filename}: Unexpected error — {str(e)}")
            logger.error(f"Upload failed for {file.filename}: {e}", exc_info=True)

    # Update run counters
    await db.flush()
    run.total_images = current_count + len(uploaded_images)
    if run.status == RunStatus.CREATED:
        run.status = RunStatus.UPLOADING

    # Refresh to get auto-generated fields
    for img in uploaded_images:
        await db.refresh(img)

    return ImageUploadResult(
        uploaded=len(uploaded_images),
        failed=len(errors),
        errors=errors,
        images=[ImageResponse.model_validate(img) for img in uploaded_images],
    )


@router.get("/api/inspection-runs/{run_id}/images", response_model=list[ImageResponse])
async def list_images(run_id: int, db: AsyncSession = Depends(get_db)):
    """List all images in an inspection run."""
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Inspection run not found")

    result = await db.execute(
        select(Image).where(Image.inspection_run_id == run_id).order_by(Image.id)
    )
    return result.scalars().all()


@router.get("/api/images/{image_id}", response_model=ImageResponse)
async def get_image(image_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single image by ID."""
    image = await db.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image

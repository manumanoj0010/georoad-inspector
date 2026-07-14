"""Processing service — orchestrates detection pipeline for an inspection run.

This is the layer between raw YOLO inference and the database.
It coordinates: image loading → inference → detection record creation → status tracking.
"""

import logging
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.detection import Detection, ReviewStatus
from app.models.image import Image, ProcessingStatus
from app.models.inspection_run import InspectionRun, RunStatus
from app.services.inference import inference_service
from app.utils.id_generator import generate_detection_id

logger = logging.getLogger(__name__)


async def process_inspection_run(run_id: int, db: AsyncSession) -> dict:
    """
    Process all pending images in an inspection run through the YOLO model.

    Steps for each image:
    1. Load the image from disk
    2. Run YOLO inference
    3. Create Detection records with GPS from the source image
    4. Update image and run status

    Returns a summary dict with processing statistics.
    """
    # Load the run
    run = await db.get(InspectionRun, run_id)
    if not run:
        raise ValueError(f"Inspection run {run_id} not found")

    # Ensure model is loaded
    if not inference_service.is_loaded:
        inference_service.load_model()

    # Update run status
    run.status = RunStatus.PROCESSING
    run.started_at = datetime.utcnow()
    run.model_version = inference_service.model_version
    await db.flush()

    # Get all pending images for this run
    result = await db.execute(
        select(Image)
        .where(Image.inspection_run_id == run_id)
        .where(Image.processing_status == ProcessingStatus.PENDING)
        .order_by(Image.id)
    )
    images = list(result.scalars().all())

    if not images:
        run.status = RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        return {"processed": 0, "failed": 0, "detections": 0, "message": "No pending images"}

    logger.info(f"Processing {len(images)} images for run {run_id}")

    processed = 0
    failed = 0
    total_detections = 0
    start_time = time.time()

    for image in images:
        try:
            image.processing_status = ProcessingStatus.PROCESSING
            await db.flush()

            # Resolve the image file path
            image_path = settings.upload_dir / str(run_id) / image.stored_filename
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Run YOLO inference
            raw_detections = inference_service.detect(str(image_path))

            # Flag images with no detections — likely not a road photo
            if not raw_detections:
                image.error_message = "no_road_damage_detected"
                logger.info(
                    f"No detections in {image.original_filename} — "
                    "image may not contain road damage or may not be a road photo"
                )

            # Create Detection records
            for det in raw_detections:
                detection = Detection(
                    detection_id=generate_detection_id(),
                    inspection_run_id=run_id,
                    image_id=image.id,
                    damage_type=det["label"],
                    class_id=det["class_id"],
                    confidence=det["confidence"],
                    x_min=det["x_min"],
                    y_min=det["y_min"],
                    x_max=det["x_max"],
                    y_max=det["y_max"],
                    center_x=det["center_x"],
                    center_y=det["center_y"],
                    latitude=image.latitude,
                    longitude=image.longitude,
                    location_method=image.location_method.value if image.latitude else "unmapped",
                    review_status=ReviewStatus.UNREVIEWED,
                    model_version=inference_service.model_version,
                )
                db.add(detection)
                total_detections += 1

            image.processing_status = ProcessingStatus.COMPLETED
            processed += 1

        except Exception as e:
            logger.error(f"Failed to process image {image.id} ({image.original_filename}): {e}")
            image.processing_status = ProcessingStatus.FAILED
            image.error_message = str(e)[:1000]
            failed += 1

        # Periodic flush to avoid huge transactions
        if (processed + failed) % 50 == 0:
            await db.flush()

    # Final status update
    elapsed = time.time() - start_time
    run.processed_images = processed
    run.failed_images = failed
    run.total_detections = total_detections
    run.status = RunStatus.COMPLETED
    run.completed_at = datetime.utcnow()

    await db.flush()

    summary = {
        "processed": processed,
        "failed": failed,
        "detections": total_detections,
        "elapsed_seconds": round(elapsed, 1),
        "model_version": inference_service.model_version,
    }

    logger.info(
        f"Run {run_id} complete: {processed} processed, {failed} failed, "
        f"{total_detections} detections in {elapsed:.1f}s"
    )

    return summary

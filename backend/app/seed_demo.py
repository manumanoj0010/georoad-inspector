"""Seed script — loads demo images and runs the pipeline for demo mode.

Usage:
    cd backend
    python -m app.seed_demo

This creates a demo inspection run with pre-processed detections so the
application works immediately without manual upload.
"""

import asyncio
import logging
import shutil
from pathlib import Path

from app.config import settings
from app.database import async_session, init_db
from app.models.inspection_run import InspectionRun, RunStatus
from app.models.image import Image, LocationMethod, ProcessingStatus
from app.services.exif import extract_metadata
from app.services.inference import inference_service
from app.services.processing import process_inspection_run
from app.utils.file_validation import generate_stored_filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Demo images source — use samples from the old project
DEMO_SOURCE = Path(__file__).parent.parent.parent.parent / "road-asset-detector" / "data" / "sample_images"
DEMO_LIMIT = 10  # Use up to this many images for demo


async def seed_demo():
    """Create a demo inspection run with pre-processed results."""
    await init_db()

    # Check for demo images
    if not DEMO_SOURCE.exists():
        logger.error(f"Demo image source not found: {DEMO_SOURCE}")
        logger.info("Run the road-asset-detector create_sample_data.py first, or provide demo images.")
        return

    demo_images = sorted(DEMO_SOURCE.glob("*.jpg"))[:DEMO_LIMIT]
    if not demo_images:
        logger.error("No JPEG images found in demo source directory.")
        return

    logger.info(f"Found {len(demo_images)} demo images")

    async with async_session() as db:
        # Create demo run
        run = InspectionRun(name="Demo: US Road Inspection", status=RunStatus.UPLOADING)
        db.add(run)
        await db.flush()
        await db.refresh(run)
        run_id = run.id

        logger.info(f"Created demo run: id={run_id}")

        # Set up upload directory
        upload_dir = settings.upload_dir / str(run_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Copy and register images
        for i, src_path in enumerate(demo_images):
            stored_name = generate_stored_filename(src_path.name, run_id, i)
            dest_path = upload_dir / stored_name
            shutil.copy(src_path, dest_path)

            meta = extract_metadata(str(dest_path))

            image = Image(
                inspection_run_id=run_id,
                original_filename=src_path.name,
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
                location_method=LocationMethod.CAMERA_EXIF if meta.has_gps else LocationMethod.UNMAPPED,
                processing_status=ProcessingStatus.PENDING,
            )
            db.add(image)

        run.total_images = len(demo_images)
        await db.flush()
        logger.info(f"Uploaded {len(demo_images)} demo images")

        # Run YOLO inference
        logger.info("Running YOLO inference on demo images...")
        if not inference_service.is_loaded:
            inference_service.load_model()

        summary = await process_inspection_run(run_id, db)
        await db.commit()

        logger.info(f"Demo seed complete!")
        logger.info(f"  Run ID: {run_id}")
        logger.info(f"  Images: {summary['processed']}")
        logger.info(f"  Detections: {summary['detections']}")
        logger.info(f"  Model: {summary['model_version']}")
        logger.info(f"\nStart the server and visit http://localhost:5173")


if __name__ == "__main__":
    asyncio.run(seed_demo())

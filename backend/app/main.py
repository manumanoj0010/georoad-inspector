"""GeoRoad Inspector — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("Starting GeoRoad Inspector API...")
    # Create tables (dev mode — use Alembic migrations in production)
    await init_db()
    logger.info(f"Database initialized: {settings.database_url}")

    # Ensure upload directory exists
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory: {settings.upload_dir}")

    # Load YOLO model into memory
    from app.services.inference import inference_service
    try:
        inference_service.load_model()
    except FileNotFoundError:
        logger.warning("YOLO model not found — inference will fail until model is available")

    yield

    logger.info("Shutting down GeoRoad Inspector API.")


app = FastAPI(
    title="GeoRoad Inspector",
    description="AI-powered road damage detection and GIS mapping API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images as static files
# StaticFiles requires directory existence at import time.
settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

# Register routers
from app.routers import inspections, images, processing, detections, geojson, arcgis  # noqa: E402

app.include_router(inspections.router)
app.include_router(images.router)
app.include_router(processing.router)
app.include_router(detections.router)
app.include_router(geojson.router)
app.include_router(arcgis.router)


# Health checks
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready", "env": settings.app_env}

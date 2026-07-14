"""YOLO Inference Service — Hugging Face Docker Space deployment.

Lightweight FastAPI service that loads a YOLO model and exposes
a /detect endpoint for remote inference. Designed to run on
Hugging Face Docker Spaces.

The main GeoRoad Inspector backend calls this service when
INFERENCE_SERVICE_URL is configured, keeping the API server
lightweight (no PyTorch/YOLO in memory).
"""

import logging
import time
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_PATH = Path("./models/road_damage_best.pt")

app = FastAPI(
    title="GeoRoad Inspector — Inference Service",
    description="YOLO road damage detection endpoint for Hugging Face Spaces",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Load model once at startup
model: YOLO | None = None
model_version: str = ""
class_mapping: dict[int, str] = {}


@app.on_event("startup")
def load_model():
    """Load YOLO model into memory at startup."""
    global model, model_version, class_mapping

    if not MODEL_PATH.exists():
        logger.error(f"Model weights not found at {MODEL_PATH}")
        return

    logger.info(f"Loading YOLO model from {MODEL_PATH}")
    start = time.time()
    model = YOLO(str(MODEL_PATH))
    elapsed = time.time() - start

    class_mapping = dict(model.names)
    model_version = MODEL_PATH.stem

    logger.info(f"Model loaded in {elapsed:.2f}s — version: {model_version}")
    logger.info(f"Classes: {class_mapping}")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_version": model_version,
        "classes": class_mapping,
    }


@app.post("/detect")
async def detect(
    file: UploadFile = File(...),
    confidence: float = Query(0.25, ge=0.0, le=1.0),
    iou: float = Query(0.45, ge=0.0, le=1.0),
):
    """
    Run YOLO detection on an uploaded image.

    Returns a list of detections with bounding boxes,
    class labels, and confidence scores.
    """
    if model is None:
        return {"error": "Model not loaded", "detections": [], "model_version": ""}

    # Read uploaded image into a temp file for YOLO
    contents = await file.read()

    # Validate it is a real image
    try:
        img = Image.open(BytesIO(contents))
        img.verify()
    except Exception:
        return {"error": "Invalid image file", "detections": [], "model_version": ""}

    with NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
        tmp.write(contents)
        tmp.flush()

        start = time.time()
        results = model(tmp.name, conf=confidence, iou=iou, verbose=False)
        inference_ms = (time.time() - start) * 1000

    detections = []
    result = results[0]

    for box in result.boxes:
        class_id = int(box.cls[0])
        label = result.names[class_id]
        conf_score = float(box.conf[0])
        x_min, y_min, x_max, y_max = box.xyxy[0].tolist()

        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        width = x_max - x_min
        height = y_max - y_min

        detections.append({
            "class_id": class_id,
            "label": label,
            "confidence": round(conf_score, 4),
            "x_min": round(x_min, 1),
            "y_min": round(y_min, 1),
            "x_max": round(x_max, 1),
            "y_max": round(y_max, 1),
            "center_x": round(center_x, 1),
            "center_y": round(center_y, 1),
            "width": round(width, 1),
            "height": round(height, 1),
        })

    logger.info(
        f"Inference: {file.filename} → {len(detections)} detections in {inference_ms:.0f}ms"
    )

    return {
        "detections": detections,
        "model_version": model_version,
        "inference_ms": round(inference_ms, 1),
    }

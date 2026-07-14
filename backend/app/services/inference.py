"""YOLO inference service — loads the model and runs detection on images.

Adapted from the original detect.py module. Designed as a singleton service
that loads model weights once at startup and processes images on demand.
"""

import logging
import time
from pathlib import Path

from ultralytics import YOLO

from app.config import settings

logger = logging.getLogger(__name__)


class InferenceService:
    """Manages YOLO model loading and inference."""

    def __init__(self):
        self._model: YOLO | None = None
        self._model_version: str = ""
        self._class_mapping: dict[int, str] = {}

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def class_mapping(self) -> dict[int, str]:
        return self._class_mapping

    def load_model(self, weights_path: str | Path | None = None) -> None:
        """
        Load YOLO model weights into memory.

        Call this once at application startup. The model stays in memory
        for fast inference across multiple requests.
        """
        path = Path(weights_path) if weights_path else settings.model_weights_path

        if not path.exists():
            logger.error(f"Model weights not found: {path}")
            raise FileNotFoundError(f"Model weights not found: {path}")

        logger.info(f"Loading YOLO model from: {path}")
        start = time.time()
        self._model = YOLO(str(path))
        elapsed = time.time() - start
        logger.info(f"Model loaded in {elapsed:.2f}s")

        # Extract class mapping from the model
        self._class_mapping = dict(self._model.names)
        self._model_version = path.stem  # e.g. "road_damage_best"

        logger.info(f"Model version: {self._model_version}")
        logger.info(f"Classes: {self._class_mapping}")

    def detect(
        self,
        image_path: str | Path,
        confidence: float | None = None,
        iou: float | None = None,
    ) -> list[dict]:
        """
        Run object detection on a single image.

        Parameters
        ----------
        image_path : path to the image file
        confidence : minimum confidence threshold (uses config default if None)
        iou : IoU threshold for NMS (uses config default if None)

        Returns
        -------
        list[dict] with keys:
            - class_id: int
            - label: str (human-readable class name)
            - confidence: float (0-1)
            - x_min, y_min, x_max, y_max: float (pixel bounding box)
            - center_x, center_y: float (box center)
            - width, height: float (box dimensions)
        """
        if not self._model:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        conf = confidence or settings.default_confidence_threshold
        iou_thresh = iou or settings.default_iou_threshold

        start = time.time()
        results = self._model(
            str(image_path),
            conf=conf,
            iou=iou_thresh,
            verbose=False,
        )
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

        logger.debug(
            f"Inference: {Path(image_path).name} → {len(detections)} detections "
            f"in {inference_ms:.0f}ms"
        )
        return detections


# Singleton instance — shared across the application
inference_service = InferenceService()

"""YOLO inference service — local or remote detection.

Supports two modes:
- Remote mode: Sends images to a Hugging Face Spaces inference service via HTTP.
  Used in production to keep the API server lightweight (no PyTorch in memory).
- Local mode: Loads YOLO weights directly. Used for local development.

The mode is determined by the INFERENCE_SERVICE_URL environment variable.
"""

import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class InferenceService:
    """Manages YOLO model loading and inference (local or remote)."""

    def __init__(self):
        self._model: Any | None = None
        self._model_version: str = ""
        self._class_mapping: dict[int, str] = {}

    @property
    def is_loaded(self) -> bool:
        if settings.remote_inference_enabled:
            return True  # Remote service manages its own model
        return self._model is not None

    @property
    def model_version(self) -> str:
        return self._model_version or "remote"

    @property
    def class_mapping(self) -> dict[int, str]:
        return self._class_mapping

    def load_model(self, weights_path: str | Path | None = None) -> None:
        """
        Load YOLO model weights into memory (local mode only).

        Skipped when remote inference is configured.
        """
        if settings.remote_inference_enabled:
            logger.info(
                f"Remote inference enabled — skipping local model load. "
                f"Service URL: {settings.inference_service_url}"
            )
            return

        path = Path(weights_path) if weights_path else settings.model_weights_path

        if not path.exists():
            logger.error(f"Model weights not found: {path}")
            raise FileNotFoundError(f"Model weights not found: {path}")

        logger.info(f"Loading YOLO model from: {path}")
        start = time.time()
        # Delay heavy Ultralytics/Torch import until inference is requested.
        from ultralytics import YOLO

        self._model = YOLO(str(path))
        elapsed = time.time() - start
        logger.info(f"Model loaded in {elapsed:.2f}s")

        self._class_mapping = dict(self._model.names)
        self._model_version = path.stem

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

        Uses remote inference service when INFERENCE_SERVICE_URL is set,
        otherwise runs local YOLO inference.

        Returns list[dict] with keys: class_id, label, confidence,
        x_min, y_min, x_max, y_max, center_x, center_y, width, height.
        """
        if settings.remote_inference_enabled:
            return self._detect_remote(image_path, confidence, iou)
        return self._detect_local(image_path, confidence, iou)

    def _detect_remote(
        self,
        image_path: str | Path,
        confidence: float | None = None,
        iou: float | None = None,
    ) -> list[dict]:
        """Send image to remote inference service and return detections."""
        conf = confidence or settings.default_confidence_threshold
        iou_thresh = iou or settings.default_iou_threshold
        url = f"{settings.inference_service_url.rstrip('/')}/detect"

        path = Path(image_path)
        start = time.time()

        with open(path, "rb") as f:
            response = httpx.post(
                url,
                files={"file": (path.name, f, "image/jpeg")},
                params={"confidence": conf, "iou": iou_thresh},
                timeout=120,
            )

        elapsed_ms = (time.time() - start) * 1000

        if response.status_code != 200:
            raise RuntimeError(
                f"Remote inference failed: HTTP {response.status_code} — {response.text[:500]}"
            )

        data = response.json()

        if "error" in data and data["error"]:
            raise RuntimeError(f"Remote inference error: {data['error']}")

        detections = data.get("detections", [])
        self._model_version = data.get("model_version", "remote")

        logger.debug(
            f"Remote inference: {path.name} → {len(detections)} detections "
            f"in {elapsed_ms:.0f}ms (includes network)"
        )
        return detections

    def _detect_local(
        self,
        image_path: str | Path,
        confidence: float | None = None,
        iou: float | None = None,
    ) -> list[dict]:
        """Run YOLO inference locally."""
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

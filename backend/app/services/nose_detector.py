"""
Nose detection service — uses YOLOv8-nano exported to ONNX.
Localizes and crops the nose region from any dog photo.
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class NoseDetector:
    """
    YOLOv8-nano ONNX nose detector.
    Detects the nose bounding box in a dog photo, then crops it out
    for downstream embedding extraction.
    """

    def __init__(self):
        self.session = None
        self.input_name = None
        self.input_shape = None
        self._loaded = False

    def load(self):
        """Load the ONNX model. Called once at startup."""
        model_path = Path(settings.NOSE_DETECTOR_MODEL_PATH)
        if not model_path.exists():
            logger.warning(
                f"Nose detector model not found at {model_path}. "
                "Detection will be skipped — full image will be used for embedding. "
                "Train and export the YOLOv8 model to enable nose detection."
            )
            self._loaded = False
            return

        self.session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape  # e.g., [1, 3, 640, 640]
        self._loaded = True
        logger.info(f"Nose detector loaded from {model_path}")

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def detect(self, image_bytes: bytes) -> tuple[np.ndarray, tuple[int, int, int, int] | None]:
        """
        Detect and crop the nose region from an image.

        Args:
            image_bytes: Raw JPEG/PNG bytes

        Returns:
            (cropped_nose_image, bbox) where bbox is (x1, y1, x2, y2) or None
            If no model loaded or no nose detected, returns (original_image, None)
        """
        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode image")

        if not self._loaded:
            # No model available — return full image (Phase 1 fallback)
            logger.debug("Nose detector not loaded, using full image")
            return img, None

        h, w = img.shape[:2]

        # Preprocess for YOLO: resize to model input size, normalize
        input_h, input_w = self.input_shape[2], self.input_shape[3]
        resized = cv2.resize(img, (input_w, input_h))
        blob = resized.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)  # HWC → CHW
        blob = np.expand_dims(blob, axis=0)  # Add batch dimension

        # Run inference
        outputs = self.session.run(None, {self.input_name: blob})
        detections = outputs[0]  # Shape depends on YOLO version

        # Parse detections — find highest confidence nose
        best_bbox = None
        best_conf = 0.0

        if detections is not None and len(detections) > 0:
            # YOLOv8 output shape: [1, num_detections, 6] → [x1, y1, x2, y2, confidence, class]
            for det in detections[0]:
                conf = float(det[4])
                if conf > best_conf and conf > 0.5:
                    best_conf = conf
                    # Scale coordinates back to original image size
                    x1 = int(det[0] * w / input_w)
                    y1 = int(det[1] * h / input_h)
                    x2 = int(det[2] * w / input_w)
                    y2 = int(det[3] * h / input_h)
                    # Clamp to image bounds
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    best_bbox = (x1, y1, x2, y2)

        if best_bbox:
            x1, y1, x2, y2 = best_bbox
            # Add a small margin around the nose for context
            margin_x = int((x2 - x1) * 0.1)
            margin_y = int((y2 - y1) * 0.1)
            x1 = max(0, x1 - margin_x)
            y1 = max(0, y1 - margin_y)
            x2 = min(w, x2 + margin_x)
            y2 = min(h, y2 + margin_y)
            cropped = img[y1:y2, x1:x2]
            logger.debug(f"Nose detected at ({x1},{y1})-({x2},{y2}), conf={best_conf:.3f}")
            return cropped, (x1, y1, x2, y2)
        else:
            logger.warning("No nose detected in image — using full image as fallback")
            return img, None


# Singleton instance
nose_detector = NoseDetector()

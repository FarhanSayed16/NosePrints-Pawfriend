"""
Stage-1 dog detector — COCO YOLOv8n ONNX (class 16 = dog).

Finds the dog (or head-biased crop) so Stage-2 nose YOLO runs on a tight
region instead of a tiny nose lost in a full street scene.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from app.config import settings
from app.services.nose_detector import (
    clip_bbox,
    decode_yolov8_multiclass,
    letterbox,
)

logger = logging.getLogger(__name__)

# COCO80 class id for dog
COCO_DOG_CLASS = 16


@dataclass
class DogBox:
    bbox: tuple[int, int, int, int]  # x1,y1,x2,y2 on original image
    confidence: float


class DogDetector:
    def __init__(self) -> None:
        self.session = None
        self.input_name = None
        self.input_shape = None
        self._loaded = False

    def load(self) -> None:
        model_path = Path(settings.DOG_DETECTOR_MODEL_PATH)
        if not model_path.exists():
            logger.warning(
                "Dog detector not found at %s — two-stage detect disabled",
                model_path,
            )
            self._loaded = False
            return
        self.session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        self._loaded = True
        logger.info("Dog detector loaded from %s", model_path)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def detect(self, bgr: np.ndarray) -> DogBox | None:
        """Return best dog box on the image, or None."""
        if not self._loaded or bgr is None or bgr.size == 0:
            return None
        h, w = bgr.shape[:2]
        input_h = int(self.input_shape[2]) if self.input_shape[2] not in (None, -1) else 640
        input_w = int(self.input_shape[3]) if self.input_shape[3] not in (None, -1) else 640
        letterboxed, scale, pad = letterbox(bgr, (input_h, input_w))
        blob = letterboxed[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None, ...]
        outputs = self.session.run(None, {self.input_name: blob})
        box, conf = decode_yolov8_multiclass(
            outputs[0],
            orig_w=w,
            orig_h=h,
            scale=scale,
            pad=pad,
            conf_threshold=settings.DOG_DETECTOR_CONF,
            class_id=COCO_DOG_CLASS,
        )
        if box is None:
            return None
        return DogBox(bbox=box, confidence=conf)

    def head_roi(self, dog: DogBox, frame_h: int, frame_w: int) -> tuple[int, int, int, int]:
        """
        Expand dog box slightly, then keep the upper portion (muzzle/head bias)
        so Stage-2 nose search avoids paws/tail.
        """
        x1, y1, x2, y2 = dog.bbox
        bw, bh = x2 - x1, y2 - y1
        pad_x = int(bw * settings.DOG_CROP_PAD)
        pad_y = int(bh * settings.DOG_CROP_PAD)
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(frame_w, x2 + pad_x)
        y2 = min(frame_h, y2 + pad_y)
        # Keep top fraction of the dog box (head / upper body)
        keep = settings.DOG_HEAD_HEIGHT_FRAC
        y2 = min(frame_h, y1 + max(32, int((y2 - y1) * keep)))
        return clip_bbox((x1, y1, x2, y2), frame_w, frame_h) or (x1, y1, x2, y2)


dog_detector = DogDetector()

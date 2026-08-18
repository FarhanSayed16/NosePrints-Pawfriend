"""
Nose detection service — YOLOv8-nano exported to ONNX.
Letterbox preprocess + [1, 4+nc, N] decode (Ultralytics export layout).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    original: np.ndarray
    crop: np.ndarray | None
    bbox: tuple[int, int, int, int] | None
    confidence: float


def letterbox(
    image: np.ndarray,
    new_shape: tuple[int, int] = (640, 640),
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize and pad to a square, matching Ultralytics YOLO preprocess."""
    h, w = image.shape[:2]
    target_h, target_w = new_shape
    scale = min(target_h / h, target_w / w)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    pad_w = (target_w - new_w) / 2
    pad_h = (target_h - new_h) / 2
    top, bottom = int(round(pad_h - 0.1)), int(round(pad_h + 0.1))
    left, right = int(round(pad_w - 0.1)), int(round(pad_w + 0.1))
    padded = cv2.copyMakeBorder(
        resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return padded, scale, (left, top)


def _to_predictions(raw: np.ndarray) -> np.ndarray:
    """
    Normalize YOLO ONNX output to [num_boxes, 4+nc].

    Ultralytics detect export is typically [1, 4+nc, num_anchors].
    Older layouts may be [1, num_anchors, 4+nc] or [1, num_anchors, 6].
    """
    pred = raw[0] if raw.ndim == 3 else raw
    if pred.ndim != 2:
        raise ValueError(f"Unexpected YOLO output shape: {raw.shape}")
    # Channels-first if the small dimension is 4+nc (5 for a single class)
    if pred.shape[0] <= 16 and pred.shape[1] > pred.shape[0]:
        pred = pred.T
    return pred.astype(np.float32)


def nms_xyxy(
    boxes: np.ndarray,
    scores: np.ndarray,
    iou_threshold: float = 0.45,
) -> list[int]:
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou <= iou_threshold]
    return keep


def decode_yolov8(
    output: np.ndarray,
    *,
    orig_w: int,
    orig_h: int,
    scale: float,
    pad: tuple[float, float],
    conf_threshold: float,
    iou_threshold: float = 0.45,
) -> tuple[tuple[int, int, int, int] | None, float]:
    """Return best (x1,y1,x2,y2) in original image pixels, plus confidence."""
    pred = _to_predictions(output)
    if pred.shape[1] < 5:
        raise ValueError(f"YOLO prediction width {pred.shape[1]} < 5")

    cx, cy, bw, bh = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
    class_scores = pred[:, 4:]
    conf = class_scores.max(axis=1)
    mask = conf >= conf_threshold
    if not np.any(mask):
        return None, 0.0

    cx, cy, bw, bh, conf = cx[mask], cy[mask], bw[mask], bh[mask], conf[mask]
    x1 = cx - bw / 2
    y1 = cy - bh / 2
    x2 = cx + bw / 2
    y2 = cy + bh / 2
    boxes = np.stack([x1, y1, x2, y2], axis=1)

    keep = nms_xyxy(boxes, conf, iou_threshold)
    if not keep:
        return None, 0.0

    best_i = keep[0]  # highest score remains first after NMS on sorted order
    # Re-pick the actual highest among kept
    best_i = max(keep, key=lambda i: float(conf[i]))
    box = boxes[best_i]
    best_conf = float(conf[best_i])

    pad_x, pad_y = pad
    box[0] = (box[0] - pad_x) / scale
    box[1] = (box[1] - pad_y) / scale
    box[2] = (box[2] - pad_x) / scale
    box[3] = (box[3] - pad_y) / scale

    return clip_bbox(box, orig_w, orig_h), best_conf


def clip_bbox(
    box: np.ndarray | tuple[float, float, float, float],
    orig_w: int,
    orig_h: int,
) -> tuple[int, int, int, int] | None:
    x1i = int(np.clip(box[0], 0, orig_w - 1))
    y1i = int(np.clip(box[1], 0, orig_h - 1))
    x2i = int(np.clip(box[2], 0, orig_w - 1))
    y2i = int(np.clip(box[3], 0, orig_h - 1))
    if x2i <= x1i or y2i <= y1i:
        return None
    return (x1i, y1i, x2i, y2i)


def shift_bbox(
    bbox: tuple[int, int, int, int],
    *,
    dx: int,
    dy: int,
    orig_w: int,
    orig_h: int,
) -> tuple[int, int, int, int] | None:
    """Map a box from a padded canvas back onto the original image."""
    x1, y1, x2, y2 = bbox
    return clip_bbox((x1 + dx, y1 + dy, x2 + dx, y2 + dy), orig_w, orig_h)


MAX_DETECT_EDGE = 1280


def _downscale_for_detect(img: np.ndarray) -> tuple[np.ndarray, float]:
    """Shrink huge phone photos before ONNX so tunnel uploads stay fast."""
    orig_h, orig_w = img.shape[:2]
    edge = max(orig_h, orig_w)
    if edge <= MAX_DETECT_EDGE:
        return img, 1.0
    scale = MAX_DETECT_EDGE / edge
    new_w = max(1, int(round(orig_w * scale)))
    new_h = max(1, int(round(orig_h * scale)))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def _scale_bbox(bbox: tuple[int, int, int, int], inv_scale: float) -> tuple[int, int, int, int]:
    if inv_scale == 1.0:
        return bbox
    return tuple(int(round(v * inv_scale)) for v in bbox)


class NoseDetector:
    """YOLOv8-nano ONNX nose detector."""

    def __init__(self):
        self.session = None
        self.input_name = None
        self.input_shape = None
        self._loaded = False

    def load(self):
        model_path = Path(settings.NOSE_DETECTOR_MODEL_PATH)
        if not model_path.exists():
            logger.warning(
                f"Nose detector model not found at {model_path}. "
                "Train with ml/training/train_detector.py and copy nose_detector.onnx."
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
        logger.info(f"Nose detector loaded from {model_path} input={self.input_shape}")

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def _infer(
        self,
        img: np.ndarray,
        conf_threshold: float,
    ) -> tuple[tuple[int, int, int, int] | None, float]:
        orig_h, orig_w = img.shape[:2]
        input_h = int(self.input_shape[2]) if self.input_shape[2] not in (None, -1) else 640
        input_w = int(self.input_shape[3]) if self.input_shape[3] not in (None, -1) else 640

        letterboxed, scale, pad = letterbox(img, (input_h, input_w))
        blob = letterboxed[:, :, ::-1].astype(np.float32) / 255.0  # BGR → RGB
        blob = np.transpose(blob, (2, 0, 1))[None, ...]

        outputs = self.session.run(None, {self.input_name: blob})
        return decode_yolov8(
            outputs[0],
            orig_w=orig_w,
            orig_h=orig_h,
            scale=scale,
            pad=pad,
            conf_threshold=conf_threshold,
        )

    def detect(self, image_bytes: bytes) -> DetectionResult:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")

        if not self._loaded:
            return DetectionResult(original=img, crop=None, bbox=None, confidence=0.0)

        orig_h, orig_w = img.shape[:2]
        work_img, detect_scale = _downscale_for_detect(img)
        inv_scale = 1.0 / detect_scale
        work_h, work_w = work_img.shape[:2]
        primary_conf = settings.DETECTOR_CONF_THRESHOLD
        retry_conf = settings.DETECTOR_RETRY_CONF_THRESHOLD
        pad_frac = settings.DETECTOR_CLOSEUP_PAD

        bbox, conf = self._infer(work_img, primary_conf)

        # YOLO often misses noses that already fill the frame. Pad and retry.
        if bbox is None and pad_frac > 0:
            ph = max(1, int(round(work_h * pad_frac)))
            pw = max(1, int(round(work_w * pad_frac)))
            padded = cv2.copyMakeBorder(
                work_img, ph, ph, pw, pw, cv2.BORDER_CONSTANT, value=(114, 114, 114)
            )
            bbox_p, conf_p = self._infer(padded, primary_conf)
            if bbox_p is not None:
                bbox = shift_bbox(bbox_p, dx=-pw, dy=-ph, orig_w=work_w, orig_h=work_h)
                conf = conf_p

        if bbox is None and retry_conf < primary_conf:
            bbox, conf = self._infer(work_img, retry_conf)

        if bbox is not None:
            bbox = _scale_bbox(bbox, inv_scale)

        if bbox is None:
            logger.info("No nose detected")
            return DetectionResult(original=img, crop=None, bbox=None, confidence=conf)

        x1, y1, x2, y2 = bbox
        margin_x = int((x2 - x1) * 0.12)
        margin_y = int((y2 - y1) * 0.12)
        cx1 = max(0, x1 - margin_x)
        cy1 = max(0, y1 - margin_y)
        cx2 = min(orig_w, x2 + margin_x)
        cy2 = min(orig_h, y2 + margin_y)
        cropped = img[cy1:cy2, cx1:cx2]
        if cropped.size == 0:
            return DetectionResult(original=img, crop=None, bbox=None, confidence=conf)

        logger.debug(f"Nose at ({cx1},{cy1})-({cx2},{cy2}) conf={conf:.3f}")
        return DetectionResult(
            original=img,
            crop=cropped,
            bbox=(cx1, cy1, cx2, cy2),
            confidence=conf,
        )


nose_detector = NoseDetector()

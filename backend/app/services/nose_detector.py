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
from app.services.image_io import decode_bgr, map_bbox_from_rotated, rotate_bgr

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    original: np.ndarray
    crop: np.ndarray | None
    bbox: tuple[int, int, int, int] | None
    confidence: float
    dog_bbox: tuple[int, int, int, int] | None = None
    dog_confidence: float = 0.0


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
    # Ultralytics export is channels-first: [4+nc, anchors] e.g. 5 (nose) or 84 (COCO).
    # Transpose to [anchors, 4+nc] whenever the short axis looks like channels.
    if pred.shape[0] < pred.shape[1] and pred.shape[0] <= 128:
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
    """Return best box for single-class (or max-class) YOLO — nose detector."""
    return decode_yolov8_multiclass(
        output,
        orig_w=orig_w,
        orig_h=orig_h,
        scale=scale,
        pad=pad,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        class_id=None,
    )


def decode_yolov8_multiclass(
    output: np.ndarray,
    *,
    orig_w: int,
    orig_h: int,
    scale: float,
    pad: tuple[float, float],
    conf_threshold: float,
    iou_threshold: float = 0.45,
    class_id: int | None = None,
) -> tuple[tuple[int, int, int, int] | None, float]:
    """
    Return best (x1,y1,x2,y2) in original pixels.

    class_id: if set (e.g. COCO dog=16), only that class; else max over classes.
    """
    pred = _to_predictions(output)
    if pred.shape[1] < 5:
        raise ValueError(f"YOLO prediction width {pred.shape[1]} < 5")

    cx, cy, bw, bh = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
    class_scores = pred[:, 4:]
    if class_id is not None:
        if class_id >= class_scores.shape[1]:
            return None, 0.0
        conf = class_scores[:, class_id]
    else:
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

    best_i = max(keep, key=lambda i: float(conf[i]))
    box = boxes[best_i].copy()
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

    @staticmethod
    def _clahe_bgr(img: np.ndarray) -> np.ndarray:
        """Boost local contrast so dark nose leather stands out on phone shots."""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        return cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2BGR)

    def _infer_zoom_windows(
        self,
        work_img: np.ndarray,
        conf_threshold: float,
        *,
        enhance: bool = False,
    ) -> tuple[tuple[int, int, int, int] | None, float]:
        """
        Phone photos often show a whole face/body — YOLO was trained on tighter
        nose crops. Retry on face/muzzle zoom windows when full-frame misses.
        """
        work_h, work_w = work_img.shape[:2]
        source = self._clahe_bgr(work_img) if enhance else work_img
        best_bbox = None
        best_conf = 0.0

        # (width_frac, height_frac, center_x, center_y) — includes top-down
        # muzzle bias (cy ≥ 0.55) common on phone stray photos.
        windows = (
            (0.70, 0.70, 0.50, 0.42),
            (0.55, 0.55, 0.50, 0.38),
            (0.42, 0.42, 0.50, 0.36),
            (0.55, 0.55, 0.50, 0.50),
            (0.40, 0.40, 0.50, 0.55),
            (0.38, 0.38, 0.50, 0.62),  # top-down nose
            (0.32, 0.32, 0.50, 0.68),
            (0.45, 0.40, 0.45, 0.58),
            (0.45, 0.40, 0.55, 0.58),
        )
        for wf, hf, cx, cy in windows:
            bw = max(32, int(round(work_w * wf)))
            bh = max(32, int(round(work_h * hf)))
            x1 = int(round(cx * work_w - bw / 2))
            y1 = int(round(cy * work_h - bh / 2))
            x1 = max(0, min(x1, work_w - bw))
            y1 = max(0, min(y1, work_h - bh))
            x2, y2 = x1 + bw, y1 + bh
            tile = source[y1:y2, x1:x2]
            if tile.size == 0:
                continue
            bbox_t, conf_t = self._infer(tile, conf_threshold)
            if bbox_t is None:
                continue
            mapped = (
                bbox_t[0] + x1,
                bbox_t[1] + y1,
                bbox_t[2] + x1,
                bbox_t[3] + y1,
            )
            if conf_t > best_conf:
                best_conf = conf_t
                best_bbox = mapped
        return best_bbox, best_conf

    def _detect_on_work(
        self,
        work_img: np.ndarray,
        *,
        primary_conf: float,
        retry_conf: float,
        pad_frac: float,
        allow_zoom: bool = True,
    ) -> tuple[tuple[int, int, int, int] | None, float]:
        """Run full-frame / pad / retry / zoom stack on one orientation."""
        work_h, work_w = work_img.shape[:2]
        bbox, conf = self._infer(work_img, primary_conf)

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

        if bbox is None and allow_zoom:
            zoom_bbox, zoom_conf = self._infer_zoom_windows(work_img, retry_conf)
            if zoom_bbox is not None:
                bbox, conf = zoom_bbox, zoom_conf
            else:
                loose = min(retry_conf, 0.10)
                zoom_bbox, zoom_conf = self._infer_zoom_windows(work_img, loose)
                if zoom_bbox is not None:
                    bbox, conf = zoom_bbox, zoom_conf
                else:
                    zoom_bbox, zoom_conf = self._infer_zoom_windows(
                        work_img, loose, enhance=True
                    )
                    if zoom_bbox is not None:
                        bbox, conf = zoom_bbox, zoom_conf
        return bbox, conf

    def _run_nose_search(
        self,
        work_img: np.ndarray,
        *,
        primary_conf: float,
        retry_conf: float,
        pad_frac: float,
        accept_conf: float,
    ) -> tuple[tuple[int, int, int, int] | None, float]:
        """Full nose search including orientation retries on one canvas."""
        bbox, conf = self._detect_on_work(
            work_img,
            primary_conf=primary_conf,
            retry_conf=retry_conf,
            pad_frac=pad_frac,
            allow_zoom=True,
        )
        if bbox is not None and float(conf) >= accept_conf:
            return bbox, conf

        best_bbox, best_conf = bbox, conf
        for angle in (90, 180, 270):
            rotated = rotate_bgr(work_img, angle)
            rb, rc = self._detect_on_work(
                rotated,
                primary_conf=primary_conf,
                retry_conf=retry_conf,
                pad_frac=pad_frac,
                allow_zoom=True,
            )
            if rb is None or rc <= best_conf:
                continue
            mapped = map_bbox_from_rotated(
                rb,
                angle_cw=angle,
                orig_w=work_img.shape[1],
                orig_h=work_img.shape[0],
            )
            if mapped is not None:
                best_bbox, best_conf = mapped, rc
                logger.info("Nose found via %d° rotation conf=%.3f", angle, rc)
        return best_bbox, best_conf

    def detect(self, image_bytes: bytes) -> DetectionResult:
        img = decode_bgr(image_bytes)

        if not self._loaded:
            return DetectionResult(original=img, crop=None, bbox=None, confidence=0.0)

        orig_h, orig_w = img.shape[:2]
        work_img, detect_scale = _downscale_for_detect(img)
        inv_scale = 1.0 / detect_scale
        primary_conf = settings.DETECTOR_CONF_THRESHOLD
        retry_conf = settings.DETECTOR_RETRY_CONF_THRESHOLD
        pad_frac = settings.DETECTOR_CLOSEUP_PAD
        accept_conf = settings.DETECTOR_MIN_ACCEPT_CONF

        dog_bbox_orig: tuple[int, int, int, int] | None = None
        dog_conf = 0.0
        bbox: tuple[int, int, int, int] | None = None
        conf = 0.0

        # ── Stage 1: COCO dog → Stage 2 nose on head ROI ─────────────────
        if settings.DOG_STAGE1_ENABLED:
            try:
                from app.services.dog_detector import dog_detector

                if dog_detector.is_loaded:
                    dog = dog_detector.detect(work_img)
                    if dog is not None:
                        wh, ww = work_img.shape[:2]
                        hx1, hy1, hx2, hy2 = dog_detector.head_roi(dog, wh, ww)
                        dog_bbox_orig = _scale_bbox(dog.bbox, inv_scale)
                        dog_conf = float(dog.confidence)
                        head = work_img[hy1:hy2, hx1:hx2]
                        if head.size > 0 and min(head.shape[:2]) >= 32:
                            nb, nc = self._run_nose_search(
                                head,
                                primary_conf=primary_conf,
                                retry_conf=retry_conf,
                                pad_frac=pad_frac,
                                accept_conf=accept_conf,
                            )
                            if nb is not None:
                                bbox = (
                                    nb[0] + hx1,
                                    nb[1] + hy1,
                                    nb[2] + hx1,
                                    nb[3] + hy1,
                                )
                                conf = nc
                                logger.info(
                                    "Nose via two-stage dog=%.3f nose=%.3f",
                                    dog_conf,
                                    conf,
                                )
            except Exception as exc:
                logger.warning("Stage-1 dog detect skipped: %s", exc)

        # ── Fallback: full-frame nose search ONLY if Stage-1 found no dog ─
        # If a dog head was found but nose YOLO missed, full-frame search
        # often locks onto paws/shadows — keep the head-scoped result/miss.
        if (bbox is None or float(conf) < accept_conf) and dog_bbox_orig is None:
            fb, fc = self._run_nose_search(
                work_img,
                primary_conf=primary_conf,
                retry_conf=retry_conf,
                pad_frac=pad_frac,
                accept_conf=accept_conf,
            )
            if fb is not None and (bbox is None or fc > conf + 0.02):
                bbox, conf = fb, fc

        if bbox is not None:
            bbox = _scale_bbox(bbox, inv_scale)

        if bbox is None:
            logger.info("No nose detected")
            return DetectionResult(
                original=img,
                crop=None,
                bbox=None,
                confidence=conf,
                dog_bbox=dog_bbox_orig,
                dog_confidence=dog_conf,
            )

        x1, y1, x2, y2 = bbox
        margin_x = int((x2 - x1) * 0.12)
        margin_y = int((y2 - y1) * 0.12)
        cx1 = max(0, x1 - margin_x)
        cy1 = max(0, y1 - margin_y)
        cx2 = min(orig_w, x2 + margin_x)
        cy2 = min(orig_h, y2 + margin_y)
        cropped = img[cy1:cy2, cx1:cx2]
        if cropped.size == 0:
            return DetectionResult(
                original=img,
                crop=None,
                bbox=None,
                confidence=conf,
                dog_bbox=dog_bbox_orig,
                dog_confidence=dog_conf,
            )

        logger.debug(f"Nose at ({cx1},{cy1})-({cx2},{cy2}) conf={conf:.3f}")
        return DetectionResult(
            original=img,
            crop=cropped,
            bbox=(cx1, cy1, cx2, cy2),
            confidence=conf,
            dog_bbox=dog_bbox_orig,
            dog_confidence=dog_conf,
        )


nose_detector = NoseDetector()

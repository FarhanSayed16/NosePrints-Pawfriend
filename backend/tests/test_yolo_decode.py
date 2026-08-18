import numpy as np

from app.services.nose_detector import decode_yolov8, letterbox, shift_bbox, _to_predictions


def test_to_predictions_channels_first():
    raw = np.zeros((1, 5, 10), dtype=np.float32)
    pred = _to_predictions(raw)
    assert pred.shape == (10, 5)


def test_decode_picks_high_confidence_box():
    # One strong detection in 640-space: cx=320, cy=320, w=80, h=80, score=0.9
    pred = np.zeros((1, 5, 20), dtype=np.float32)
    pred[0, :, 0] = [320, 320, 80, 80, 0.91]
    pred[0, :, 1] = [10, 10, 20, 20, 0.05]
    bbox, conf = decode_yolov8(
        pred,
        orig_w=640,
        orig_h=640,
        scale=1.0,
        pad=(0.0, 0.0),
        conf_threshold=0.35,
    )
    assert bbox is not None
    x1, y1, x2, y2 = bbox
    assert x1 < 320 < x2
    assert y1 < 320 < y2
    assert conf > 0.8


def test_decode_rejects_low_confidence():
    pred = np.zeros((1, 5, 8), dtype=np.float32)
    pred[0, :, 0] = [320, 320, 80, 80, 0.1]
    bbox, conf = decode_yolov8(
        pred,
        orig_w=640,
        orig_h=640,
        scale=1.0,
        pad=(0.0, 0.0),
        conf_threshold=0.35,
    )
    assert bbox is None
    assert conf == 0.0


def test_letterbox_square_output():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    padded, scale, pad = letterbox(img, (640, 640))
    assert padded.shape[0] == 640
    assert padded.shape[1] == 640
    assert scale > 0


def test_shift_bbox_undoes_closeup_padding():
    orig_w, orig_h = 400, 300
    pw, ph = 120, 90
    # Box on the padded canvas covering the original image.
    padded_box = (pw + 10, ph + 20, pw + 200, ph + 180)
    mapped = shift_bbox(padded_box, dx=-pw, dy=-ph, orig_w=orig_w, orig_h=orig_h)
    assert mapped == (10, 20, 200, 180)


def test_shift_bbox_clips_to_original():
    mapped = shift_bbox((-20, -10, 50, 40), dx=0, dy=0, orig_w=100, orig_h=80)
    assert mapped == (0, 0, 50, 40)

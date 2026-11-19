# Gemini Batch 1 — Runtime pipeline (CURRENT code after two-stage fix)

Upload this whole folder/zip to Gemini.

## What Gemini originally asked (Batch 1)
- services/nose_detector.py
- services/capture_pipeline.py
- services/nose_heuristics.py
- services/look_gate.py
- config.py

## Extra files included (new final code)
- services/dog_detector.py     ← Stage-1 COCO dog ONNX
- services/image_io.py         ← EXIF upright decode + rotation helpers
- matching.py                  ← detect-preview uses dog_bbox for assist
- main.py                      ← loads dog_detector on startup
- eval_phone_detect.py         ← offline phone_eval runner
- GEMINI_COMPLETE_PROJECT_DOCUMENT.md ← project context

## Model files (NOT in zip — too large; tell Gemini paths)
- backend/models/nose_detector.onnx
- backend/models/dog_detector_coco.onnx
- backend/models/embedding_model.onnx

## Ask Gemini
Review this Batch 1 code (post two-stage dog→nose + look-gate dog bypass).
Suggest any further betterments only if clearly higher impact than fine-tuning Stage-2 on phone labels.
Do not ask to re-implement Stage-1 — it is already present in dog_detector.py + nose_detector.detect().

# Phase 3 — Polish (after Stage-2 promote only)

## Threshold freeze (default)

Do **not** lower these until labeled phone evidence says otherwise:

- `NOSE_MIN_LIKENESS`
- `NOSE_SOFT_MISS_MIN_LIKENESS`
- junk / skin / colorfulness caps in `backend/app/config.py`

Reason: lowering gates to pass loose snout crops pollutes pgvector and ruins matching.

## In-camera coaching

Shipped in Phase 1 via `CameraCapture` guide text:

- Fill circle with **ONLY** wet nose leather before shutter.

## Extra Stage-1 (dog-face)

Only if Phase 0 / `FAILURE_MAP.md` shows **high Stage-1 miss rate** on real dogs (COCO dog miss).  
Current baseline often shows dog found + Stage-2 miss → **do not** replace Stage-1 yet.

## Staff match UX

Separate from detector precision; schedule after field ≥2/3 crop-ready.

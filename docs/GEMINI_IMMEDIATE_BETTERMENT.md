# Immediate betterment (Gemini) — status

**Date:** 20 Nov 2026

## Applied now (restart FastAPI to load)

| Change | File | Effect |
|--------|------|--------|
| Assist box `win * 0.85`, max `0.18` edge | `nose_heuristics.py` | ~40% tighter blue box on YOLO miss |
| CLAHE on Stage-1 head before Stage-2 | `nose_detector.py` | Leather pops vs dark fur |
| Soft-block wide confirm + no sticky red | frontend (prior) | Forces Tighten; clean camera |
| Train augs: scale≈0.45, mosaic, mixup, blur | `train_detector.py` | Tiny-nose simulation from merged_v1 |
| Head-crop prep for labeling | `scripts/prep_phone_head_crops.py` | Label noses on heads, not 4K full frames |

## Do not

- Download Stanford/Oxford/PetFace for product (licence + wrong labels)
- Lower `NOSE_MIN_LIKENESS` to pass fur crops
- Re-enable full-frame nose search after dog found

## Next (smart train — this weekend)

1. Drop 30–50 real phone dog photos into `ml/data/phone_eval/` (or a field folder).
2. `prep_phone_head_crops.py` → label leather on `phone_v1/heads_to_label/`.
3. Oversample those heads 3–5× into `phone_v1/train` + empty-label negatives.
4. Fine-tune from `merged_v1` with heavy scale/mosaic (script defaults ready).
5. Promote only if `eval_phone_detect.py` / `promote_nose_onnx.py` improves.

## Retest now

Hard-refresh phone → same outdoor dog → blue box should open **tighter**.  
If still slightly loose, one Tighten tap then confirm.

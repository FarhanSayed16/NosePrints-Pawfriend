# NosePrints × PawFriend — One-pager for Gemini

**Date:** 19 Nov 2026 · **Repo:** `D:\NosePrints-Pawfriend`  
Upload **this file only** + paste the prompt at the bottom. Share code later only if Gemini asks.

---

## 1. What it is

Phone **PWA** to reunite lost/stray dogs using **nose-leather biometrics** (texture of the black/pink nose ≈ fingerprint). Not face ID, not microchips, not automatic legal ID. AI suggests matches; **staff must confirm** before owner contact. Partner framing: PawFriend.in.

**Flows:** Register (owner + dog + ≥3 nose crops + optional look photo) → Identify (nose scan → candidates / no-match) → Lost/Found → Staff review.

---

## 2. Stack (real models, not mocks)

```
Phone (React/Vite PWA)
  → FastAPI
      YOLO ONNX (find nose) → quality/junk/skin gates → ResNet50 ArcFace ONNX (512-d)
  → Supabase Postgres + pgvector (cosine search)
  → Staff JWT confirm
```

| Piece | Location |
|-------|----------|
| Frontend | `frontend/` |
| Backend | `backend/app/` |
| Detector weights | `backend/models/nose_detector.onnx` (YOLOv8n, class dog-nose) |
| Embedding weights | `backend/models/embedding_model.onnx` |
| Capture gate | `backend/app/services/capture_pipeline.py` |
| YOLO runtime | `backend/app/services/nose_detector.py` |
| Junk/leather/skin | `backend/app/services/nose_heuristics.py` |
| Look-photo soft gate | `backend/app/services/look_gate.py` |
| Train detector | `ml/training/train_detector.py` |
| Train embedding | `ml/training/train_embedding.py` |
| Detector data | `ml/data/detector/merged_v1/` + Roboflow `dog_nose_yolov8/` |
| Identity data | `ml/data/identity/{train,val}` (CVPR ~6000 dogs) |
| Phone pilot data | **Missing** (`pawfriend/` empty) |

Demo URL pattern: Cloudflare tunnel → local PC (`noseprints.farhanbuilds.in`).

---

## 3. Honest accuracy (lab only)

| Model | Data | Result | Street? |
|-------|------|--------|---------|
| YOLO detector | merged_v1 (Roboflow + negs) | mAP50 ≈ **0.54** | **Weak** on phone whole-dog / top-down |
| ArcFace embed | CVPR mirror | AUC ≈ **0.80**, rank-1 ≈ **78.6%** | Untested at scale on Indian phone noses |
| Continue-train embed | same | Slightly worse → **not shipped** | — |

**Do not claim 98–99%.** Strict demo match band ≈ cosine ≥ 0.60; staff still confirms.

---

## 4. What already works

- Real ONNX detect → embed → pgvector search → staff confirm.
- Rejects many junk cases: keyboards, blank, fabric, blurry non-nose (when gates fire).
- Client crop is a hint; server re-checks (no “accept anything” bypass).
- Human-skin heuristic + stricter soft-miss on YOLO miss.
- EXIF upright + YOLO zoom/CLAHE + 90/180/270 rotation retries.
- If YOLO misses: **heuristic assist box** in crop UI (user must tighten).

---

## 5. Current field problems (why demos still hurt)

1. **YOLO often conf ≈ 0** on real phone photos (distance, angle, whole face/body) → no “Nose found”; only a starting box.
2. Assist box often **wrong/loose** (whiskers, muzzle, paw) — not true detection.
3. **Look photo** of a real outdoor dog on concrete falsely warned as “keyboard/grid” (edge/grid heuristics).
4. Volunteers **cannot always** get 15–30 cm from a stray (danger) — product assumes close-ups too often.
5. No strong **dog-vs-human / animal** classifier — leather heuristics only.
6. Biggest data gap: **no labeled Indian phone/stray set** for fine-tune.

Correct rejects (pants, blurry keyboard) must **stay**.

---

## 6. Product constraints for any recommendation

- Only **dog nose leather** into gallery/match.
- No human noses, garbage, screens, rooms as prints.
- Respect stray safety (distance/angle).
- Prefer existing on-disk data + scripts before paid datasets.
- PetFace / non-commercial face sets = blocked for product.
- Internship timeline: prefer 1–2 week demo-complete path + clear later pilot.

---

## 7. Ask Gemini

Think broadly; mark assumptions. Return:

1. **Diagnosis** (≤10 bullets)  
2. **Option matrix** (fine-tune YOLO / two-stage dog→nose / UX multi-shot / keep assist) — effort, data, risk, stray-safety fit  
3. **Recommended plan:** this week / next / defer  
4. **ML recipe** if retrain (data mix, negatives, augs for distance/angle, RTX 4050 ~6GB hints, promote rules)  
5. **Capture UX** when user cannot safely get close  
6. **Anti-junk / anti-human** checklist  
7. **“Done enough”** criteria for demo/viva  

Primary question: best way to make nose finding usable for stray phone photos without polluting the DB or pretending lab accuracy is street accuracy.

---

## 8. Code Gemini may request later (do not upload unless asked)

```
ml/training/train_detector.py
ml/training/train_embedding.py
ml/training/build_merged_detector_v1.py
ml/training/export_onnx.py
ml/training/augmentations.py
backend/app/services/nose_detector.py
backend/app/services/capture_pipeline.py
backend/app/services/nose_heuristics.py
backend/app/services/look_gate.py
backend/app/config.py
```

Never upload: `backend/.env`, `*.onnx`, full image folders.

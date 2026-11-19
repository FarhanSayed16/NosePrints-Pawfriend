# NosePrints × PawFriend — Complete Project Document for Gemini

**Document type:** Single self-contained handoff (upload this file alone)  
**Date:** 19 November 2026  
**Repository:** `D:\NosePrints-Pawfriend`  
**Audience:** Gemini / external ML–product advisor  
**Author context:** Internship / demo project for PawFriend-style stray & lost-dog reunification in India  

If you need source code later, ask for specific paths listed in **Appendix A**. Do not assume files beyond this document unless the user uploads them.

---

# PART A — Product & objectives

## A1. One-line definition

**NosePrints** is a mobile Progressive Web App that identifies dogs by the unique texture of their **nose leather** (black/pink nose surface), similar in spirit to a human fingerprint. It helps reunite lost and stray dogs with registered owners. It is **not** face recognition, iris recognition, a microchip, or an automatic legal identity system.

## A2. Problem statement

- Stray and lost dogs in Indian cities are hard to identify visually.
- Microchips help when present and scanned; many strays have none.
- Nose leather patterns are biometric and relatively stable.
- Capture happens on **phones** in the field: poor light, motion, fear, dirt, awkward angles.
- Getting within inches of a nervous stray can be **dangerous**. Users cannot always take a perfect close-up.

## A3. Product goals

1. Let owners **register** a dog with multiple nose prints.  
2. Let volunteers/staff **identify** a found/stray dog by scanning the nose.  
3. Search a gallery and return ranked candidates with honest confidence bands.  
4. Require **human staff confirmation** before revealing owner contact (privacy + safety).  
5. Reject garbage (keyboards, screens, human faces, rooms) so the gallery stays clean.  
6. Remain honest about accuracy: lab metrics ≠ street performance; never claim 98–99%.

## A4. Non-goals

- Replacing microchips or veterinary records.  
- Fully automatic “this is Max” without staff.  
- Identifying cats or other species.  
- Claiming nationwide accuracy without a real phone pilot dataset.

## A5. Main user flows

| Flow | Steps |
|------|--------|
| **Register** | Owner details → dog profile → optional “look” (body/face) photo → **≥3** accepted nose crops → store embeddings |
| **Identify** | Capture/upload nose → crop confirm → gates → embed → search → show candidates / no-match → optional look photo for staff |
| **Lost** | Mark registered dog lost (ranking boost only, not fake score) |
| **Found intake** | After no-match, list found dog; nose embed only if gate passes |
| **Staff** | Login → review match queue → confirm/reject → registry cleanup |

## A6. Partner framing

Built for / aligned with **PawFriend.in** style shelter–community workflows. Demo historically served at `https://noseprints.farhanbuilds.in` via Cloudflare tunnel to a local PC (not permanent Cloud Run unless separately deployed).

---

# PART B — System architecture

## B1. High-level pipeline

```
Phone browser (React PWA + Vite)
        │  HTTPS (tunnel) / localhost
        ▼
FastAPI backend (uvicorn :8000)
        │
        ├─ detect-preview → suggest crop box (honest: may say “not found”)
        ├─ prepare_nose_scan (shared for register / identify / quality-check / found)
        │     1. Decode image (EXIF orientation applied)
        │     2. YOLOv8n ONNX dog-nose detect (+ pad / zoom / CLAHE / 90°–270° retries)
        │     3. Quality: sharpness, brightness, coverage rules
        │     4. Heuristics: leather likeness, edges/grid, fabric, human-skin
        │     5. Re-detect on client crop when enabled
        │     6. Reject → HTTP 422 with issues/suggestions OR accept crop
        ├─ Embedding: ResNet50 + ArcFace head → L2-normalized 512-d vector
        ├─ Match: pgvector cosine vs gallery → bands / strict demo
        └─ Staff JWT confirm → reveal owner PII

Data: Supabase PostgreSQL + pgvector
Photos (local demo): filesystem under backend/uploads/
```

## B2. Technology table

| Layer | Technology | Notes |
|-------|------------|--------|
| Frontend | React, Vite, PWA | Camera + gallery + crop editor |
| Backend | FastAPI, Python | Rate limits, staff auth, audit |
| Detector | YOLOv8-nano → ONNX | Single class: dog-nose |
| Embedding | ResNet50 + ArcFace → ONNX | 512-d, cosine similarity |
| Database | Supabase Postgres + pgvector | Project ref historically `tfzmlkpcxvkjvmiryuxo`, region `ap-south-1` |
| Auth | Staff JWT | Bootstrap admin from env if table empty |
| Storage | Local FS (S3 optional) | Demo does not require S3 |

## B3. Key runtime code paths (for later upload)

| Concern | Path |
|---------|------|
| Detect API | `backend/app/routers/matching.py` (`/match/detect-preview`, `/match/identify`) |
| Capture gate | `backend/app/services/capture_pipeline.py` |
| YOLO service | `backend/app/services/nose_detector.py` |
| Leather/junk/skin | `backend/app/services/nose_heuristics.py` |
| Look soft gate | `backend/app/services/look_gate.py` |
| Image EXIF decode | `backend/app/services/image_io.py` |
| Thresholds | `backend/app/config.py` |
| Crop UI | `frontend/src/components/NoseCropEditor.jsx` |
| Intake | `frontend/src/components/PhotoIntake.jsx` |
| JPEG/EXIF client | `frontend/src/utils/imageFile.js` |

## B4. Production model files

| File | Role |
|------|------|
| `backend/models/nose_detector.onnx` | Live detector |
| `backend/models/nose_detector.prev.onnx` | Rollback |
| `backend/models/embedding_model.onnx` | Live embedding |
| `backend/models/embedding_model.prev.onnx` | Rollback |
| `backend/models/embedding_model.candidate.onnx` | Failed continue-train — **not** production |

---

# PART C — Machine learning: data, training, metrics

## C1. Detector training

| Item | Detail |
|------|--------|
| Script | `ml/training/train_detector.py` (Ultralytics YOLO) |
| Merge builder | `ml/training/build_merged_detector_v1.py` |
| Export | `ml/training/export_onnx.py` |
| Augmentations | `ml/training/augmentations.py` |
| Base data | Roboflow Dog_nose → `ml/data/detector/dog_nose_yolov8/` |
| Merged data | `ml/data/detector/merged_v1/` (+ synthetic negatives under `ml/data/detector/negatives/`) |
| Promoted result | val **mAP50 ≈ 0.54057** (epoch 33 merged_v1) |
| Older cited test mAP50 | ~0.68 on a prior split (do not mix with street claims) |
| Ops close-up recall | ~70% with pad + lower-conf retry **on closer crops** — much worse on whole-dog phone scenes |

**Domain gap:** Training boxes are mostly **tight nose leather**. Field photos are often whole dog / face / top-down from standing height → YOLO confidence collapses to ~0.

## C2. Embedding training

| Item | Detail |
|------|--------|
| Script | `ml/training/train_embedding.py` |
| Data | CVPR 2022 Pet Biometric Challenge mirror — `ml/data/identity/train` + `val` (~6000 dog IDs) |
| Architecture | ResNet50 backbone + ArcFace head; inference ONNX is embedder |
| Lab gallery-probe | **Rank-1 ≈ 78.6%**, **AUC ≈ 0.803** |
| Metrics file | `ml/eval_results/embedding/metrics.txt` |
| Continue-train (30 ep, LR 1e-4) | AUC 0.800 / R1 78.3% → **not promoted** |
| Torch baseline | `ml/checkpoints/embedding/best_model.baseline.pt` |
| ONNX↔Torch parity | Mean cosine ≈ 0.999999 on sample |

**Lesson:** More epochs on the **same** CVPR set do not fix street accuracy. **New representative phone/pilot data** is required.

## C3. Offline experiments (production unchanged)

| Experiment | Script | Finding |
|------------|--------|---------|
| Multi-print aggregation (A/B/C/D) | `ml/training/experiment_a_multiprint.py` | Production **max** over prints is fine; mean slightly better on lab; keep max for now |
| Open-set unknown dogs | `ml/training/experiment_c_openset_prod.py` | At cosine 0.60 strict, unknown FPIR lower; keep cautious public thresholds |

## C4. Dataset inventory (honest)

| Dataset | On disk? | Use |
|---------|----------|-----|
| CVPR identity | Yes | Embedding train/eval |
| Roboflow / merged detector | Yes | YOLO train |
| Synthetic negatives | Yes | Hard negatives for detector |
| PawFriend phone pilot | **No (empty)** | Highest priority gap |
| Nexdata commercial | Quote only | No purchase assumed |
| PetFace | Blocked | Non-commercial / not nose-print ID |

**Rule:** Dog face / pose / landmark datasets ≠ nose-leather biometric identity.

## C5. Matching thresholds (config defaults)

| Setting | Typical value | Meaning |
|---------|---------------|---------|
| `MATCH_THRESHOLD` | 0.56 | “Likely” band (~5% FAR on lab ROC) |
| `MATCH_THRESHOLD_LOW` | 0.51 | “Possible” band floor (~20% FAR) |
| `MATCH_STRICT_DEMO` | often true for demos | Turns off weak “possible” public hits |
| `MATCH_THRESHOLD_STRICT` | 0.60 | Only ≥0.60 counts as match in strict mode |
| `LOST_STATUS_BOOST` | +0.03 | Ranking only; displayed score stays raw cosine |
| `TOP_K_MATCHES` | 5 | Candidates returned |

---

# PART D — Anti-garbage & “dog nose only” gates

## D1. Historical failure (fixed)

Before G0: if the client sent `pre_cropped=true` and YOLO missed, the backend could **accept the whole crop** (including keyboards). Registering “Jack” with keyboard crops then matching another keyboard produced high cosine “matches.” That full-frame fallback was removed.

## D2. Current gate stack

| Stage | Behavior |
|-------|----------|
| YOLO miss (full scene) | Reject — do not embed |
| Low detector confidence | Reject or soft-assist in preview only |
| Full-frame YOLO box on scene | Reject / force tighten |
| Quality | Sharpness/brightness floors (crop floor lower for dark leather) |
| Edge density / grid | Keyboard-like rejection |
| Colorfulness / hue spread | Fabric / rainbow junk |
| Leather center (dark or pink) | Fur / flat reject |
| Human skin score | Soft-reject peach/skin-dominant crops |
| Soft-miss on pre_cropped | Only if heuristics pass **and** likeness ≥ ~0.48 **and** low skin **and** dark center OK |
| Soft-redetect fallback | Likeness ≥ ~0.45 |
| Look gate | Soft warn on appearance photos; user may “Use anyway” |
| Register | Requires ≥3 successful nose prints |
| Staff | Must confirm before contact |

## D3. Important thresholds (detector / heuristics)

| Setting | Approx value |
|---------|--------------|
| `DETECTOR_CONF_THRESHOLD` | 0.32 |
| `DETECTOR_RETRY_CONF_THRESHOLD` | 0.15 |
| `DETECTOR_MIN_ACCEPT_CONF` | 0.28 |
| `DETECTOR_PREVIEW_SUGGEST_CONF` | 0.15 |
| `NOSE_MIN_LIKENESS` | 0.36 |
| `NOSE_MAX_HUMAN_SKIN` | 0.42 |
| `NOSE_SOFT_MISS_MIN_LIKENESS` | 0.48 |
| `LOOK_MAX_EDGE_DENSITY` | 0.12 |
| `LOOK_MAX_GRID_REGULARITY` | 0.28 |

## D4. What gates are NOT

- Not a trained **species** classifier (dog vs human vs object).  
- Not liveness / anti-spoof deep model.  
- Look gate is **not** biometric; false “keyboard” on outdoor dogs is a known field bug (concrete texture).

---

# PART E — Capture UX (current design intent)

1. User picks Camera or Gallery.  
2. Client converts to JPEG (EXIF orientation `from-image` when supported).  
3. `detect-preview` returns optional bbox + message (may be assist, not “found”).  
4. `NoseCropEditor`: drag box, pinch, −/+/Tighten/Reset, nudge pad, circular preview.  
5. Confirm crop → server `prepare_nose_scan` with `pre_cropped=true`.  
6. Failures show API message + issues + suggestions (not a generic “all failed”).  
7. Identify optional look photo: soft gate; staff use for coat/body comparison only.

**Guidance copy:** fill box with nose leather only; little muzzle OK; not eyes/whole head.

---

# PART F — Current field issues (19 Nov 2026)

These are the live pain points from phone testing on real dogs / junk.

## F1. Look photo of a real dog → “keyboard / grid”

- Soft look-gate uses edge density + grid regularity.  
- Outdoor dogs on **textured concrete** trigger the same pattern as keyboards.  
- User can still “Use anyway,” but the warning is wrong and destroys trust.  
- **Root cause:** heuristic thresholds / message not gated by “is this a dog?”  

## F2. Nose detection not precise on “proper” dog photos

- UI often shows assist messaging (“Frame the nose leather / suggested box”), **not** “Nose found.”  
- Means YOLO confidence ≈ 0 on that photo.  
- Blue box comes from **heuristics** (e.g. darkest-window), not a confident model.  
- Boxes land on whiskers, muzzle fur, paws, or are too loose.  
- User must manually tighten — hard if the dog moves or is unsafe to approach again.  

## F3. Correct rejects (keep these)

- Camera on pants / human body → no nose.  
- Blurry keyboard → uncertain / reject.  

## F4. Operational constraint (must drive the solution)

Volunteers often **cannot** safely take a 15–30 cm nose macro shot of a stray. The system must plan for:

- Greater distance  
- Top-down / side / tilted angles  
- Partial muzzle in frame  
- Then a **guided** path to a usable leather crop (zoom, multi-shot, two-stage detect, or safe approach protocol) — not pretend every user gets a studio close-up.

## F5. Mitigations already shipped (insufficient alone)

- EXIF upright decode  
- YOLO pad / multi-zoom / CLAHE / rotation 90–180–270  
- Heuristic assist bbox  
- Crop UI tighten/nudge  
- Human-skin + stricter soft-miss  
- These reduce some failures; they **do not** replace phone-domain YOLO fine-tune or a two-stage dog→nose pipeline.

---

# PART G — What is done vs open

## Done

- End-to-end PWA + FastAPI + staff confirm  
- Real detector + embedding ONNX in the live path  
- G0–G3 style junk gates + tests  
- Detector promote (merged_v1); embedding baseline kept  
- Registry junk purge tooling / past purge of demo junk dogs  
- Strict demo mode available  
- Local tunnel demo path  

## Still open / incomplete

- Reliable **phone-field nose finding** (core gap)  
- Look-gate false positives on outdoor dogs  
- Labeled **Indian phone/stray** detector + embedding pilot set  
- Durable Cloud Run hosting (optional ops)  
- Dedicated dog-vs-human / nose-vs-junk learned classifier (G4 deferred historically)  
- Nationwide accuracy claims (explicitly not ready)

---

# PART H — Enhancement options (for Gemini to rank)

## H1. Option families

| Option | Idea | Helps | Cost / risk |
|--------|------|-------|-------------|
| **A. Phone fine-tune YOLO** | Label phone failures; fine-tune from current weights with hard negatives (human nose, pavement, fur, feet) | Directly fixes “conf=0” / bad boxes | Needs labeling; GPU time on RTX 4050 |
| **B. Two-stage** | Detect dog/face first → crop → nose YOLO / leather | Works at distance before close leather | Extra model; latency; still need nose stage |
| **C. UX multi-shot / coach** | Burst frames, “move closer” meter, best-of-N | Safer when dog allows approach | Does not fix impossible distance alone |
| **D. Keep assist + staff** | Honest assist box + human tighten + staff confirm | Demo-complete interim | Not “automatic precision” |
| **E. Nose-vs-junk CNN** | After crop, binary classifier | Stronger than heuristics | Needs junk + real nose labels |
| **F. Embedding fine-tune on pilot** | After good crops exist | Match quality on Indian dogs | Useless if crops are still garbage |
| **G. Buy commercial nose data** | e.g. Nexdata | Faster volume | Cost; may not match Indian street phones |

**Priority principle already agreed internally:** **data + capture beat another CVPR-only continue-train.**

## H2. Pilot program sketch

1. Consent + 10–20 dogs, then ~50.  
2. 3–5 nose crops each, varied angle/light; tag failures into `phone-test/`.  
3. Fine-tune detector and/or embedding; promote ONNX **only if offline eval improves**.  
4. Recalibrate cosine thresholds.  
5. Keep staff confirmation forever for contact reveal.

## H3. Success criteria for “project complete enough” (demo/viva)

- Keyboard / human / bag reliably rejected.  
- Real dog close-ups: crop → gate pass → embed → search works.  
- Whole-dog phone shots: either assist to a **usable** leather crop or clear coaching — not silent wrong boxes.  
- Look photos of real dogs not falsely branded as keyboards.  
- Staff can confirm/reject; junk not flooding gallery.  
- Honest accuracy statement in viva docs (lab ~0.80 AUC; street = pilot pending).

---

# PART I — Prompt for Gemini (answer using this document)

You are a senior computer-vision and product architect. Using **only this document** (plus any code the user later pastes), do the following.

### Required output

1. **Diagnosis** — ≤10 bullets on root causes of field failures.  
2. **Option matrix** — compare A–G above (and any better option you invent); columns: solves which failure, effort, data needed, risk, fit for “cannot safely approach stray.”  
3. **Recommended plan** — Do this week / Do next (pilot) / Do not do. Pick **one primary strategy + one fallback**.  
4. **ML recipe** — If fine-tune/two-stage: dataset mix, negatives, augmentations for distance/angle, batch/epochs hints for **RTX 4050 ~6GB**, metrics, promote/rollback rules. Name which existing scripts to reuse.  
5. **Capture UX recipe** — Safe protocol when close-up is dangerous.  
6. **Anti-human / anti-garbage checklist** — what to keep, what to add.  
7. **Demo/viva “done enough” definition** — concrete checklist.  

### Constraints you must respect

- Dog nose leather only in the biometric path.  
- No PetFace / blocked licences for product.  
- Do not invent 98% accuracy.  
- Prefer on-disk Roboflow/merged/CVPR + new phone labels over random new datasets.  
- Mark creative assumptions clearly.  

### Primary question

**What is the best practical way to finish NosePrints so stray-dog phone photos (any reasonable distance/angle users can safely get) produce usable dog-nose-only biometrics, without gallery pollution, within an internship/demo timeline?**

---

# Appendix A — Code & artifact paths (provide only if Gemini asks)

```
ml/training/train_detector.py
ml/training/train_embedding.py
ml/training/build_merged_detector_v1.py
ml/training/export_onnx.py
ml/training/augmentations.py
ml/training/experiment_a_multiprint.py
ml/training/experiment_c_openset_prod.py
backend/app/services/nose_detector.py
backend/app/services/capture_pipeline.py
backend/app/services/nose_heuristics.py
backend/app/services/look_gate.py
backend/app/services/image_io.py
backend/app/config.py
backend/app/routers/matching.py
frontend/src/components/NoseCropEditor.jsx
frontend/src/components/PhotoIntake.jsx
frontend/src/utils/imageFile.js
backend/models/nose_detector.onnx
backend/models/embedding_model.onnx
ml/data/detector/dog_nose_yolov8/data.yaml
ml/eval_results/embedding/metrics.txt
```

**Do not upload:** `backend/.env`, passwords, full image trees, large `.pt`/`.onnx` unless Gemini explicitly needs a tiny sample and you accept size limits.

---

# Appendix B — Related internal docs (already summarized here)

You do **not** need to upload these if this complete document is provided:

- `docs/SYSTEM_STATUS_AND_ENHANCEMENT_PLAN.md`  
- `docs/ACCURACY.md`  
- `docs/DATASET_INVENTORY.md`  
- `docs/GARBAGE_PHOTO_FALSE_MATCH_PLAN.md`  
- `docs/G0_G3_AUDIT_FIXES.md`  
- `docs/NEXT_ML_DECISION_REPORT.md`  
- `docs/CAPTURE_UX.md`  
- `docs/ML_PILOT_PROGRAM.md`  
- `docs/VIVA_EXPLANATION_GUIDE.md`  

---

**End of complete project document.**

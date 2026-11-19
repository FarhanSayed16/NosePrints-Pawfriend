# NosePrints — Gemini briefing: field detection, junk rejection, completion path

**Date:** 19 November 2026  
**Audience:** Gemini (strategic ML + product analysis)  
**Repo root:** `D:\NosePrints-Pawfriend`  
**Companion files:** [`GEMINI_PROMPT.md`](./GEMINI_PROMPT.md) · [`GEMINI_UPLOAD_CHECKLIST.md`](./GEMINI_UPLOAD_CHECKLIST.md)

---

## 1. What the project is

**NosePrints × PawFriend** is a phone Progressive Web App that helps reunite lost and stray dogs by comparing **nose-leather prints** (biometric texture of the black/pink nose), similar in spirit to a fingerprint — **not** face recognition, not microchips, not automatic legal ID.

| Stakeholder need | How NosePrints responds |
|------------------|-------------------------|
| Find if a stray is already registered | Scan nose → gallery search → staff confirm |
| Register owned dogs | ≥3 accepted nose crops + optional look photo |
| Safety / liability | AI suggests; **humans** confirm before owner contact |
| India street reality | Phones, uneven light, dirty noses, nervous dogs |

Partner framing: complements [PawFriend.in](https://pawfriend.in).

---

## 2. Objectives (success definition)

1. **Capture** usable dog-nose leather from phones (camera/gallery).  
2. **Reject** non-dog and non-nose content before embedding/storage.  
3. **Match** against a gallery with honest scores + staff review.  
4. **Demo** a working HTTPS path (currently Cloudflare tunnel → local PC).  
5. Stay honest: lab accuracy ≠ street accuracy; never claim 98–99%.

---

## 3. Current architecture (runtime)

```
Phone PWA (React/Vite)
  → detect-preview (suggest crop box)
  → user confirms crop
  → quality-check / prepare_nose_scan
       YOLO ONNX (dog-nose)
       quality + leather/junk/human-skin heuristics
       re-detect on crop
  → ResNet50 ArcFace ONNX → 512-d L2 vector
  → Supabase Postgres + pgvector cosine search
  → MatchLog → staff JWT confirm → reveal contact
```

| Component | Path / tech | Role |
|-----------|-------------|------|
| Frontend | `frontend/` | Camera, crop editor, identify/register |
| Backend | `backend/app/` | FastAPI routes + gates |
| Detector | `backend/models/nose_detector.onnx` | YOLOv8n single class `dog-nose` |
| Embedding | `backend/models/embedding_model.onnx` | 512-d ArcFace embedder |
| DB | Supabase project `tfzmlkpcxvkjvmiryuxo` (ap-south-1) | Gallery + staff |
| Capture pipeline | `backend/app/services/capture_pipeline.py` | Hard gate before embed |
| Heuristics | `backend/app/services/nose_heuristics.py` | Leather / keyboard / skin |
| Look gate | `backend/app/services/look_gate.py` | Soft warn on appearance photos |
| Detector service | `backend/app/services/nose_detector.py` | YOLO + zoom + rotation retries |

Models are **real ONNX**, not mocks. Photos for local demo are filesystem-backed.

---

## 4. Model training (what exists)

### Detector (YOLO)

| Item | Detail |
|------|--------|
| Train script | `ml/training/train_detector.py` |
| Merge/build | `ml/training/build_merged_detector_v1.py` |
| Export | `ml/training/export_onnx.py` |
| Primary data | `ml/data/detector/dog_nose_yolov8/` (Roboflow) |
| Merged set | `ml/data/detector/merged_v1/` (+ synthetic negatives) |
| Lab result | val mAP50 ≈ **0.54** (promoted merged_v1) |
| Gap | Trained mostly on **tight nose boxes**, not Indian phone whole-dog / top-down stray shots |

### Embedding (ArcFace)

| Item | Detail |
|------|--------|
| Train script | `ml/training/train_embedding.py` |
| Data | `ml/data/identity/{train,val}` — CVPR 2022 pet biometric mirror (~6000 dogs) |
| Lab result | AUC ≈ **0.80**, rank-1 ≈ **78.6%** |
| Continue-train | Slightly worse → **not promoted** (`embedding_model.candidate.onnx`) |
| Gap | Lab crops ≠ dirty street phone crops |

### Offline experiments (no prod change)

- Multi-print aggregation: `ml/training/experiment_a_multiprint.py`  
- Open-set: `ml/training/experiment_c_openset_prod.py`  
- Results: `docs/EXPERIMENT_A_MULTIPRINT_RESULTS.md`, `docs/EXPERIMENT_C_OPEN_SET_RESULTS.md`

**Missing critical data:** PawFriend phone pilot set (`ml/data/identity/pawfriend/` empty; no large labeled phone detector set of Indian strays).

---

## 5. Gates already built (anti-garbage)

| Gate | Purpose | Limit |
|------|---------|--------|
| YOLO accept conf | Must find a nose-like region | Misses many phone scenes |
| Quality (blur/brightness) | Reject unusable frames | Sharp keyboards can still be sharp |
| Leather / edge / grid / colorfulness | Reject keyboards, fabric, blank | Heuristic, not species ID |
| Human skin score | Soft-reject peach skin crops | Pink dog noses need care |
| Soft-miss likeness floor (raised) | YOLO miss on client crop only if strong leather | Still not a dog classifier |
| Look gate | Soft warn on appearance junk | **False alarms on concrete outdoor dogs** |
| Staff confirm | Final safety | Does not fix bad gallery pollution if junk was enrolled |

Historical lesson (fixed): `pre_cropped` used to accept full frame when YOLO missed — that caused keyboard→keyboard false matches. See `docs/GARBAGE_PHOTO_FALSE_MATCH_PLAN.md`.

---

## 6. Field issues observed (19 Nov 2026 screenshots)

### Issue A — Look photo of a real dog → “keyboard / grid”
- Soft gate uses edge density + grid regularity.  
- Textured **pavement** under outdoor dogs triggers the same pattern as keyboards.  
- User can “Use anyway”; message is still wrong and erodes trust.

### Issue B — Nose “detection” not precise on proper dog photos
- Banner often stays in **assist** mode (“suggested box / frame the leather”), not “Nose found.”  
- Means YOLO conf ≈ 0; box is heuristic.  
- Boxes land on **whiskers / muzzle / paw**, or are too loose around the leather.  
- User must manually tighten — hard when dog moves or is unsafe to approach.

### Issue C — Correct rejects (must keep)
- Camera on pants / blurry keyboard → reject. Good.

### Issue D — Operational constraint
- Volunteers **cannot always** put a phone 15–30 cm from a stray’s nose (bite risk, traffic, fear).  
- Product cannot assume studio close-ups for every identify.

---

## 7. Recent engineering mitigations (already in code)

- EXIF upright decode (client + Pillow).  
- YOLO retries: pad, zoom windows, CLAHE, **90/180/270** rotation search.  
- Darkest-window assist bbox when YOLO misses.  
- Crop UI redesign (tighten / nudge / preview).  
- Human-skin heuristic + stricter soft-miss likeness.  
- These **help**, but do **not** close the domain gap of the YOLO weights.

---

## 8. What Gemini must optimize for

1. **Stray-safe capture:** distance + angle + danger.  
2. **Dog-nose-only gallery hygiene.**  
3. **Demo-complete** path in limited time (internship).  
4. Prefer **fine-tune / two-stage / UX** using existing scripts and disks before paid datasets.  
5. Clear “done enough” criteria for viva/demo.

---

## 9. Questions we want answered

1. Best architecture for “dog far / angled / dangerous” without destroying biometric quality.  
2. Whether to invest next GPU hours in **detector fine-tune on phone data** vs two-stage dog→nose vs UX-only.  
3. Minimum labeled phone set size for a meaningful detector lift on RTX 4050.  
4. How to keep junk/human out without blocking pink dog noses.  
5. What to tell examiners honestly about accuracy vs “works for pilot.”

---

## 10. Pointers to deeper docs

| Topic | File |
|-------|------|
| System status + plan | `docs/SYSTEM_STATUS_AND_ENHANCEMENT_PLAN.md` |
| Accuracy honesty | `docs/ACCURACY.md` |
| Dataset inventory | `docs/DATASET_INVENTORY.md` |
| Garbage/false match history | `docs/GARBAGE_PHOTO_FALSE_MATCH_PLAN.md` |
| ML master plan | `docs/ML_ENHANCEMENT_MASTER_PLAN.md` |
| Next ML decisions | `docs/NEXT_ML_DECISION_REPORT.md` |
| Capture UX | `docs/CAPTURE_UX.md` |
| Viva explanation | `docs/VIVA_EXPLANATION_GUIDE.md` |
| G0–G3 audit | `docs/G0_G3_AUDIT_FIXES.md` |
| Pilot program | `docs/ML_PILOT_PROGRAM.md` |

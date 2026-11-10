# NosePrints × PawFriend — Current System Status & Enhancement Plan

**Date:** 10 November 2026  
**Purpose:** Single handoff document for humans + ChatGPT. Describes **exactly what the system is today**, what training/ops finished, honest accuracy, and a prioritized plan to make it **more accurate and robust**.  
**Repo:** `D:\NosePrints-Pawfriend`  
**Related:** `PROJECT_STATUS.md` · `ACCURACY.md` · `ML_CHANGELOG_2026-11-09.md` · `OPS_COMPLETION_STATUS.md` · `GARBAGE_PHOTO_FALSE_MATCH_PLAN.md` · `ML_ENHANCEMENT_MASTER_PLAN.md` · **`NEXT_INDEX_AND_CHATGPT_AUDIT_RESPONSE.md`** (exact next steps after ChatGPT review)

---

## 0. One-line summary

NosePrints is a **phone PWA** that identifies dogs by **nose-print biometrics**: YOLOv8n finds the nose → quality/junk gates → ResNet50 ArcFace embedding → **pgvector** cosine search → **staff must confirm** before owner contact. Models are **real ONNX** (not mock). Lab identity accuracy is ~**AUC 0.80 / rank-1 78.6%** — usable for gated demos, **below** CVPR-winner (~86.7% AUC). Free-data retrain (Nov 2026) improved/shipped detector parity; embedding continue-train did **not** beat baseline. Strict demo mode is **ON**. Gallery junk was purged.

**Do not claim 98–99% accuracy.**

---

## 1. Product definition (what it is / is not)

### Is
| Item | Detail |
|------|--------|
| Goal | Help reunite lost dogs via nose leather pattern (like a fingerprint) |
| Client | Progressive Web App (camera in browser) |
| Partner framing | Built for [PawFriend.in](https://pawfriend.in) — complement to microchips, not a replacement |
| Human-in-the-loop | AI suggests candidates; **staff confirms** before contact is shown |
| Demo URL | `https://noseprints.farhanbuilds.in` (Cloudflare tunnel → local PC) |

### Is not
- Automatic legal ID / “99% biometric”
- Retina / iris / face recognition
- Native iOS/Android app (PWA only for now)
- Trained primarily on Indian street/phone pilot dogs yet (lab data is CVPR + Roboflow)

### Main user flows
1. **Register** — owner + dog + optional “look” (body/face) photo + **≥3** accepted nose prints  
2. **Identify** — upload/scan nose → candidates or no-match → staff queue  
3. **Lost / found** — mark lost; found intake after no-match  
4. **Staff** — login, confirm/reject matches, registry cleanup  

---

## 2. Runtime architecture (current)

```
Phone / browser (React PWA on :5173, tunnel HTTPS)
        │  /api proxied to backend
        ▼
FastAPI (uvicorn :8000)
        │
        ├─ prepare_nose_scan()
        │     YOLOv8n ONNX  → bbox / reject
        │     quality + junk heuristics → reject
        │     ResNet50 ONNX → L2-normalized 512-d embedding
        │
        ├─ PostgreSQL on Supabase + pgvector (cosine search)
        │
        └─ Match bands → MatchLog → staff JWT confirm → reveal owner PII
```

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend | React + Vite PWA | `npm run tunnel` builds + serves `:5173` |
| Backend | FastAPI | Health, rate limits, staff JWT |
| DB | Supabase Postgres + `pgvector` | Restored 10 Nov 2026; was briefly `ENOTFOUND` when project paused/missing |
| Photos | Local filesystem storage | S3 optional / not required for local demo |
| Detector | `backend/models/nose_detector.onnx` | YOLOv8n, promoted from `merged_v1` |
| Embedding | `backend/models/embedding_model.onnx` | ResNet50 + ArcFace head (inference = embedder only) |
| Rollback files | `*.prev.onnx`, `embedding_model.candidate.onnx` | Present |

### Inference pipeline detail
1. JPEG upload  
2. **YOLO** nose detect (conf thresholds + pad/retry for close-ups)  
3. If client sends a crop: **re-detect / heuristics** — no “accept full frame if YOLO misses” bypass  
4. Quality: sharpness, brightness, coverage, fabric/keyboard/edge/leather-center heuristics  
5. Embed → 512-d vector  
6. Search gallery with cosine similarity  
7. Apply bands / strict mode  
8. Staff confirmation required for contact  

---

## 3. Current configuration (production-ish local demo)

From `backend/.env` (values as of 10 Nov 2026):

| Setting | Value | Effect |
|---------|------:|--------|
| `MATCH_THRESHOLD` | **0.56** | Likely band (ROC FAR~5% on lab set) |
| `MATCH_THRESHOLD_LOW` | **0.51** | Possible band floor (FAR~20%) when strict off |
| `MATCH_STRICT_DEMO` | **true** | Possible band **off** for public demo |
| `MATCH_THRESHOLD_STRICT` | **0.60** | Only ≥0.60 counts as match in strict mode |
| Models | real ONNX paths | `embedding_mode: real` on `/health` |
| Storage | local | Not S3-backed for demo |

**Live health (when API running):**  
`status: healthy` · `database: connected` · `embedding_mode: real`

---

## 4. Models & training status (honest metrics)

### 4.1 Detector (YOLOv8n)
| Item | Value |
|------|------:|
| Production file | `nose_detector.onnx` (**promoted 10 Nov 2026**) |
| Train data | `ml/data/detector/merged_v1` (Roboflow Dog_nose + synthetic negatives + offline augs) |
| Best checkpoint | `ml/checkpoints/detector_merged_v1/best_epoch33_map054.pt` |
| Best val mAP50 | **0.54057** (epoch 33) — matches prior ~0.54 |
| Prior test mAP50 | ~0.68 (older split; still cited) |
| Close-up recall (ops) | ~70% with pad + lower-conf retry |
| Rollback | `nose_detector.prev.onnx` |

### 4.2 Embedding (ResNet50 + ArcFace)
| Item | Value |
|------|------:|
| Production file | `embedding_model.onnx` (**baseline kept**) |
| Train data | CVPR 2022 Pet Biometric Challenge mirror ~**6000** dog IDs |
| Gallery-probe Rank-1 | **0.7856 (~78.6%)** |
| AUC | **0.8027 (~0.80)** |
| Metrics file | `ml/eval_results/embedding/metrics.txt` |
| Continue-train experiment | 30 epochs, LR 1e-4 from baseline → AUC **0.800** / R1 **78.3%** → **not promoted** |
| Candidate kept | `embedding_model.candidate.onnx` |
| Open-set (continued ckpt, not prod) | Unknown FAR @0.56 ≈ **6.0%** on 15% ID holdout (`open_set_continued_v1.txt`) |

### 4.3 What Free Public Track proved
- More epochs on the **same CVPR identity set** did **not** improve identity metrics.  
- Detector retrain on merged free data **held** mAP and was safe to ship.  
- **Next accuracy gains require new representative data** (real phone / pilot dogs), not another CVPR-only continue-train.

---

## 5. Anti-junk / “only dog nose” behavior (current)

### Implemented (G0–G3 + follow-ons)
| Gate | Behavior |
|------|----------|
| Shared `prepare_nose_scan` | Single path for register / identify / found / quality-check |
| YOLO miss | Reject — do not embed whole image |
| Keyboard / grid | Heuristic reject / soft-warn |
| Fabric / multi-hue / fur-like | Colorfulness / hue / leather-center checks |
| Detect-preview honesty | Does not claim “Nose found” on junk |
| Look photo | Soft-warn only (not biometric); user can “Use anyway” |
| Register | Requires ≥3 successful nose prints |
| Found intake | Embed only after nose gate passes |
| Strict demo | Suppresses weak cosine matches |

### Verified locally (synthetic fixtures, 10 Nov 2026)
Keyboard / wall / fabric → detect `detected=false`; look soft-warn; quality `passed=false`.  
Report: `docs/OPS_ACCEPTANCE_API.json` · unit tests: **50/50** pytest.

### Still imperfect (honesty for ChatGPT)
- Not a dedicated “is animal nose” deep classifier — classical heuristics + YOLO  
- Synthetic “nose-like” blobs are rejected (good), but **real phone** edge cases (mud, pink noses, extreme angle, fur close-up) need field QA  
- Look photos can still be forced with “Use anyway”  
- Cosine on two junk images is meaningless if junk ever enters the gallery — hence purge discipline  

---

## 6. Data / gallery state (after restore + purge)

| Table / item | Count / note |
|--------------|--------------|
| Dogs kept | **2** — **Max** (2 prints), **Ness** (3 prints) |
| Junk deleted | **12** dogs (incl. Jack + all 0-print rows) |
| Orphan owners cleaned | **12** |
| Staff users | 1 |
| pgvector extension | Enabled |

Supabase project ref historically: `tfzmlkpcxvkjvmiryuxo` (org linked to ChatGPT/`toteziebags@gmail.com` trail). Account was briefly missing (`ENOTFOUND`); restored and reconnecting works.

---

## 7. What is done vs still open

### Done
- [x] Product PWA + FastAPI + staff confirm  
- [x] Real detector + embedding ONNX in production paths  
- [x] G0–G3 junk gates in code + tests  
- [x] Free Public Track: detector promote; embedding experiment logged  
- [x] Strict demo ON  
- [x] Registry purge  
- [x] Frontend rebuild + local tunnel  
- [x] `/health` healthy with DB connected  

### Still open (ops / product)
- [ ] Real **phone HTTPS** acceptance checklist on `noseprints.farhanbuilds.in`  
- [ ] Cloud Run / durable hosting (needs `gcloud` + Docker Desktop)  
- [ ] Closed pilot: **10–20+** real dogs (then **≥50** for serious fine-tune)  
- [ ] Optional WhatsApp notify / `id.pawfriend.in`  

---

## 8. Enhancement plan — how to make it much more accurate & robust

Priority order is intentional: **data and capture beat more CVPR epochs**.

### P0 — Highest impact (do next)

| # | Enhancement | Why it helps | Effort |
|---|-------------|--------------|--------|
| P0.1 | **Closed pilot capture** — 10–20 dogs now; target **≥50** with 5–10 close nose photos each (angles/light) | Domain shift: lab CVPR ≠ Indian phone photos | Medium (ops) |
| P0.2 | **Fine-tune embedding** from `best_model.baseline.pt` on pilot + keep CVPR as regularizer / pretrain | Only path left that beat “same-data continue-train” plateau | High (ML) |
| P0.3 | **Re-calibrate ROC thresholds** after fine-tune; keep promote-only-if-better | Avoid shipping regressions; retune 0.56/0.51/0.60 | Low–Med |
| P0.4 | **Phone HTTPS acceptance loop** — keyboard reject, real nose accept ×3, look soft-warn; log failures into `phone-test/` | Makes gates field-true; feeds detector labels | Low |

### P1 — Robustness / fewer false accepts & misses

| # | Enhancement | Why | Effort |
|---|-------------|-----|--------|
| P1.1 | Label **detector failures** from phone-test; fine-tune YOLO on phone close-ups | Better crop → better embedding | Med |
| P1.2 | Binary **nose-vs-junk classifier** (small CNN/MobileNet) after YOLO | Stronger than heuristics alone for fur/screens | Med |
| P1.3 | **Open-set calibration** — measure unknown-dog FAR at Likely/strict; adjust or add “unknown” score | Fewer false “this is Max” on new dogs | Med |
| P1.4 | Multi-print **enrollment quality** — enforce diversity (3+ angles), reject near-duplicates | Stronger gallery templates | Low–Med |
| P1.5 | Identify-time **multi-frame / best-of-N** capture | Reduces single bad JPEG fails | Med (UX) |

### P2 — Accuracy ceiling (after P0 data exists)

| # | Enhancement | Why | Effort |
|---|-------------|-----|--------|
| P2.1 | Stronger backbone (e.g. ResNet101 / ViT / domain biometric nets) **only after** pilot data | Architecture rarely helps without data | High |
| P2.2 | Hard-negative mining + ArcFace margin/scale sweep on **pilot-aware** splits | Better separation | Med |
| P2.3 | Licensed / commercial nose corpora (e.g. Nexdata) **if** rights OK and pilot saturates | Scale IDs | Cost + legal |
| P2.4 | Session-aware gallery/probe splits; prevent leakage in eval | Trustworthy metrics | Low |

### P3 — Product / platform

| # | Enhancement | Why | Effort |
|---|-------------|-----|--------|
| P3.1 | Cloud Run + object storage (R2/S3) | Stable public demo | Med |
| P3.2 | Liveness / screen-photo detection | Spoof resistance | High |
| P3.3 | Staff override + audit tools for borderline noses | Ops safety | Low |
| P3.4 | Custom domain `id.pawfriend.in` | Branding | Low |

### Explicitly low value right now
- Another long **CVPR-only** continue-train (already tried; slight regression)  
- Claiming higher accuracy without new held-out **phone** eval  
- Buying data before verifying licence + stable `dog_id` + commercial rights  

---

## 9. Suggested success metrics (for any future model)

Promote a new embedding/detector only if **all** hold on a frozen protocol:

1. Gallery-probe **AUC** and **Rank-1** ≥ current baseline (0.803 / 0.786) on old CVPR split **or** clearly better on a new phone protocol with documented trade-offs  
2. Unknown-dog **FAR @ Likely/strict** not worse than agreed budget (e.g. ≤5–6% at 0.56, tighter under strict 0.60)  
3. Phone acceptance: junk reject rate high; real-nose accept rate acceptable on ≥20 labeled phone images  
4. No regression in `/health`, latency, or gate unit tests  
5. Staff confirm remains mandatory  

---

## 10. How to run the system today (local)

```powershell
# API
cd D:\NosePrints-Pawfriend\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (Cloudflare-friendly build)
cd D:\NosePrints-Pawfriend\frontend
npm run tunnel

# Health
Invoke-RestMethod http://127.0.0.1:8000/health
# Expect: healthy, database=connected, embedding_mode=real

# Public: https://noseprints.farhanbuilds.in  (hard-refresh phone after rebuild)
```

Staff login: `/staff` using `STAFF_BOOTSTRAP_EMAIL` / `STAFF_BOOTSTRAP_PASSWORD` from `backend/.env`.

---

## 11. Prompt block — paste this to ChatGPT

> You are advising on NosePrints, a dog nose-print biometric PWA for PawFriend.  
> Stack: React PWA → FastAPI → YOLOv8n ONNX detector → quality/junk heuristics → ResNet50 ArcFace ONNX (512-d) → Supabase pgvector cosine match → staff confirmation.  
> Current lab metrics: detector val mAP50 ≈ 0.54 (promoted merged_v1); embedding AUC ≈ 0.803, rank-1 ≈ 78.6% (baseline kept). CVPR-only continue-train did not improve. Strict demo ON (match ≥ 0.60). Junk gates exist and pass local tests; gallery purged to 2 demo dogs with prints.  
> Constraint: we cannot claim 98–99% accuracy; staff confirm stays.  
> Ask: Given this status doc, what are the **highest-ROI next experiments** to improve (1) identity accuracy on real phone photos, (2) junk rejection robustness, (3) open-set false accept — without wasting time on more same-dataset epochs? Propose a concrete 2-week and 6-week plan with data requirements, eval protocol, and promote/rollback criteria.

---

## 12. File map (where truth lives)

| Topic | Path |
|-------|------|
| This handoff | `docs/SYSTEM_STATUS_AND_ENHANCEMENT_PLAN.md` |
| Product status | `docs/PROJECT_STATUS.md` |
| Accuracy claims | `docs/ACCURACY.md` |
| Nov ML run | `docs/ML_CHANGELOG_2026-11-09.md` |
| Ops now | `docs/OPS_COMPLETION_STATUS.md` |
| Junk plan | `docs/GARBAGE_PHOTO_FALSE_MATCH_PLAN.md` |
| Longer ML plan | `docs/ML_ENHANCEMENT_MASTER_PLAN.md` |
| Deploy | `docs/DEPLOY.md` |
| Baseline metrics | `ml/eval_results/embedding/metrics.txt` |
| Continued (not prod) | `ml/eval_results/embedding/continued_v1/metrics.txt` |

---

*End of handoff. Update this file when thresholds, models, or pilot data change.*

# NosePrints × PawFriend — Project Status (One File)

**Date:** 9 November 2026  
**Purpose:** Single overview of what this project is, what is already done, what is still required for a solid demo, and what more ML training is needed next.  
**Canonical plans:** [`MASTER_PLAN.md`](./MASTER_PLAN.md) · [`ACCURACY.md`](./ACCURACY.md) · [`DEPLOY.md`](./DEPLOY.md) · [`G0_G3_AUDIT_FIXES.md`](./G0_G3_AUDIT_FIXES.md)  
**ChatGPT / senior handoff (current system + enhancement plan):** [`SYSTEM_STATUS_AND_ENHANCEMENT_PLAN.md`](./SYSTEM_STATUS_AND_ENHANCEMENT_PLAN.md)

---

## 1. What the project is about

**NosePrints** is an AI-powered **dog nose-print biometric ID** system built for [PawFriend.in](https://pawfriend.in).

A dog’s nose leather has a unique pattern (like a human fingerprint). The product lets anyone with a phone:

| Flow | What happens |
|------|----------------|
| **Register** | Owner details + dog profile + optional full-body “look” photo + **3–5 nose crops** |
| **Identify** | Scan a found dog’s nose → AI proposes candidate dogs → **staff confirms** before any owner contact is shown |
| **Lost / found** | Mark a dog lost; after no-match, create a found-dog listing |
| **Staff** | Login, match queue, confirm/reject, registry cleanup |

**Positioning:** not a microchip replacement — a free, install-nothing complement. Finders usually have a phone, not a chip scanner.

**v1 scope (locked):**
- Nose-print ID only (no retina / iris)
- Progressive Web App (browser camera), not a native app yet
- Human-in-the-loop: AI suggests, staff decides

**How the ML pipeline works at runtime:**

```
Phone camera → JPEG upload
  → YOLOv8-nano: find / crop the nose (reject if none)
  → Quality + junk heuristics on the crop
  → ResNet50 ONNX: 512-d embedding (“nose fingerprint”)
  → pgvector cosine search vs stored prints
  → Likely / Possible / No match bands
  → Staff confirms → then owner contact
```

**Local demo URL (Cloudflare tunnel):** `https://noseprints.farhanbuilds.in`  
(API on `:8000`, site on `:5173` via `npm run tunnel` — see [`DEPLOY.md`](./DEPLOY.md).)

---

## 2. What is already done (product + engineering)

### 2.1 Product / app (Phases 0–3 — in the repo)

| Area | Status |
|------|--------|
| React PWA (Register, Identify, Directory, Lost, Found intake, Staff) | Done |
| FastAPI + PostgreSQL / Supabase + pgvector | Done |
| Staff JWT auth; owner contact staff-only | Done |
| Explicit consent; privacy-safe identify responses | Done |
| Nose upload → detect → quality → embed → store | Done |
| Identify → match bands + staff confirm queue | Done |
| Report lost + found-dog intake | Done |
| Rate limits, health check (DB + models), combined register | Done |
| Capture UX (crop editor, camera, look soft-warn) | Done (iterate as needed) |
| Garbage / false-match gates (G0–G3) | Done in code — see §3 for ops leftovers |

### 2.2 Models already trained and exported

| Model | File | Training result (honest) |
|-------|------|---------------------------|
| Nose detector (YOLOv8n) | `backend/models/nose_detector.onnx` | **Promoted 10 Nov 2026** from `merged_v1` retrain — val mAP50 **0.54057** (≈ prior 0.54); prior test mAP50 **0.68**; close-up recall ~**70%** with pad + retry. Rollback: `nose_detector.prev.onnx` |
| Embedding (ResNet50 + ArcFace) | `backend/models/embedding_model.onnx` | Gallery-probe **rank-1 78.6%**, **AUC 0.803** on CVPR mirror (~6,000 dogs). Continue-train experiment **did not beat baseline** (AUC 0.800 / R1 78.3%) → **not promoted**. See [`ML_CHANGELOG_2026-11-09.md`](./ML_CHANGELOG_2026-11-09.md) |

**Production thresholds (from our ROC, not a guess):**

| Band | Cosine | Meaning |
|------|--------|---------|
| Likely | ≥ **0.56** | Strong candidate; staff still confirms |
| Possible | **0.51–0.56** | Extra caution (can disable with `MATCH_STRICT_DEMO=true`) |
| No match | < **0.51** | Empty candidates; offer found-dog intake |

**Do not claim 98–99% or “CVPR winner 86.67% AUC.”** We are **below** that bar. See [`ACCURACY.md`](./ACCURACY.md).

### 2.3 Capture / anti-junk gates already in code (G0–G3 + follow-ons)

- Shared `prepare_nose_scan` — no “accept whole image if YOLO misses”
- Detector min confidence + re-detect on client crops
- Heuristics: aspect, edges, grid (keyboards), colorfulness / hue (fabric), leather-center (dark or pink)
- Look-photo soft-warn (not biometric)
- Detect-preview honesty (don’t say “Nose found” on junk; still suggest a box when unsure)
- Register requires ≥3 successful nose prints

---

## 3. What is still required (non-ML / ops / pilot)

Live tracker for this pass: [`OPS_COMPLETION_STATUS.md`](./OPS_COMPLETION_STATUS.md).

| # | Item | Status (10 Nov 2026) |
|---|------|----------------------|
| 1 | **Purge junk dogs** | **Done** — deleted 12 junk/incomplete (incl. Jack); kept **Max** (2 prints) + **Ness** (3). Orphan owners cleaned |
| 2 | **Rebuild tunnel** | **Done locally** — `npm run tunnel` on `:5173`. Hard-refresh phone still on you |
| 3 | **Acceptance checks** | **Partial** — pytest 50/50 + local API junk gates pass. Real-phone HTTPS still needed |
| 4 | **Strict demo / DB wipe** | **Strict = ON** (`MATCH_STRICT_DEMO=true`). Targeted purge done (not full wipe) |
| 5 | **Phase 4 hosting** | **Blocked** — no `gcloud`; Docker Desktop engine not running |
| 6 | **Closed pilot:** 10–20 real dogs | **Not started** — needs consent captures |
| 7 | Optional: WhatsApp / `id.pawfriend.in` | Deferred / Phase B |

**DB:** Supabase restored — `/health` = `healthy` / `database: connected`. See [`OPS_COMPLETION_STATUS.md`](./OPS_COMPLETION_STATUS.md).

---

## 4. What is still needed for more ML training

Current models are **usable for a gated demo**, but accuracy and field robustness need more training / data. This is **Phase G4 / post-internship stretch** in the plans.

**Done (Free Public Track, 9–10 Nov 2026):** detector retrain on `merged_v1` → promoted; embedding continue-train on CVPR-only → **no win** (kept baseline). Live status / decision: [`TRAINING_LIVE.md`](./TRAINING_LIVE.md) · [`CURRENT_PROGRESS.md`](./CURRENT_PROGRESS.md).

### 4.1 Priority training work

| Priority | Work | Goal | Data needed |
|----------|------|------|-------------|
| **P0** | **Fine-tune embedding** on real PawFriend / pilot dogs | Move toward CVPR-style AUC (≥ **0.86** target); reduce false matches in the field | **≥ 50 dogs**, ideally 5–10 close nose photos each (same dog, different angles/light) — CVPR-only continue-train already tried and did not improve |
| **P0** | **Re-calibrate ROC thresholds** after fine-tune | New `MATCH_THRESHOLD` / `MATCH_THRESHOLD_LOW` from *our* val set | Held-out gallery/probe split from the new data |
| **P1** | **Phone close-up YOLO QA / labels** | Confirm promoted detector on real phones; fix residual misses | Extra labeled nose boxes from real phone photos (`ml/data/detector/phone-test/` + new labels) |
| **P1** | Visual QA on **20+ real phone photos** | Confirm crops look like leather before claiming field-ready | Put files in `ml/data/detector/phone-test/` |
| **P2** | Optional **animal / “is dog nose” classifier** | Harder reject of fur, screens, non-dog (beyond classical heuristics) | Labeled nose vs non-nose set |
| **P2** | Open-set calibration | Better “this dog is not in the DB” behavior | Impostor / unknown-dog scans |
| **P3** | Liveness / multi-frame capture | Harder to spoof with a photo of a screen | Later product risk, not internship blocker |
| **P3** | Stronger backbone / more data (Petnow-scale) | Long-term accuracy | Large proprietary or licensed nose corpora |

### 4.2 How to run more training (pointers)

**Detector (Phase 1 style):**

```powershell
# Dataset: YOLO boxes — see docs/dataset-download-guide.md
cd D:\NosePrints-Pawfriend\ml
.\.venv\Scripts\activate
cd training
python train_detector.py --epochs 40 --batch 8 --imgsz 640 --device 0
# → export/copy to backend/models/nose_detector.onnx
```

**Embedding (Phase 2 style):**

```powershell
# Dataset: per-dog folders — see docs/identity-download-guide.md
cd D:\NosePrints-Pawfriend\ml
.\.venv\Scripts\python.exe training\train_embedding.py --data_dir data\identity --epochs 50 --batch_size 16 --num_workers 0 --checkpoint_dir checkpoints\embedding
# Then evaluate.py → ROC → export_onnx → backend/models/embedding_model.onnx
```

**Fine-tune path (recommended next ML step):**
1. Collect ≥50 real dogs during the closed pilot (consent + good lighting).
2. Folder layout: `ml/data/identity/train/<dog_id>/*.jpg` and `val/...`.
3. Fine-tune from the existing ArcFace checkpoint (do not train from scratch).
4. Re-run ROC; update env thresholds; re-export ONNX; restart API.
5. Keep staff confirmation — field accuracy will still be below lab papers.

### 4.3 What more training will *not* fix by itself

- Polluted gallery (junk already stored) → **purge / wipe**, then re-register clean noses  
- Bad capture UX / wrong crop → **product + gates**, then ML  
- Claiming 99% accuracy → **honesty policy**; always staff-confirm  

---

## 5. Scorecard (honest)

| Capability | Ready to show as working? |
|------------|---------------------------|
| Register owner + dog + nose prints (with gates) | **Yes** (after purge + phone acceptance) |
| Identify with real ONNX + thresholds | **Yes as candidate suggestion** — not automatic ID |
| Staff confirm before contact | **Yes** |
| “99% accurate biometric” | **No — never claim this** |
| Field-proven on 50+ PawFriend dogs | **Not yet** — needs pilot + fine-tune |
| Production host on pawfriend.in / Cloud Run | **Phase 4** — local tunnel works; cloud deploy optional |

---

## 6. One-line summary for seniors

> NosePrints is a phone PWA that registers and matches dogs by nose print using a trained YOLO detector + ArcFace embeddings, with staff confirmation and junk-photo gates. Models are real (AUC ~0.80) but below the CVPR bar; next ML step is fine-tuning on ≥50 real dogs after a clean pilot gallery.

---

*Related deep-dives: [`MASTER_PLAN.md`](./MASTER_PLAN.md) · [`ACCURACY.md`](./ACCURACY.md) · [`GARBAGE_PHOTO_FALSE_MATCH_PLAN.md`](./GARBAGE_PHOTO_FALSE_MATCH_PLAN.md) · [`PHASE_A_DEPLOYMENT.md`](./PHASE_A_DEPLOYMENT.md) · [`task.md`](./task.md).*

# NosePrints × PawFriend — Task Tracker

Follow **[MASTER_PLAN.md](./MASTER_PLAN.md)** as the source of truth.  
This file is only a checklist. Do not mark a phase done unless that phase’s Definition of Done in the master plan is met.

**Honest status (18 Aug 2026):** Phase 0–3 product work is in the repo. Embedding rank-1 **78.6%**, AUC **0.80** — not 86%+ or 99%. Restart FastAPI so ONNX loads. Phase 4 leftover: real HTTPS host + closed 10–20 dog pilot (needs PawFriend hosting). SOP and accuracy appendix are written.

---

## Phase 0 — Freeze, honesty, safety (~5 days) 🔒
*Goal: tell the truth in the product, and stop leaking PII.*

- [x] Treat `docs/MASTER_PLAN.md` as the plan (this tracker stays in sync)
- [x] Fix frontend deps/build (`react`, `react-dom`, Vite React plugin; remove dead Vite TS starter files)
- [x] Health check actually pings Postgres + reports model file presence
- [x] Staff JWT auth on owner list/update/delete and match confirm
- [x] Strip owner contact / `owner_name` from public identify responses
- [x] Explicit consent checkbox (no auto-stamp)
- [x] Refuse identify/upload with 503 when `DEBUG=false` and embedding model missing
- [x] Combined register endpoint (no orphan owners)
- [x] Document real env/secrets (no production JWT default)

**DoD:** public identify has zero owner contact fields; owners API is staff-only; placeholder matching cannot run in non-debug. ✅

---

## Phase 1 — Capture reliability (~2 weeks) 🎯
*Goal: every stored photo is a usable nose crop.*

- [x] Download Kaggle / images.cv nose-detection datasets
- [x] Fine-tune YOLOv8-nano — **40/40 epochs** (`ml/runs/detector/yolov8n-nose`); val mAP50 **0.54**, test mAP50 **0.68**
- [x] Export detector to ONNX → `backend/models/nose_detector.onnx` (shape `[1, 5, 8400]`)
- [x] Fix YOLO post-processing to match real ONNX output shape
- [x] Close-up miss fix: pad + lower-conf retry (labeled val recall **70%**, was ~50% / 7 of 20 close-ups)
- [x] Quality checks on the **cropped nose** (sharpness, brightness, coverage) — code exists, must retarget + tune
- [x] Reject “no nose detected” (stop using the full image)
- [x] PWA camera guide overlay — ✅ already in code; keep
- [x] Client-side blur/brightness hint
- [x] Auto-capture on stable sharp frame (nice-to-have if tap-capture is already solid)
- [ ] Visual QA on 20+ real phone photos (optional remaining check — put files in `ml/data/detector/phone-test/`)

**DoD:** detector loads; crops look like noses or the API rejects; no garbage embeddings stored.

---

## Phase 2 — Real matching (~3 weeks) 🧠
*Goal: embeddings mean identity; threshold comes from ROC, not a guess.*

- [x] Confirm GPU (local RTX 4050)
- [x] Get identity data (CVPR 2022 Kaggle mirror — 6,000 dogs / 20,000 images in `ml/data/identity`)
- [x] ResNet50 + ArcFace training pipeline — ✅ code done; needs data + GPU
- [x] Train on public / collected data — **50/50 epochs**, best checkpoint epoch 48
- [x] ROC evaluation + two-band threshold — gallery-probe **AUC 0.80**, rank-1 **78.6%**; T_high **0.56**, T_low **0.51** (not the old 0.85 guess). CVPR bar was 0.86 — we are below that; do not claim 86%+
- [x] Export embedding model to ONNX — `backend/models/embedding_model.onnx`
- [x] Load real ONNX in FastAPI; **disable placeholder** — file is in place; **restart the API** so it loads (`embedding_mode` on `/health` should be `real`)
- [x] pgvector cosine search — ✅ code done; verify with held-out photos
- [x] Identify UI: side-by-side query crop vs candidate photo
- [x] Boost `status=lost` in ranking (`LOST_STATUS_BOOST=0.03`, ranking only)
- [ ] Fine-tune later on PawFriend data (after ≥50 dogs)

**DoD:** held-out same-dog scan ranks #1 **78.6% of the time** on this val set (not 100%). AUC **0.80**. `ml/eval_results/embedding/metrics.txt` exists. Staff review remains required.

---

## Phase 3 — Reunion operations (~1.5 weeks) ✨
*Goal: staff can reunite without putting phones on the public internet.*

- [x] Staff admin dashboard (match queue, confirm/reject)
- [x] Report Lost flow (status + location + note)
- [x] Found-dog intake after no-match
- [x] Email notify owner on confirmed match (SMTP optional; skipped if unset)
- [ ] WhatsApp Business API — optional, only if already approved
- [x] Owner delete also deletes stored photos
- [x] Rate limit identify + uploads
- [x] Alembic migrations (additive Phase 3 columns; DEBUG still uses `create_all` + ALTER)
- [x] Error / loading / empty states passable on phone

**DoD:** staff login → confirm → contact revealed to staff only; lost + found flows work.

---

## Phase 4 — Pilot deploy (~1 week) 🚀
*Goal: a real HTTPS URL for a closed staff pilot, not a site rewrite.*

- [ ] Host PWA + API (subdomain or subpath on pawfriend.in)
- [ ] `DEBUG=false`, CORS locked, object storage (R2/B2)
- [ ] Closed pilot: 10–20 real dogs
- [x] Staff SOP (how to capture, how to confirm, what never to share) — [`docs/STAFF_SOP.md`](./STAFF_SOP.md)
- [x] Internship write-up with ROC + limitations (no 99% claims) — [`docs/ACCURACY.md`](./ACCURACY.md)

---

## Stretch — after internship / leftover time

- [ ] Native mobile app
- [ ] On-device inference
- [ ] Liveness detection
- [ ] Multi-language (Hindi / regional)
- [ ] Community WhatsApp alerts
- [ ] HNSW index at >1000 embeddings
- [ ] Iris/retina R&D note only — **not a v1 feature**

---

## Original Phase 1 skeleton (already built — do not redo)

These were the old Weeks 1–2 items. They are **scaffolding**, not a finished biometric product.

- [x] Monorepo (`/frontend`, `/backend`, `/ml`)
- [x] FastAPI + dependencies
- [x] PostgreSQL + pgvector schema
- [x] CRUD: owners, dogs, nose_prints
- [x] S3-compatible / local photo upload
- [x] React PWA (Vite) pages
- [x] Registration UI (owner → dog → nose scan → done)
- [x] Searchable directory
- [x] Docker Compose for Postgres
- [x] Identify page (pipeline demo)
- [x] Lost Dogs listing page
- [x] Home page
- [x] Camera capture + guide overlay
- [x] Training / ONNX / ROC **scripts** (not trained models)
- [x] README quick start

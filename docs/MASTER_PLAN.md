# NosePrints × PawFriend — Master Plan

**Status:** Source of truth for this project  
**Date:** 17 August 2026  
**Audience:** Intern / builder, PawFriend mentors, future contributors  

This document replaces overlapping guidance in `docs/pawfriend-noseprint-plan.md`, `docs/implementation_plan.md`, `docs/AIML Plan.txt`, and `docs/task.md`. Those files remain useful background. **If anything conflicts, follow this file.**

---

## Where we are — start / continue here

**Phase 0 (safety freeze) is implemented.** Do not restart the project.

**Phase 1 detector is trained and exported.** Close-up misses are handled by a padded retry in FastAPI (do not retrain YOLO for that).

**Phase 2 matching is trained and wired.** Held-out rank-1 **78.6%**, AUC **0.80**. Restart FastAPI so `embedding_model.onnx` loads. Do not claim 86%+ or 99%.

**Phase 3 reunion flows are in the app** (`/staff`, report-lost, found intake). Next is Phase 4 pilot hosting.

| Decision | Locked |
|---|---|
| Product | Nose-print ID only (PWA on phone camera) |
| Retina / iris | **Dropped for v1.** No schema, UI, ML, or copy for it |
| Native app | Later. PWA first |
| Next work | **Phase 4** in `docs/task.md` (hosting + closed pilot) |

---

## 0. How to use this document

| You want to… | Go to |
|---|---|
| Know if this idea is real | Section 1 |
| Know what we are (and are not) building | Sections 2–3 |
| Know what is actually done vs claimed | Section 4 |
| Know the final product design | Sections 5–8 |
| Know the exact execution order from today | Section 9 |
| Know when a phase is finished | Section 10 |
| Know what can still kill the project | Section 11 |

**Rule:** do not start a later phase until the current phase’s Definition of Done is met. Shipping more UI on top of a fake biometric is not progress.

---

## 1. Verdict — is this possible?

**Yes. Nose-print identification is real science and a real product category.**  
**No. Retina scanning is not a v1 feature.**  
**No. The current app does not yet identify dogs by nose print.** It has a working registration/search product with a *placeholder* matching pipeline.

### Evidence that nose prints work

| Evidence | What it actually means for us |
|---|---|
| Bae et al., IEEE Access 2021 (DNNet, Yonsei) | Rank-1 ~98.97% on **curated lab datasets**. Proves uniqueness + CNN matching is valid. |
| Petnow (CES 2022 Best of Innovation) | A company already ships smartphone snout ID. We are not inventing a new biometric. |
| CVPR 2022 Pet Biometric Challenge | Winners scored **86.67% AUC on a blind test set**. This is the honest number. Use it in every demo/write-up. |
| Biology | A dog’s nose print is formed by ~2 months of age and stays stable for life. |

### Honest accuracy we should promise

| Condition | Expected result | What we tell PawFriend |
|---|---|---|
| Clean photos, trained model, same dog, good lighting | High similarity, useful top-1 | “Works well when the capture is good.” |
| Street dog, phone camera, mud, motion, bad light | Materially worse | “The model suggests candidates. A human always decides.” |
| Human staff confirms side-by-side | Effective reunions approach “good enough for NGO use” | This is the product, not a fallback. |

**Never advertise 98–99% as our production accuracy.** That is lab marketing. Our internal target is:

- Public-data AUC ≥ **0.86** (match the CVPR bar, not Petnow’s brochure)
- Field FAR (wrong dog accepted) **< 5%** at the production threshold
- Staff can review a match in under 30 seconds
- Scan-to-result latency **< 3 seconds** on CPU

### Retina / iris — drop for v1

Retina scanning needs infrared hardware, a still cooperative subject, and controlled lighting. That is the opposite of “a stranger found a street dog and opened a phone.” Keep it as a one-line future-research note only. Do not design schema, UI, or ML around it.

---

## 2. The product we are actually building

A **lightweight Progressive Web App** that PawFriend can embed into [pawfriend.in](https://pawfriend.in), so anyone with a phone can:

1. **Register** a dog with owner details + 3–5 nose photos.
2. **Identify** a found/stray dog by scanning the nose.
3. **Report lost / browse lost dogs** using the same profiles.
4. Let **PawFriend staff confirm** a match before any owner contact is revealed.

### Positioning (do not change this)

This is **not** a replacement for microchips.  
It is a **free, install-nothing complement**. Most people who find a stray have no scanner. Almost all of them have a phone.

### Two products inside one repo

Treat them as two tracks that share a database:

| Track | What it is | Value without ML | Value with ML |
|---|---|---|---|
| **A. Registry** | Owner + dog profiles, photos, lost/found status, directory | Useful for the NGO on day 1 | Same |
| **B. Biometric ID** | Nose detect → quality gate → embedding → vector search → staff confirm | Demo-only until models are trained | The internship differentiator |

Track A can go in front of PawFriend staff even if Track B is still training. Track B must not be presented as “working identification” until a trained ONNX model is loaded and evaluated.

---

## 3. What to keep, change, and drop

### Keep (the old plans got these right)

- PWA first, not a native app.
- FastAPI + PostgreSQL + pgvector + S3-compatible photos.
- Pipeline: detect nose → quality gate → 512-d embedding → cosine search.
- Multiple embeddings per dog (3–5), take the best score.
- Human confirmation before contact reveal.
- Transfer learning (do not train from scratch on a few PawFriend photos).
- ONNX on CPU for production inference (no GPU required at runtime).
- DPDP Act: consent, minimization, deletion.

### Change (old plans were incomplete or the code drifted)

| Old plan / current code | New rule |
|---|---|
| 8-week plan starting from empty repo | Rebase from **today**. Phase 1 skeleton already exists. |
| Threshold hardcoded at 0.85 | 0.85 is a placeholder. Production threshold comes from ROC on **our** val set. |
| Identify page shows `owner_name` | Public identify returns **dog visual + breed/color/status only**. Owner contact is staff-only after confirm. |
| JWT settings exist, no auth implemented | Auth is **blocking** before any public or staff use. |
| Quality checks on the full photo | Quality must run on the **cropped nose**, after detection. |
| Consent auto-stamped on create | Explicit checkbox + stored timestamp. No checkbox → no registration. |
| WhatsApp in the same week as polish | WhatsApp is **optional**. Email / in-app staff queue is the v1 notification path. |
| “List as found” mentioned, not built | No-match flow must create a **found-dog** record, not only say “try register.” |
| YOLO parser assumes `[1, N, 6]` xyxy | YOLOv8 ONNX is typically `[1, 4+nc, 8400]`. Fix parser **before** integrating a real detector. |
| One combined “internship demo” | Split **internal demo** (placeholder OK) vs **field pilot** (trained models + auth + privacy required). |

### Drop / defer

| Item | Why |
|---|---|
| Retina / iris in v1 | Hardware + subject cooperation |
| Native app in v1 | PWA covers the “found a dog on the street” case |
| On-device TFLite in v1 | Extra ML ops; server ONNX is enough |
| Liveness detection in v1 | Real risk later; not the internship bottleneck |
| Community-wide WhatsApp blast | Needs Business API approval, templates, and legal review |
| Breed classifier | Nice extra, not identification |
| Public owner directory with phones | Privacy / DPDP failure |

---

## 4. Honest audit — what is actually done

The task tracker marked Phase 1 as complete. That is **mostly true for software scaffolding** and **false for biometric capability**.

### 4.1 What is real (keep and build on)

| Area | Evidence in repo |
|---|---|
| Monorepo | `frontend/`, `backend/`, `ml/`, `docs/` |
| Local DB | `docker-compose.yml` with `pgvector/pgvector:pg16` |
| Schema | `owners`, `dogs`, `nose_prints` (vector 512), `match_logs` |
| CRUD APIs | `/api/v1/owners`, `/dogs`, `/noseprints`, `/match` |
| Photo storage | S3 client + local `uploads/` fallback |
| PWA shell | Home, Register (4-step), Identify, Directory, Lost Dogs |
| Camera | `getUserMedia`, rear camera, guide circle, multi-capture 3–5 |
| Training code | ResNet50 + ArcFace, augmentations, ROC eval, ONNX export |
| Matching code | pgvector cosine search, top-K, threshold, match log |

This is a good internship foundation. Do not rewrite it.

### 4.2 What is fake, incomplete, or unsafe

| Item | Reality | Risk if ignored |
|---|---|---|
| Embedding model | If ONNX file is missing, `_placeholder_embedding()` hashes brightness into a random 512-d vector | Two different dogs can “match.” Demos lie. |
| Nose detector | Same: no ONNX → full image used | Quality + embedding see fur/background, not nose texture |
| Quality gate | Coverage skipped when there is no bbox (always, today) | Blurry close-ups of the wrong region can pass |
| Auto-capture | Not implemented; user taps shutter | Moving dogs → blur → garbage embeddings |
| Auth | JWT libs in requirements, **no login, no roles** | Anyone can `GET /owners/` and read phones |
| Identify privacy | API returns `owner_name` to the finder | DPDP / safety failure |
| Staff confirm | Endpoint exists; **no admin UI, no staff users** | Human-in-the-loop is theoretical |
| Report Lost | Lost page only **lists** `status=lost`. No owner flow to mark lost + location | Core NGO flow missing |
| Found-dog intake | Identify no-match links to `/register` (owner form) | Finders are not owners |
| Consent | `consent_given_at` set automatically | Not real consent |
| PWA | `manifest.json` only; no service worker; icons referenced but missing | Not installable / not offline |
| Frontend deps | `package.json` has axios + react-router, **no `react` / `react-dom` / Vite React plugin listed** | Fragile installs/builds |
| Leftover Vite TS template | `counter.ts`, `main.ts`, `style.css`; build runs `tsc && vite build` | Broken production build risk |
| Migrations | Alembic in requirements; startup uses `create_all` | Production schema drift |
| Tests | pytest in requirements; **no tests** | Regressions will land in matching |
| Health check | Returns `"database": "connected"` without pinging DB | False confidence |
| YOLO decode | Parser likely wrong for real YOLOv8 ONNX | Detector “integration” will fail silently |
| `init_db` | `conn.execute("CREATE EXTENSION...")` needs SQLAlchemy `text()` | Dev startup can break |

### 4.3 Scorecard

| Capability | Code | Trained model | Safe to show PawFriend as “working”? |
|---|---|---|---|
| Register owner + dog | Yes | n/a | Yes, as a form |
| Store photos | Yes (local) | n/a | Dev only |
| Search directory | Yes | n/a | Yes |
| Scan camera UI | Yes | n/a | Yes, as a camera demo |
| Detect nose | Structure only | **No** | No |
| Real nose fingerprint | Structure only | **No** | No |
| Identify a dog | Pipeline yes, identity no | **No** | **No** — say “pipeline demo” |
| Staff review | API stub | n/a | No |
| Notify owner | No | n/a | No |
| Deployed on pawfriend.in | No | n/a | No |

---

## 5. How identification must work

Do not mix these two problems:

| Problem | Question | Difficulty | Our product |
|---|---|---|---|
| Verification (1:1) | “Is this photo the same dog as profile X?” | Easier | Useful later for “confirm this is Buddy” |
| Identification (1:N, **open-set**) | “Which registered dog is this, **if any**?” | Harder | **This is the product** |

Open-set means “no match” is a valid, common answer. A system that always returns a top-1 dog is dangerous.

### Runtime pipeline (lock this)

```
Phone camera (PWA)
    → JPEG upload
    → YOLOv8-nano: crop nose (reject if none)
    → Quality gate on CROP (sharpness, brightness, coverage)
    → ResNet50 ONNX: 512-d L2-normalized embedding
    → pgvector cosine search against all stored embeddings
    → Collapse to unique dogs (best score per dog)
    → Rank: similarity, then boost if status=lost
    → Decision:
         best >= T_high     → "likely match" (staff queue)
         T_low <= best < T_high → "possible match" (staff queue, extra caution)
         best < T_low       → "no match" → offer Found-dog intake
    → Staff sees query photo vs candidate photo(s)
    → Staff confirms
    → Only then: owner contact + notification
```

### Matching rules (lock these)

1. Store **3–5** embeddings per dog. Match against all. Keep the **max** score per dog.
2. Never return owner phone/email/address on `/match/identify`.
3. Never auto-call, auto-WhatsApp, or auto-email an owner.
4. Log every attempt in `match_logs` (query image, top dog, score, later confirm/reject).
5. Thresholds `T_high` / `T_low` come from ROC, not from this document’s 0.85 example.
6. If the embedding model is not loaded, the identify API must **refuse** with `503` in any non-debug environment. Placeholder embeddings are **dev-only**.

### Why a second threshold band

A single cutoff forces a false choice between missing real dogs and accusing the wrong owner. Two bands plus humans is how we survive field accuracy.

---

## 6. Architecture (final)

```
┌──────────────────────── PWA (React + Vite) ─────────────────────────┐
│  /register  /identify  /lost  /found-intake  /directory  /staff     │
│  Camera + guide overlay + client sharpness hint                      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS
┌──────────────────────── FastAPI ────────────────────────────────────┐
│  Public (rate-limited): register, identify, found-intake, directory │
│  Staff JWT: confirm match, view owner contact, mark lost, delete    │
│  Pipeline: detect → quality → embed → search → log                  │
└──────────────┬──────────────────────────────┬───────────────────────┘
               │                              │
     PostgreSQL + pgvector              Object storage
     owners, dogs, nose_prints,         original JPEGs only
     match_logs, staff_users            (never in Postgres)
```

### Tech stack — freeze

| Layer | Choice | Note |
|---|---|---|
| Client | React PWA (Vite) | Already started. Finish PWA properly; don’t switch to Next.js mid-internship unless pawfriend.in already is Next and integration requires it. |
| API | FastAPI | Keep. ML + API in one language. |
| Inference | ONNX Runtime CPU | Keep. |
| Training | PyTorch, ResNet50 + ArcFace | Keep as v1. Add triplet/circle loss only if AUC is below target. |
| Detector | YOLOv8-nano → ONNX | Keep. |
| DB | PostgreSQL 16 + pgvector | Keep. Add HNSW when embeddings exceed ~1,000. |
| Photos | Local in dev; Cloudflare R2 / B2 in deploy | Keep. |
| Auth | Staff JWT (already in deps) | Implement before any shared URL. |
| Notify v1 | Staff dashboard + email | WhatsApp later. |
| Host | One small VPS or Railway/Render | Don’t over-build infra. |

### Schema additions (do these; don’t redesign from scratch)

Keep existing tables. Add only what safety and flows require:

```
staff_users     (id, email, password_hash, role, created_at)
                role: staff | admin

dogs            already has last_seen_lat/lng, status
                add: found_notes TEXT NULL
                     listed_as_found_at TIMESTAMPTZ NULL

owners          add: consent_text_version VARCHAR
                     consent_ip / user_agent optional

match_logs      add: query_embedding VECTOR(512) NULL
                     staff_notes TEXT NULL
                     (query image URL already exists)

data_deletion_requests  (optional, if NGO wants a paper trail)
```

Do **not** add retina fields. Do **not** store embeddings as reversible photos. Photos stay in object storage; Postgres stores URL + vector only.

### DPDP Act 2023 — minimum bar

- Explicit consent checkbox quoting purpose: “reunite this dog with you if found.”
- Public pages never show phone, email, address.
- `DELETE /owners/{id}` must remove owner, dogs, embeddings, **and** photos from storage (today photos can be orphaned).
- Staff access is authenticated and logged.
- No training on PawFriend owner photos without the same consent covering model improvement — add one extra checkbox: “Allow PawFriend to use this nose photo to improve identification.” Default off is acceptable.

---

## 7. ML plan — the part that decides if Track B works

### 7.1 Two models, two jobs

| Model | Job | Labels needed | Hardness |
|---|---|---|---|
| YOLOv8-nano | Find the nose box | Bounding boxes only | Low |
| ResNet50 + ArcFace | Turn a nose crop into an identity embedding | Many images **per dog** | High |

If detection is weak, embedding never sees the print. Detection is the first real ML milestone, not a side task.

### 7.2 Data — with a Plan B (this is the usual project killer)

| Source | Use | Access reality | Priority |
|---|---|---|---|
| Kaggle / images.cv dog-nose YOLO sets | Train detector | Free, should work | **Do first** |
| CVPR 2022 Pet Biometric Challenge | Pretrain embedder | Original download often **dead**. Check Tianchi, Kaggle mirrors, challenge GitHub | Best if obtainable |
| Nexdata free sample | Extra embedder images | Small, free | Use |
| PawFriend captures | Fine-tune later | Yours; starts at zero | Long-term gold |
| Self-collect at NGO / campus / friends’ dogs | Bridge dataset | Tedious but reliable | **Assume you need this** |

**Plan B if CVPR data is gone:**  
Train detector on Kaggle → collect 30–80 dogs × 5–10 nose photos each (NGO + friends + shelters) → train ArcFace on that + any public sample → evaluate honestly. Accuracy will be lower than papers. That is still a valid internship result **if ROC, threshold, and human review are real.**

Do not wait weeks hoping a dead dataset link returns.

### 7.3 Training sequence

1. Detector on public bbox data → export ONNX → plug into FastAPI → verify crops look like noses.
2. Collect / download identity data in `dog_id/image.jpg` folders.
3. Train ResNet50 + ArcFace on GPU (Kaggle or Colab, not a laptop CPU).
4. Run `ml/training/evaluate.py` → save ROC, pick `T_high` / `T_low`.
5. Export ONNX → `backend/models/embedding_model.onnx`.
6. Turn **off** placeholder embeddings when `DEBUG=false`.
7. After ≥50 PawFriend dogs with 3+ prints, fine-tune last layers only.

### 7.4 GPU

Inference: CPU is enough.  
Training: you **need** a free/paid GPU notebook. If you have zero GPU access, Track B cannot be trained in an internship; Track A still ships, and matching stays a documented prototype. Resolve this in week 1 of Phase C.

### 7.5 Known code fix before training time is wasted

YOLOv8 ONNX output is usually transposed predictions, not a list of `[x1,y1,x2,y2,conf,cls]` rows. When the detector is exported, rewrite `nose_detector.py` against a **real** ONNX dump (print `output.shape`) and add a unit test with a fixture image.

Quality assessment must use the cropped nose array, not the original full-frame JPEG, once a bbox exists.

---

## 8. User flows (corrected)

### Flow 1 — Register (owner or NGO staff)

1. Consent checkboxes.
2. Owner details.
3. Dog details (name, breed, color, sex, optional microchip).
4. Capture **3–5** nose photos (guided). Fail closed on quality.
5. Store profile + embeddings.
6. Success screen with **dog ID**, not a claim of “AI ID complete” until models are live.

**Fix:** one backend transaction (combined register endpoint) so a failed dog step does not leave an orphan owner.

### Flow 2 — Report lost

1. Owner or staff finds the dog in directory / “my dogs.”
2. Sets status `lost`, last-seen location/time, optional note.
3. Dog is boosted in identify ranking.
4. Appears on Lost Dogs page **without** owner phone.

### Flow 3 — Identify found dog (public)

1. No login.
2. Scan → pipeline.
3. UI shows: query crop, candidate dog photos, breed/color, lost badge, confidence band (“likely” / “possible” / none).
4. CTA: “Send to PawFriend staff for review” (creates/keeps match log).
5. If no match: **Found-dog intake** (finder nickname + phone *optional*, location, photos) with status `found`. This grows the database. Do not force the owner-registration form.

### Flow 4 — Staff confirm (the actual reunion)

1. Staff logs in.
2. Queue of match logs + found dogs.
3. Side-by-side photos.
4. Confirm / reject / needs another scan.
5. On confirm: reveal owner contact to **staff**, notify owner (email first).

---

## 9. Execution plan from today

Old roadmap assumed an empty repo and mixed “write training scripts” with “the model works.” Below is the **rebased** plan. Week numbers are sequential from **now**, not from the original Week 1.

```
NOW ──────────────────────────────────────────────────────────────────▶
 Phase 0     Phase 1        Phase 2           Phase 3      Phase 4
 Freeze      Capture        Real matching     Staff        Pilot
 Harden      quality        (the biometric)   reunion      deploy
 ~5 days     ~2 weeks       ~3 weeks          ~1.5 weeks   ~1 week
```

If the internship is shorter than ~8 weeks from today, **cut Phase 4 polish and WhatsApp**. Do not cut Phase 0 privacy or Phase 2 evaluation.

---

### Phase 0 — Freeze, honesty, safety (~5 days)

**Goal:** The repo tells the truth, and a stranger cannot dump owner phones.

Work:

1. Treat this file as the plan. Update `docs/task.md` to match (honest checkboxes).
2. Frontend hygiene: add `react`, `react-dom`, `@vitejs/plugin-react`; remove dead Vite TS starter files; make `npm run build` work.
3. Health check actually pings Postgres; `/health` reports `nose_detector` / `embedding` loaded flags truthfully.
4. **Auth:** `staff_users` + login + JWT on:
   - list/update/delete owners
   - confirm match
   - any response that includes phone/email/address
5. Strip `owner_name` (and any contact) from public `MatchCandidate`.
6. Identify + directory: public payloads are visual + non-contact metadata only.
7. Explicit consent checkbox; refuse register without it.
8. If `DEBUG=false` and embedding ONNX missing → identify/upload returns 503, not a random vector.
9. Combined register endpoint (owner + dog in one transaction).
10. `.env` secrets: no default JWT in production notes; document required vars.

**Deliverable:** A mentor can click around locally. Matching still fake in DEBUG, but APIs are not a data leak.

**Do not** download datasets until this phase is done. More ML on an unsafe API is the wrong order.

---

### Phase 1 — Capture reliability (~2 weeks)

**Goal:** Every stored photo is actually a usable nose image.

Work:

1. Download YOLO nose-bbox datasets (Kaggle / images.cv).
2. Fine-tune YOLOv8-nano; export ONNX to `backend/models/nose_detector.onnx`.
3. Fix YOLO post-processing to match real output tensor shape; test on 20 photos.
4. Quality gate on the **crop**: Laplacian sharpness, brightness, min coverage.
5. Camera UX:
   - keep guide overlay
   - client-side blur/brightness hint (can be a simple Laplacian on a downscaled frame)
   - auto-capture when a frame stays sharp for N ms (can be v1.1 if tap-capture is already good)
6. Reject “no nose detected” instead of embedding the whole dog.
7. Tune thresholds on 30 real phone photos (indoor/outdoor).

**Deliverable:** Registration photos look like noses. Staff can tell from the file names/crops. Identify still may not know *which* dog, but it no longer indexes random pixels.

---

### Phase 2 — Real matching (~3 weeks)

**Goal:** Embeddings mean identity, with a measured AUC and a chosen threshold.

Work:

1. Confirm GPU (Kaggle/Colab).
2. Obtain identity dataset (CVPR if alive, else Plan B collection).
3. Folder layout: `data/train/<dog_id>/*.jpg`, `data/val/<dog_id>/*.jpg`.
4. Train existing `ml/training/train_embedding.py`.
5. Run `evaluate.py`; save ROC + similarity histograms into `ml/eval_results/`.
6. Set `MATCH_THRESHOLD` / two-band thresholds from that file, not from guesswork.
7. Export ONNX; load in FastAPI; **disable placeholder**.
8. pgvector search already exists — verify with a held-out photo of a registered dog vs a different dog.
9. Identify UI: side-by-side **query crop vs candidate nose photo** (not just text scores).
10. Lost-status ranking boost (small additive bonus or separate sort key, documented).

**Target:** AUC ≥ 0.86 on the val set you actually have. If you only have a small self-collected set, report that AUC honestly (it may be lower) and still ship human review.

**Deliverable:** A recorded demo: register Dog A with 4 photos → scan a 5th photo → Dog A is top candidate → scan Dog B → no false high-confidence match.

---

### Phase 3 — Reunion operations (~1.5 weeks)

**Goal:** A found dog can become a phone call without leaking data to the internet.

Work:

1. Staff dashboard: match queue, confirm/reject, notes.
2. Report Lost flow (status + location + note).
3. Found-dog intake after no-match.
4. Email notification to owner on confirmed match (WhatsApp only if API access is already approved).
5. Deletion: owner delete also deletes S3/local photos.
6. Basic rate limit on `/match/identify` and uploads.
7. Error/loading/empty states cleaned up.
8. Alembic migration from the current schema (stop relying on `create_all` for anything shared).

**Deliverable:** Staff can complete a reunion drill end-to-end on staging.

---

### Phase 4 — Pilot on pawfriend.in (~1 week)

**Goal:** A small real URL, not a rewrite of the NGO site.

Work:

1. Host API + static PWA (subpath or subdomain), e.g. `pawfriend.in/noseprints` or `id.pawfriend.in`.
2. HTTPS, CORS locked to that origin, `DEBUG=false`.
3. R2/B2 for photos.
4. 10–20 real dogs registered by staff as a closed pilot.
5. One-page staff SOP: how to capture, how to confirm, what never to share.
6. Internship write-up: ROC, limitations, not 99% claims.

**Out of scope for this phase:** native app, Hindi UI, liveness, WhatsApp blasts, municipal partnerships.

---

### Stretch (after internship / if time left)

- WhatsApp Business templates for “possible match, please contact PawFriend”
- Native app / on-device inference
- Liveness
- HNSW index at scale
- Fine-tune on Indian street-dog phones
- Iris research note only
- Multi-language

---

## 10. Definition of Done (do not mark a phase done early)

### Phase 0 done when

- [ ] Public identify response contains **zero** owner contact fields
- [ ] `GET /api/v1/owners/` requires staff JWT
- [ ] Consent checkbox required
- [ ] Placeholder embeddings cannot run when `DEBUG=false`
- [ ] `npm run build` succeeds
- [ ] `/health` reflects real DB + model file presence

### Phase 1 done when

- [ ] `nose_detector.onnx` exists and loads
- [ ] 20/20 test photos crop a nose or correctly reject
- [ ] Failed quality returns guidance, not a stored embedding
- [ ] At least 3 prints stored per test dog are visually nose-closeups

### Phase 2 done when

- [ ] `embedding_model.onnx` exists and loads
- [ ] `ml/eval_results/metrics.txt` has AUC + chosen threshold
- [ ] Held-out same-dog scan ranks #1
- [ ] Held-out different-dog scan is below `T_high`
- [ ] Identify UI shows side-by-side images

### Phase 3 done when

- [ ] Staff can log in and confirm/reject
- [ ] Owner contact visible only after confirm
- [ ] Lost + found intake work
- [ ] Delete owner removes photos

### Phase 4 done when

- [ ] Staging/prod URL works on a phone over HTTPS
- [ ] Closed pilot of ≥10 dogs
- [x] Written SOP + honest accuracy appendix (`docs/STAFF_SOP.md`, `docs/ACCURACY.md`)

---

## 11. Risks (updated, ranked)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CVPR dataset unavailable | High | Can’t copy paper numbers | Plan B collection; still evaluate |
| No GPU | Medium | Can’t train ResNet50 well | Kaggle/Colab; intern asks mentor week 1 of Phase 2 |
| Field photos are garbage | High | Matching fails | Phase 1 quality gate is mandatory |
| False match → wrong owner contacted | Medium | Harm + legal | Two thresholds + staff-only contact |
| Open APIs leak PII | **Already true** | DPDP | Phase 0 |
| Similar-looking Indie dogs | High visually, lower on nose texture | Confusion | Nose crop only; never match on coat color alone |
| Dog won’t stay still | High | Blur | Auto-capture / burst; reject blur |
| Internship time runs out | High | Half-product | Prefer Phase 0+1+2 over WhatsApp/native |
| pawfriend.in is WordPress/shared hosting | Medium | Hard PWA integration | Subdomain + separate API is enough |
| YOLO parser wrong | High | Silent bad crops | Fixture tests when ONNX exists |
| Demo with placeholder called “AI working” | High | Trust damage | Language rules in Section 12 |

---

## 12. Communication rules (for demos and the NGO)

**Allowed now:**  
“We built registration, a camera capture flow, and the matching *pipeline*. Identification becomes real after the models are trained and measured.”

**Forbidden until Phase 2 DoD:**  
“Scan a nose and the app knows whose dog it is.”

**Always:**  
“Staff confirm before anyone gets a phone number.”  
“This complements microchips; it does not replace them.”  
“Published 99% numbers are lab conditions, not our street-dog guarantee.”

---

## 13. Integration with pawfriend.in

Do not block biometric work on a full rewrite of the existing site.

**Recommended:**  
- PWA hosted on a **subdomain or subpath**  
- FastAPI as a separate service  
- Header/footer can later match PawFriend branding  
- Shared login with the main site is **not** required for v1; staff accounts inside this app are enough  

Ask the NGO once (not as a build blocker):

1. Current site stack (WordPress vs custom)
2. Can they create `id.pawfriend.in` or a `/noseprints` path?
3. Budget for ~$5–10/month hosting + object storage
4. Who are the 2–3 staff that will confirm matches?
5. Approximate existing dog records (even a spreadsheet) for migration later

Until those answers exist, develop locally with Docker as now.

---

## 14. Success criteria for the internship

The internship is successful if **all** of these are true:

1. PawFriend can register dogs and store 3–5 quality nose photos.
2. A trained detector crops noses (or cleanly rejects).
3. A trained embedder is evaluated with an ROC curve you can show.
4. Identify returns candidates **without** leaking owner PII.
5. A staff user can confirm a match in a dashboard.
6. Limitations are written down honestly.

It is **not** a failure if AUC is 0.80 on a small Indian phone dataset instead of 0.99. It **is** a failure if the app is shown as identifying dogs while still using placeholder vectors.

---

## 15. Immediate next actions (this week)

Phase 0 is done. Do these next:

1. Confirm GPU access (Kaggle account + notebook GPU) for Phase 2 later.
2. Download **detector** datasets (Kaggle / images.cv) and start Phase 1.
3. Collect 10 real nose photos on a phone as a visual test set.
4. Do not train the embedder until Phase 1 detector crops are visibly correct.

---

## 16. Document map

| File | Role after this plan |
|---|---|
| `docs/MASTER_PLAN.md` | **Follow this** |
| `docs/task.md` | Checklist only; keep in sync with Section 9 |
| `docs/implementation_plan.md` | Historical detailed draft |
| `docs/pawfriend-noseprint-plan.md` | Historical feasibility draft |
| `docs/AIML Plan.txt` | Historical ML explainer |
| `README.md` | How to run locally; link here for “what we are building” |

---

## 17. Final answer

| Question | Answer |
|---|---|
| Is dog nose-print ID real? | Yes. |
| Is retina scanning in scope? | No for v1. |
| Is the current repo on the right architecture? | Yes. |
| Is matching working today? | No. Placeholder embeddings only. |
| Is the old 8-week plan still the schedule? | No. Rebase from today using Phases 0–4. |
| What is the single most important next step? | Close PII leaks and stop treating placeholder matching as the product. |
| What makes the biometric actually work? | Real nose crops + trained ArcFace ONNX + ROC threshold + human confirm. |
| Can this be integrated into pawfriend.in as a light PWA? | Yes. That remains the right delivery form. |

**This is doable.** The science is proven, the stack in this repo is the right one, and enough code exists that the remaining work is execution quality — not a new idea. The way to make it solid is to stop adding pages, freeze the safety rules, make capture real, then make embeddings real, then make reunion operational.

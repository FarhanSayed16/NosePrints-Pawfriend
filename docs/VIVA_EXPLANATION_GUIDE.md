# NosePrints × PawFriend — Complete Viva Explanation Guide

**Use this in your viva.** Speak in simple clear language. Numbers below are from *this* project — do **not** invent better accuracy.

**Related:** [`ACCURACY.md`](./ACCURACY.md) · [`FINAL_DEPLOYMENT_PLAN.md`](./FINAL_DEPLOYMENT_PLAN.md) · [`COST_AND_UNIT_ECONOMICS.md`](./COST_AND_UNIT_ECONOMICS.md)

---

## 0. 60-second opening (memorize this)

> Sir/Ma’am, my project is **NosePrints**, built for **PawFriend.in**.  
> Dogs have unique nose patterns, similar to human fingerprints. We use a phone camera to **register** a dog’s nose, and later **identify** a found or lost dog by comparing the new nose photo against a database.  
> The system has three layers: a **React PWA** frontend, a **FastAPI** backend, and two **ONNX ML models** — a YOLO nose detector and a ResNet50 embedding model trained with ArcFace.  
> Matching uses **cosine similarity** in **PostgreSQL + pgvector**. Owner phone numbers are **locked** until a **PawFriend staff member confirms** the match.  
> Junk photos (keyboards, walls) are rejected by quality gates so false matches don’t pollute the gallery.

---

## 1. Problem statement

| Without NosePrints | With NosePrints |
|--------------------|-----------------|
| Lost/found dogs identified by breed/color only (unreliable) | Biometric nose texture + human staff confirm |
| Owner contact exposed publicly → privacy risk | Contact hidden until staff confirms |
| No structured registry | Searchable dog registry with embeddings |

**Scope of v1:** Nose-print identity only (not iris/retina). Phone browser PWA — no native Android/iOS app required.

---

## 2. How the system is built (architecture)

```
┌─────────────────────┐
│  Phone / Laptop     │  React PWA (Vite)
│  Register / Identify│  Camera → crop → upload
│  Staff console      │
└──────────┬──────────┘
           │ HTTPS /api/v1
           ▼
┌─────────────────────┐
│  FastAPI backend    │  Auth, register, match, dogs
│  + ONNX Runtime     │  YOLO detector + embedding
└──────────┬──────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐  ┌────────────┐
│ Supabase │  │ Photos     │
│ Postgres │  │ local/R2   │
│ pgvector │  │ (URLs in DB)│
└──────────┘  └────────────┘
```

| Layer | Technology | Role |
|-------|------------|------|
| Frontend | React + Vite PWA | UI, camera capture, staff ops |
| Backend | FastAPI (Python) | APIs, gates, matching, auth |
| ML | ONNX Runtime (CPU) | Nose detect + 512-d embedding |
| Database | PostgreSQL + pgvector | Owners, dogs, vectors, match logs |
| Storage | Local disk or S3/R2 | Nose/look photos as files; DB keeps URLs |
| Deploy (plan) | Google Cloud Run one container | UI + API + both models together |

**Important viva point:** Frontend, backend, and ML models are designed to deploy as **one Cloud Run service**. The database is separate (Supabase). Photos should be in object storage so they survive redeploys.

### Main code map (if they ask “where is the code?”)

| Part | Path |
|------|------|
| App entry | `backend/app/main.py` |
| Matching | `backend/app/services/matcher.py` |
| Detector | `backend/app/services/nose_detector.py` |
| Embedding | `backend/app/services/embedding.py` |
| Junk gates | `backend/app/services/capture_pipeline.py`, `nose_heuristics.py` |
| Staff UI | `frontend/src/pages/Staff.jsx` |
| Config / thresholds | `backend/app/config.py` |

---

## 3. End-to-end working flows

### Flow A — Register a dog

1. Owner enters name, phone, consent (DPDP).
2. Dog profile: name, breed, color, optional look photo.
3. User captures **3–5 nose photos** (different angles help).
4. For each photo the backend:
   - Detects the nose (YOLO)
   - Runs quality / junk gates
   - Creates a **512-dimensional embedding**
   - Stores embedding in `nose_prints` + photo URL
5. Dog is now searchable in the gallery.

### Flow B — Identify a found / unknown dog

1. Finder uploads a nose photo (optional full-body look photo).
2. Same detect → gate → embed pipeline.
3. System searches all stored nose embeddings with **cosine similarity**.
4. Returns:
   - **Likely match** / **Possible match** / **No match**
5. If match band is strong enough, a row goes to the **staff match queue**.
6. **Owner phone is still hidden** from the public finder.

### Flow C — Staff confirmation (the “lock”)

1. Staff logs in with JWT (`/staff`).
2. Opens Match Queue — sees side-by-side nose crops + scores.
3. **Confirm** → system reveals owner contact (and can email if SMTP set).
4. **Reject** → marked false positive; no owner reveal.
5. This is intentional: **AI suggests, human unlocks identity**.

### Flow D — No match

Offer **found-dog intake** so the stray can still be listed without claiming a wrong owner.

---

## 4. How the ML models work

We use **two separate models**, not one.

### Model 1 — Nose detector (YOLOv8n → ONNX)

**Job:** Find *where* the nose is in the photo (bounding box).

| Item | Detail |
|------|--------|
| Architecture | YOLOv8 **nano** (small, fast on CPU) |
| Input | Image letterboxed to **640×640** |
| Output | Bounding box + confidence |
| Runtime | ONNX Runtime, CPU |
| File | `backend/models/nose_detector.onnx` |

**Why needed:** Embedding must see the nose leather, not the whole dog or background. Bad crops → bad identity.

**Training result (honest):** On our merged detector data, validation **mAP50 ≈ 0.54** (promoted model). Close-up recall improved with padding + retry at a lower confidence.

### Model 2 — Embedding / identity (ResNet50 + ArcFace → ONNX)

**Job:** Turn a nose crop into a **fingerprint vector**.

| Item | Detail |
|------|--------|
| Backbone | **ResNet50** |
| Training loss | **ArcFace** (metric learning for identity) |
| Output | **512-d** vector, **L2-normalized** |
| Inference size | Resize crop to **224×224**, ImageNet normalize |
| File | `backend/models/embedding_model.onnx` |
| Training data | CVPR 2022 Pet Biometric Challenge mirror (~**6,000 dogs**) |

**Lab metrics (quote these, not 98%):**

| Metric | Value |
|--------|-------|
| Rank-1 identification | **78.6%** |
| AUC | **0.803** |
| CVPR winner bar | **86.67% AUC** — we are **below** that |

A later continue-train experiment got AUC **0.800** (slightly worse) → **not promoted**. Production still uses the better baseline.

**Viva sentence:**

> The detector localizes the nose; the embedding model maps that crop into a 512-dimensional unit vector so similar noses are close in cosine space.

---

## 5. How the matching / “locking” algorithm works

### 5.1 Similarity

- Vectors are L2-normalized.
- We use **cosine similarity** via pgvector:
  - Distance operator `<=>`
  - Score = `1 − cosine_distance`
- Score near **1.0** = very similar; near **0** = dissimilar.

### 5.2 Max-over-prints (how we avoid weak single-photo matching)

Each dog can have up to **5** nose embeddings.

**Production rule:** Compare the query against **every** print in the gallery, then for each dog keep the **maximum** similarity (best print).  
That is **max-over-prints**, not averaging all prints into one template at search time.

**Why:** One bad registration photo should not drag down a dog that also has good prints.

### 5.3 Threshold bands (decision logic)

| Score (cosine) | Result | Meaning |
|----------------|--------|---------|
| ≥ **0.56** | **Likely / matched** | Strong candidate → staff queue |
| **0.51 – 0.56** | **Possible** | Weaker; extra caution |
| < **0.51** | **No match** | Empty candidates to the user; offer found intake |

These came from lab ROC calibration (~5% FAR at 0.56, ~20% FAR at 0.51 on the evaluation set) — **not** “56% accuracy.”

**Strict demo mode** (for careful public demos):

- `MATCH_STRICT_DEMO=true`
- Only scores ≥ **0.60** count as a match
- “Possible” band off → fewer false hopes

### 5.4 Lost-dog ranking boost

Lost dogs get **+0.03** added **only for sorting** among candidates.  
The **score shown** to users stays the raw cosine. This gently prioritizes reunions without faking confidence.

### 5.5 Top-K

We fetch a wider neighbor list from pgvector, dedupe by dog, then return up to **top 5** dogs.

### 5.6 Appearance / look photo

Full-body similarity is a **soft hint for staff only**. It **never** alone decides `match_found`. Biometric decision is nose cosine.

### 5.7 What “locking algorithm” means in this project

Professors may say “locking” for privacy / access control. In NosePrints:

1. **Data lock:** Owner PII is not in public identify responses.
2. **Auth lock:** Staff JWT required for queue / confirm / owner APIs.
3. **Role lock:**
   - `viewer` — can view, cannot confirm
   - `staff` — can confirm/reject
   - `admin` — invite staff, delete dogs, DPDP erase
4. **Confirm lock:** Only after staff **Confirm** is owner phone/email returned.

So “locking” = **biometric suggestion + cryptographic staff auth + role checks + human unlock of PII**.

---

## 6. How redundancy and false matches are avoided

“Redundancy” / pollution in this project means: **junk or duplicate-quality garbage** entering the gallery, or **weak matches** shown as confident IDs.

### 6.1 Multi-gate pipeline (G0–G3)

Every nose path (register, identify, found-intake embed) goes through **`prepare_nose_scan`**:

| Gate | What it stops |
|------|----------------|
| **G0 — Detector honesty** | Accept only a real nose box above min confidence; reject “full frame is the nose” cheats |
| **G1 — Crop heuristics** | Keyboard/fabric/walls: aspect ratio, edge density, grid regularity, colorfulness, hue spread, dark leather center, blur |
| **Quality** | Sharpness, brightness range, nose coverage in frame |
| **G1.1 — Re-detect on crop** | YOLO again on the crop so we didn’t just crop random texture |
| **G2 — Match honesty** | Below threshold → **no candidates** shown (don’t display a random “best wrong dog”) |
| **G3 — Look photo soft gate** | Full-body junk soft-warns; user can override; **not** used as biometric ID |

**Viva example:**

> If someone uploads a keyboard, edge density and grid regularity are high, colorfulness is high, and the detector/heuristics reject it **before** we store an embedding. That prevents two junk images from matching each other with a meaningless high cosine score.

### 6.2 Why junk can falsely “match” without gates

Embedding models measure **texture similarity**. Two keyboards can look more similar to each other than to real noses. Gates keep garbage **out of the gallery** and out of the search path.

### 6.3 Multi-print without redundant identity rows

- Multiple prints = **same dog**, different captures (good redundancy for recall).
- Matching collapses to **one dog ID** via max score (avoids returning the same dog five times).
- Cap: max **5** prints per dog.

### 6.4 Staff + registry cleanup

- False AI matches → staff **Reject**.
- Polluted test dogs → admin **Registry delete**.
- Demo gallery was purged to clean dogs for honest demos.

### 6.5 Rate limits & audit

Public identify/upload endpoints are rate-limited. Staff actions (confirm, delete, invite) write **audit logs** — accountability, not ML.

---

## 7. Database design (explain briefly)

| Table | Purpose |
|-------|---------|
| `owners` | Contact + consent timestamp (DPDP) |
| `dogs` | Profile, lost/found status, optional region |
| `nose_prints` | **512-d vector** + photo URL + quality |
| `match_logs` | Every identify attempt for audit / staff queue |
| `staff_users` | Staff accounts + roles |
| `staff_invites` / `password_reset_tokens` | Multi-admin ops |
| `audit_logs` | Who confirmed/deleted/invited |

**Key design choice:** Store **vectors + URLs** in Postgres; store **image bytes** in files/object storage — keeps DB small and searchable with pgvector.

---

## 8. Frontend features (what the user sees)

| Page | Purpose |
|------|---------|
| Register | Consent, dog info, multi nose capture |
| Identify | Scan nose → match result |
| Directory / Lost / Found | Browse / report / intake |
| Staff | Login, match queue, registry, admin invite, erasure |

Staff console is redesigned as an ops tool: refresh queue, show reviewed, role-aware buttons, DPDP erase for admins.

---

## 9. Privacy & DPDP (India)

- Explicit **consent** at registration (`consent_given_at`, version string).
- Owner contact **not public**.
- Admin can **erase** owner + dogs + photos on request.
- Staff confirmation is part of the privacy design, not only accuracy.

---

## 10. Accuracy — what to say / what never to say

### Say

- Lab embedding: **AUC 0.803**, **rank-1 78.6%** on ~6k-dog public challenge data.
- Detector: **mAP50 ~0.54** on our val set (promoted).
- Thresholds calibrated for approximate FAR bands on that lab set.
- **Staff must confirm** before reunion contact.
- For real India field performance we need a **consented pilot** of many real dogs, then fine-tune.

### Never say

- “**98–99% accuracy**” (those are paper figures on curated setups, **not** our production claim).
- “It identifies all dogs automatically with no human.”
- “We beat the CVPR winner” (we did **not**; winner AUC ~86.7%).

---

## 11. Deployment & cost (if asked)

| Topic | Answer |
|-------|--------|
| Where it runs today | Local PC + optional Cloudflare tunnel for phone HTTPS |
| Production plan | **Cloud Run** (2 GiB) + **Supabase** + **R2** photos |
| One deploy includes | Frontend + backend + both ONNX models |
| Cost | Near **$0/month** at demo scale with scale-to-zero + free tiers; GCP billing card required; avoid always-on min instances |

---

## 12. Likely viva Q&A

**Q: Why nose prints?**  
A: Nose leather has unique ridge patterns; cameras are available on every phone; no special hardware.

**Q: Why two models?**  
A: Detection finds the region; embedding encodes identity. Mixing both in one model is harder and less modular.

**Q: Why ONNX?**  
A: Train in PyTorch, export once, run fast on CPU in production without needing a GPU server.

**Q: Why pgvector?**  
A: Store embeddings next to dog metadata; cosine search in SQL; one database for product + ML vectors.

**Q: What if two dogs look similar?**  
A: Cosine may be close; thresholds + staff review + multi-print + look hint reduce risk. We do not auto-release phone numbers.

**Q: How do you avoid fake matches from junk?**  
A: G0–G3 gates reject non-nose inputs before embedding/search; G2 hides sub-threshold candidates.

**Q: Is ArcFace the matcher?**  
A: ArcFace is the **training loss** that shapes the embedding space. At runtime we only do **cosine** between L2-normalized vectors.

**Q: Max vs mean prints?**  
A: Production uses **max similarity across a dog’s prints**. Offline lab metrics historically used mean centroids — we documented that difference.

**Q: What did you implement beyond ML?**  
A: Full product: PWA, registration, identify, staff JWT + roles, invite/reset, audit logs, DPDP erase, junk gates, Cloud Run deploy plan.

**Q: Limitations?**  
A: Lab metrics ≠ India street conditions; need more real consented dogs; lighting/angle matter; human-in-the-loop is required; Cloud Run prod deploy still needs GCP credentials.

---

## 13. Suggested viva speaking order (8–12 minutes)

1. Problem + one-line solution (1 min)  
2. Architecture diagram in words (2 min)  
3. Register → Identify → Staff confirm demo story (2 min)  
4. Two models + cosine matching + thresholds (3 min)  
5. Gates / how junk & redundancy avoided (2 min)  
6. Privacy lock + honest accuracy + future Cloud Run (1–2 min)  
7. Stop and invite questions  

---

## 14. One closing line

> NosePrints is not “magic AI that always knows the dog.” It is an engineered pipeline — detect, gate, embed, search, and **staff-unlock** — built so PawFriend can reunite pets **safely** with measurable models and clear failure modes.

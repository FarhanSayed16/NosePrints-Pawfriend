# NosePrints — Phase A Final Deployment Plan

**Status:** Final plan for standalone demo  
**Audience:** Intern / builder, mentor, PawFriend technical lead  
**Related:** Step-by-step CLI detail remains in [`DEPLOY.md`](./DEPLOY.md). Product roadmap: [`MASTER_PLAN.md`](./MASTER_PLAN.md).

---

## 1. Decision (locked)

| Item | Choice |
|------|--------|
| Phase | **A — Standalone demo only** |
| Hosting | **Google Cloud Run** (`us-central1`) |
| Database | **Supabase** (Postgres + `pgvector`) |
| Delivery | One HTTPS URL (`*.run.app`) serving UI + API + ONNX |
| PawFriend site | **Not in this phase** — attach later via subdomain |
| Merge into existing pawfriend.in app | **No** — keep as a separate service |

**One-line summary for seniors:**  
Deploy NosePrints as a single Cloud Run service (2 GiB) built from a machine that has the ONNX models, backed by Supabase + pgvector, for a public standalone demo. Attach `id.pawfriend.in` later without rewriting the product.

---

## 2. What we are deploying

```
Phone / laptop (HTTPS)
        │
        ▼
┌─────────────────────────────────────┐
│  Google Cloud Run — service         │
│  "noseprints"                       │
│  • React PWA (static)               │
│  • FastAPI                          │
│  • nose_detector.onnx               │
│  • embedding_model.onnx             │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Supabase Postgres + vector         │
│  owners, dogs, nose_prints,         │
│  match_logs, staff_users            │
└─────────────────────────────────────┘
```

| Component | Provider | Notes |
|-----------|----------|--------|
| App (frontend + API + models) | Cloud Run | Memory **2 GiB**, CPU 1, scale-to-zero OK |
| Database | Supabase | Port **5432** only (not 6543) |
| Model files | Bundled at build from this PC | **Not** on GitHub — deploy with `gcloud run deploy --source .` from local disk |
| Photos (Phase A) | Local `/uploads` by default; set `S3_*` + `S3_PUBLIC_BASE_URL` for durable R2/B2 | Without S3, photos vanish on Cloud Run redeploy |
| Custom domain | Out of scope | Phase B |

---

## 3. What Phase A does *not* include

- Custom domain / `id.pawfriend.in` / links from pawfriend.in  
- Durable object storage (GCS / R2) — **optional but recommended**; see Step 7 “Durable photos”  
- SMTP / WhatsApp owner notifications  
- Always-on paid instances  
- Merging into existing PawFriend GCP website process  
- Hugging Face (paid) or free 512 MB hosts (will OOM)

---

## 4. Prerequisites checklist

Before starting:

- [ ] Repo on disk: `D:\NosePrints-Pawfriend`
- [ ] Both models present:
  - `backend/models/nose_detector.onnx` (~12 MB)
  - `backend/models/embedding_model.onnx` (~100 MB)
- [ ] Google account + billing (free allowance; set **$1 budget alert**)
- [ ] Supabase account (or existing project that is **not** paused/deleted)
- [ ] Google Cloud CLI installed (`gcloud`)
- [ ] Secrets notepad (never commit):

```text
JWT_SECRET =
STAFF_EMAIL =
STAFF_PASSWORD =
SUPABASE_DB_URI =
GOOGLE_PROJECT_ID =
APP_URL =
```

---

## 5. End-to-end execution plan

### Step 0 — Verify models on this PC

```powershell
dir D:\NosePrints-Pawfriend\backend\models\*.onnx
```

If either file is missing → **stop**. Identify will not work in production.

---

### Step 1 — Secrets and staff login

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

- Save output as `JWT_SECRET`
- Choose `STAFF_EMAIL` (real inbox) and `STAFF_PASSWORD` (≥ 8 characters)
- Staff UI path after deploy: `https://APP_URL/staff`

---

### Step 2 — Supabase database

1. Create project (or restore a **paused** one — a deleted tenant causes `ENOTFOUND tenant/user postgres.xxx not found`).
2. Enable extension **`vector`** (Database → Extensions, or SQL: `create extension if not exists vector;`).
3. Copy connection URI on port **5432**:
   - Direct: `db.xxxxx.supabase.co`, user `postgres`
   - **or** Session pooler: `…pooler.supabase.com:5432`, user `postgres.PROJECTREF`
4. **Do not** use transaction pooler port **6543**.
5. URL-encode special characters in the password (`@` → `%40`, `#` → `%23`, etc.).
6. Skip Supabase Auth / Storage / Edge Functions — FastAPI owns the data path.

**Local `.env` (dev):** set `DATABASE_URL` to this URI, then restart uvicorn until `/health` shows `"database": "connected"`.

---

### Step 3 — Google Cloud project

1. Console → New project → name `noseprints` → save **Project ID**.
2. Link billing; create budget alert **$1 USD**.
3. Enable APIs:
   - Cloud Run API  
   - Cloud Build API  
   - Artifact Registry API  

---

### Step 4 — gcloud CLI

```powershell
gcloud init
gcloud config get-value project
```

Region for free-tier friendly Cloud Run: **`us-central1`**.

---

### Step 5 — Reconfirm models (required)

Cloud Run builds from the local folder. GitHub alone is not enough.

```powershell
dir D:\NosePrints-Pawfriend\backend\models\*.onnx
```

Do **not** set `DATABASE_SSL_VERIFY=false` on Cloud Run (Windows-local TLS workaround only).

---

### Step 6 — Deploy from this PC

First build often takes **15–25 minutes**. Leave PC on and terminal open.

```powershell
cd D:\NosePrints-Pawfriend

gcloud run deploy noseprints `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 1 `
  --timeout 300 `
  --cpu-boost `
  --set-env-vars "DEBUG=false,SERVE_FRONTEND=true,FRONTEND_DIR=/app/frontend_dist,STAFF_BOOTSTRAP_EMAIL=YOUR_STAFF_EMAIL,JWT_SECRET_KEY=YOUR_JWT_SECRET,STAFF_BOOTSTRAP_PASSWORD=YOUR_STAFF_PASSWORD,DATABASE_URL=YOUR_SUPABASE_DB_URI"
```

Save printed Service URL as `APP_URL` (no trailing slash), e.g.:

```text
https://noseprints-xxxxxxxxxx-uc.a.run.app
```

If PowerShell mangles the DB URI, deploy without `--set-env-vars` and set variables in the Console (Step 7).

---

### Step 7 — Environment variables (Cloud Run Console)

**Cloud Run → noseprints → Edit & deploy new revision → Variables**

| Name | Value |
|------|--------|
| `DATABASE_URL` | Supabase URI (5432) |
| `JWT_SECRET_KEY` | JWT from Step 1 |
| `STAFF_BOOTSTRAP_EMAIL` | Staff email |
| `STAFF_BOOTSTRAP_PASSWORD` | Staff password (≥ 8 chars) |
| `DEBUG` | `false` |
| `SERVE_FRONTEND` | `true` |
| `FRONTEND_DIR` | `/app/frontend_dist` |
| `CORS_ORIGINS` | `APP_URL` (no trailing slash) |

Confirm **Memory = 2 GiB**.

Do **not** set `SMTP_*` for Phase A.

### Durable photos (recommended before sharing with staff)

Local `/uploads` on Cloud Run **vanishes** when a new revision deploys. For durable photos, create a Cloudflare R2 (or B2) bucket that is **publicly readable**, then set:

| Name | Example |
|------|--------|
| `S3_ENDPOINT_URL` | `https://<accountid>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY` | R2 API token access key |
| `S3_SECRET_KEY` | R2 API token secret |
| `S3_BUCKET_NAME` | `noseprints-photos` |
| `S3_REGION` | `auto` |
| `S3_PUBLIC_BASE_URL` | `https://pub-xxxxx.r2.dev` (no trailing slash) |

Also allow CORS `GET` on the bucket for your `APP_URL`. After redeploy, `/health` should show `"storage": "s3"`.

If you skip this, the demo still works until the next Cloud Run revision.

---

### Step 8 — Health gate (mandatory before UI demos)

Open: `https://APP_URL/health`

Required:

```json
{
  "status": "healthy",
  "database": "connected",
  "ml_models": {
    "nose_detector_loaded": true,
    "embedding_extractor_loaded": true,
    "embedding_mode": "real"
  }
}
```

| Symptom | Fix |
|---------|-----|
| `database: disconnected` / `ENOTFOUND tenant/user` | Project paused/deleted or wrong URI — restore project or create new + update `DATABASE_URL` |
| `embedding_mode` ≠ `real` | Models missing from image — confirm `.onnx` locally, redeploy `--source .` |
| OOM / container killed | Memory must be **2 GiB** |
| Cold start 30–90s | Normal after scale-to-zero — refresh once |
| Blank white page | `SERVE_FRONTEND=true`; Cloud Build must have run `npm run build` |

---

### Step 9 — Acceptance test (PC, then phone)

**PC**

1. Open `APP_URL` — home page (not raw JSON).  
2. **Register** — owner + dog + nose photos.  
3. **Identify** — same dog → candidate + side-by-side.  
4. **`/staff`** — login → confirm match.  
5. Owner phone must appear **only** after staff confirm, never on public Identify.

**Phone**

1. Open `APP_URL` over HTTPS (any network).  
2. Camera + identify.  
3. Optional: Add to Home Screen (PWA).

---

### Step 10 — Definition of Done (Phase A)

- [ ] `/health` → `database: connected` and `embedding_mode: real`
- [ ] Home loads on HTTPS
- [ ] Register + Identify work
- [ ] Staff login + confirm works
- [ ] Owner contact hidden on public Identify
- [ ] Phone camera works on `*.run.app`

Until this list is complete, **do not** share the URL with PawFriend as “live”.

Do **not** put real owner PII on a public URL until staff privacy has been verified.

---

## 6. Local run (before / alongside Cloud Run)

Use this to verify DB + models while preparing GCP.

**Terminal 1 — API**

```powershell
cd D:\NosePrints-Pawfriend\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check: `http://127.0.0.1:8000/health`

**Terminal 2 — website (for Cloudflare tunnel demos)**

```powershell
cd D:\NosePrints-Pawfriend\frontend
npm run tunnel
```

- Local: `http://127.0.0.1:5173`  
- If port in use: `netstat -ano | findstr :5173` then `taskkill /PID <pid> /F`  
- Do **not** use `npm run dev` behind Cloudflare (blank page risk)

---

## 7. Architecture rules for this phase

| Rule | Why |
|------|-----|
| Deploy from PC with models | `.onnx` files are not in git |
| Memory ≥ 2 GiB | Models ~112 MB + runtime; 512 MB hosts die |
| Supabase port 5432 | Transaction pooler (6543) breaks this stack |
| `DEBUG=false` in Cloud Run | Blocks placeholder embeddings in prod |
| Staff confirm before contact | Privacy + accuracy are below lab 99% claims |
| Separate from pawfriend.in process | WordPress/shared hosting cannot run ONNX |

Honest accuracy for demos: held-out rank-1 ~**78.6%**, AUC ~**0.80** — not 98–99%. See [`ACCURACY.md`](./ACCURACY.md).

---

## 8. After Phase A (out of scope here)

**Phase B — Attach PawFriend (no rebuild)**

1. Point `id.pawfriend.in` (or similar) at the **same** Cloud Run service.  
2. Set `CORS_ORIGINS` to that HTTPS origin.  
3. Keep same Supabase DB and `DEBUG=false`.  
4. Add links from pawfriend.in → subdomain.  
5. Add durable photo storage (GCS/R2) before a real pilot.

---

## 9. File map

| Path | Role |
|------|------|
| `Dockerfile` | Builds frontend, installs Python, starts API |
| `backend/start.sh` | uvicorn on `$PORT` (Cloud Run) |
| `backend/models/*.onnx` | Required for real matching |
| `.gcloudignore` | Includes models; skips venv / node_modules / `.env` |
| `docs/DEPLOY.md` | Verbose click-by-click companion |
| `docs/PHASE_A_DEPLOYMENT.md` | **This file — final Phase A plan** |

---

## 10. Sign-off summary

| Question | Answer |
|----------|--------|
| What are we shipping? | Standalone NosePrints demo on Cloud Run + Supabase |
| Reuse existing PawFriend GCP site? | Reuse **billing/DNS org later**; do **not** merge into the marketing site for v1 |
| When is Phase A done? | Health green + register/identify/staff/phone checks pass |
| What next? | Subdomain + durable photos + closed 10–20 dog pilot |

  # Final deploy guide — NosePrints (everything in one go)

  **Goal:** One public HTTPS URL that serves **frontend + backend + ML models** together on Google Cloud Run, connected to Supabase + durable photos.

  **Time:** ~45–90 minutes the first time.  
  **Cost:** Usually **~$0/month** on free tiers if you follow this guide (GCP billing card still required). See [`COST_AND_UNIT_ECONOMICS.md`](./COST_AND_UNIT_ECONOMICS.md).

  **Architecture reminder:** One Cloud Run container = PWA + FastAPI + both ONNX files. Database and photos are external (env vars). You do **not** deploy frontend/backend/ML separately.

  ---

  ## Before you start (checklist)

  - [ ] Repo on this PC: `D:\NosePrints-Pawfriend`
  - [ ] Models present:
    - `backend\models\nose_detector.onnx`
    - `backend\models\embedding_model.onnx`
  - [ ] Supabase project **not paused**; connection uses port **5432** (not 6543)
  - [ ] Google account + **billing** enabled + **$1 budget alert**
  - [ ] [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed
  - [ ] **Docker Desktop** installed and **running**
  - [ ] Cloudflare R2 (or B2/GCS) bucket ready for photos (recommended)

  Verify models:

  ```powershell
  dir D:\NosePrints-Pawfriend\backend\models\*.onnx
  ```

  ---

  ## Step 1 — Google Cloud project

  ```powershell
  gcloud auth login
  gcloud projects create YOUR_PROJECT_ID --name="NosePrints"
  gcloud config set project YOUR_PROJECT_ID
  ```

  Or use an existing project. Note the project ID.

  In [Cloud Console → Billing](https://console.cloud.google.com/billing): link billing, create a budget alert at **$1**.

  Enable APIs (the deploy script also does this):

  ```powershell
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
  ```

  ---

  ## Step 2 — Secrets notepad (do not commit)

  Generate a JWT secret:

  ```powershell
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

  Fill privately:

  ```text
  GOOGLE_PROJECT_ID =
  DATABASE_URL = postgresql+asyncpg://USER:PASS@HOST:5432/postgres
  JWT_SECRET_KEY = (from command above)
  S3_ENDPOINT_URL =
  S3_ACCESS_KEY =
  S3_SECRET_KEY =
  S3_BUCKET_NAME = noseprints-photos
  S3_PUBLIC_BASE_URL = https://your-public-r2-or-cdn-host
  STAFF_BOOTSTRAP_EMAIL = staff@pawfriend.in
  STAFF_BOOTSTRAP_PASSWORD = (strong password, only if staff table empty)
  ```

  **Supabase tip:** use the **direct** or session pooler URI on port **5432**. URL-encode special characters in the password (e.g. `@` → `%40`).

  ---

  ## Step 3 — Durable photos (R2 recommended)

  1. Create an R2 bucket (e.g. `noseprints-photos`).
  2. Create an API token with Object Read/Write.
  3. Enable a **public** bucket URL or custom domain → that becomes `S3_PUBLIC_BASE_URL`.
  4. Endpoint looks like: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

  Without S3/R2, photos sit on the container disk and **vanish on redeploy**. Do not skip this for a real deploy.

  ---

  ## Step 4 — Create Cloud Run env file

  ```powershell
  cd D:\NosePrints-Pawfriend
  copy .env.cloudrun.yaml.example .env.cloudrun.yaml
  notepad .env.cloudrun.yaml
  ```

  Fill every required value. Example shape:

  ```yaml
  DATABASE_URL: "postgresql+asyncpg://USER:PASS@HOST:5432/postgres"
  JWT_SECRET_KEY: "your-long-unique-secret"
  DEBUG: "false"
  SERVE_FRONTEND: "true"
  FRONTEND_DIR: "/app/frontend_dist"
  PUBLIC_APP_URL: "https://placeholder.run.app"
  MATCH_STRICT_DEMO: "true"
  S3_ENDPOINT_URL: "https://ACCOUNT.r2.cloudflarestorage.com"
  S3_ACCESS_KEY: "..."
  S3_SECRET_KEY: "..."
  S3_BUCKET_NAME: "noseprints-photos"
  S3_REGION: "auto"
  S3_PUBLIC_BASE_URL: "https://photos.yourdomain.com"
  STAFF_BOOTSTRAP_EMAIL: "staff@pawfriend.in"
  STAFF_BOOTSTRAP_PASSWORD: "only-if-empty-staff-table"
  ```

  Add `.env.cloudrun.yaml` to gitignore if not already (never commit secrets).

  You will update `PUBLIC_APP_URL` after the first deploy when you know the real `*.run.app` URL.

  ---

  ## Step 5 — Deploy (frontend + backend + models together)

  **Docker Desktop must be running.**

  ```powershell
  cd D:\NosePrints-Pawfriend
  .\scripts\cloud_run_deploy.ps1 -ProjectId YOUR_PROJECT_ID
  ```

  This builds from the `Dockerfile` on this PC (so ONNX files are included) and deploys service **`noseprints`** in **`us-central1`** with **2 GiB** RAM.

  Manual equivalent:

  ```powershell
  gcloud run deploy noseprints `
    --source . `
    --region us-central1 `
    --project YOUR_PROJECT_ID `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 1 `
    --timeout 300 `
    --env-vars-file .env.cloudrun.yaml
  ```

  Wait for the service URL, e.g. `https://noseprints-xxxxx-uc.a.run.app`.

  ---

  ## Step 6 — Point PUBLIC_APP_URL at the real URL

  Edit `.env.cloudrun.yaml`:

  ```yaml
  PUBLIC_APP_URL: "https://noseprints-xxxxx-uc.a.run.app"
  ```

  Redeploy (same script) **or** update env in Cloud Console → Cloud Run → `noseprints` → Edit & deploy new revision.

  Invite / password-reset links need this.

  ---

  ## Step 7 — Acceptance tests (must all pass)

  Open these on phone **and** laptop:

  | Check | How |
  |-------|-----|
  | Health | `GET https://YOUR.run.app/health` → `status: healthy`, `database: connected`, models loaded, `storage` not local-only |
  | Home PWA | Site loads over HTTPS |
  | Register | Register a test dog with nose crop |
  | Identify | Identify returns a result (staff queue if likely) |
  | Staff | `https://YOUR.run.app/staff` login works |
  | Photos | After a redeploy later, old photos still load (proves R2) |

  If `/health` is `degraded` / DB disconnected: fix `DATABASE_URL` (port 5432, SSL, password encoding) and redeploy.

  If OOM / crash: confirm memory is **2Gi**, not 512Mi.

  ---

  ## Step 8 — Retire laptop tunnel for public users

  Once Cloud Run passes acceptance:

  1. Share the **Cloud Run** URL (or domain) as the official app.
  2. Stop relying on `noseprints.farhanbuilds.in` / local Cloudflare tunnel for public traffic.
  3. Keep local API only for development.

  ---

  ## Step 9 — Optional Phase B (brand domain)

  1. Cloud Run → manage custom domains → map **`id.pawfriend.in`**
  2. Add the DNS records Google shows at your domain DNS
  3. Set `PUBLIC_APP_URL=https://id.pawfriend.in` and redeploy env
  4. Link from pawfriend.in marketing site → `id.pawfriend.in` (no code merge)

  ---

  ## Step 10 — Optional SMTP (multi-admin email)

  When ready for real invite/reset emails (instead of copyable staging links), add to `.env.cloudrun.yaml`:

  ```yaml
  SMTP_HOST: "..."
  SMTP_PORT: "587"
  SMTP_USER: "..."
  SMTP_PASSWORD: "..."
  SMTP_FROM: "noreply@pawfriend.in"
  SMTP_USE_TLS: "true"
  ```

  Redeploy. Until then, Admin → Invite returns a link you can copy.

  ---

  ## What gets deployed vs what you only configure

  | Piece | How it goes live |
  |-------|------------------|
  | Frontend (React PWA) | Built into Cloud Run image |
  | Backend (FastAPI) | Same image |
  | ML (`nose_detector.onnx`, `embedding_model.onnx`) | Copied from this PC into the image at build |
  | Staff UI / RBAC / queue | Same frontend + backend |
  | Supabase DB | Already running — only `DATABASE_URL` |
  | Photos | R2/S3 via `S3_*` env |
  | Custom domain / SMTP | Optional after first URL works |

  **One deploy = full app.** You do not deploy frontend, backend, and models to three places.

  ---

  ## Redeploy after code or model changes

  From this PC (models + latest code):

  ```powershell
  cd D:\NosePrints-Pawfriend
  .\scripts\cloud_run_deploy.ps1 -ProjectId YOUR_PROJECT_ID
  ```

  Never deploy from a machine that lacks the `.onnx` files.

  ---

  ## Troubleshooting (quick)

  | Symptom | Fix |
  |---------|-----|
  | `gcloud` not found | Install Cloud SDK; restart PowerShell |
  | Docker errors | Start Docker Desktop; wait until it is ready |
  | Build missing models | Confirm `backend\models\*.onnx` on this PC |
  | DB disconnected | Port 5432, unpause Supabase, encode password |
  | Photos 404 after redeploy | Configure R2 / `S3_PUBLIC_BASE_URL` |
  | Weak JWT / won’t start | `DEBUG=false` needs a unique 32+ char `JWT_SECRET_KEY` |
  | Huge bill | Ensure **min instances = 0**; check budget alert |

  ---

  ## Done when

  - [ ] Public Cloud Run HTTPS URL works without your PC  
  - [ ] `/health` healthy + DB connected + real models  
  - [ ] Photos durable on R2  
  - [ ] Staff login + register + identify verified on phone  
  - [ ] `$1` budget alert on  
  - [ ] Tunnel no longer required for users  

  **Plans / costs:** [`FINAL_DEPLOYMENT_PLAN.md`](./FINAL_DEPLOYMENT_PLAN.md) · [`COST_AND_UNIT_ECONOMICS.md`](./COST_AND_UNIT_ECONOMICS.md) · longer CLI companion [`DEPLOY.md`](./DEPLOY.md)

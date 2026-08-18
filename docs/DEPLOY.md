# NosePrints — standalone free deployment guide

Follow this **in order**. Do not skip steps.  
This deploys **this project only** (its own HTTPS URL). PawFriend.in comes later.

**Time:** about 45–90 minutes the first time.  
**Cost:** $0 for a light internship demo if you stay on Google Cloud’s free allowance (billing account required).  
**When you are done:** you can open the app on your phone over HTTPS, register a dog, identify it, and log in as staff.

---

## Stop — Hugging Face Docker is no longer free

On https://huggingface.co/new-space, **Gradio** and **Docker** now show **Paid**. That is real, not a glitch.

- Do **not** click **Subscribe to PRO** unless you want to pay **$9/month**.
- Do **not** create a **Static** Space. Static is only HTML. It cannot run FastAPI or the ONNX models. Identify will not work.

**What to do instead:** close that Hugging Face tab. Use **Google Cloud Run** (steps from Step 3 below). Same `Dockerfile`, same Supabase database.

Skip Hugging Face entirely unless you later choose the optional $9 PRO path at the bottom of this file.

---

## Local run on this PC (phone / laptop via Cloudflare)

Keep **Supabase**. Do **not** start `docker-compose` for Postgres.

Leave both processes running on this PC. Add a **new** hostname on your existing tunnel `systems` — do not reuse `systems.farhanbuilds.in` or `trace-x.farhanbuilds.in`.

**Terminal 1 — API**

```powershell
cd D:\NosePrints-Pawfriend\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Wait until you see `Application startup complete`. Then open http://127.0.0.1:8000/health — `database` must be `connected` and `embedding_mode` must be `real`.

**Terminal 2 — website (for Cloudflare)**

```powershell
cd D:\NosePrints-Pawfriend\frontend
npm run tunnel
```

This **builds** the site then serves it on port 5173 (do not use `npm run dev` for the public URL — the Vite dev server goes blank through Cloudflare). Open http://127.0.0.1:5173 on this PC. Rebuild by stopping that terminal (Ctrl+C) and running `npm run tunnel` again after UI changes.

**Cloudflare Zero Trust → Networks → Tunnels → `systems` → Public Hostname → Add**

| Field | Value |
|--------|--------|
| Subdomain | `noseprints` |
| Domain | `farhanbuilds.in` |
| Type | HTTP |
| URL | `localhost:5173` |

Save. Phone, laptop, and this PC then use:

`https://noseprints.farhanbuilds.in`

Do not point the hostname at port 8000. Vite on 5173 already proxies `/api`, `/uploads`, and `/health`.

Staff login is `/staff` with `STAFF_BOOTSTRAP_EMAIL` / `STAFF_BOOTSTRAP_PASSWORD` from `backend/.env` (created on first API start if the table was empty).

---

## What you are deploying

Three things work together:

1. **Supabase** — PostgreSQL + `pgvector` (already set up).
2. **Google Cloud Run** — runs the website + API + ONNX models in Docker.
3. **Your two model files** from this PC (they are **not** on GitHub). The Cloud Run build must run **from this PC** so those files are included.

Do **not** use Vercel / Netlify / GitHub Pages / Hugging Face Static for the whole app.

Do **not** use Render or Koyeb **free** instances. Those are **512 MB RAM**. This app loads ~112 MB of ONNX models and will be killed for memory.

---

## Accounts you need

| # | Account | Link |
|---|---------|------|
| 1 | Supabase | already done |
| 2 | Google account | https://console.cloud.google.com |

You also need this project on disk:

`D:\NosePrints-Pawfriend`

---

## Fill this in as you go (keep it private)

Copy this into Notepad. You will fill the blanks.

```text
JWT_SECRET =
STAFF_EMAIL =
STAFF_PASSWORD =
SUPABASE_DB_URI =
GOOGLE_PROJECT_ID =
APP_URL = https://noseprints-xxxxx-uc.a.run.app
```

Do not commit this file. Do not paste it in a public chat.

---

# Step 0 — Check models exist on this PC

Open **PowerShell**:

```powershell
dir D:\NosePrints-Pawfriend\backend\models\*.onnx
```

You must see **both**:

| File | About |
|------|--------|
| `nose_detector.onnx` | ~12 MB |
| `embedding_model.onnx` | ~100 MB |

If either is missing, **stop**. Deployment will not work.

---

# Step 1 — Create a JWT secret and staff login

Still in PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the printed line into `JWT_SECRET` in your Notepad.

Choose staff login (you will use this on `/staff`):

- `STAFF_EMAIL` — a real email you control, e.g. `you@gmail.com`
- `STAFF_PASSWORD` — at least **8 characters**

Write both in Notepad.

---

# Step 2 — Create the database (Supabase)

## 2.1 Create a project

1. Open https://supabase.com and sign in.
2. Click **New project**.
3. Organization: your personal org.
4. **Name:** `noseprints` (any name).
5. **Database password:** generate a strong password.  
   **Save it.** If you lose it you must reset it.
6. **Region:** pick the closest (e.g. Mumbai / Singapore / Frankfurt).
7. Click **Create new project**.
8. Wait until the project status is ready (green / healthy). This can take a few minutes.

## 2.2 Turn on pgvector

1. In the left sidebar click **Database**.
2. Click **Extensions**.
3. Search for `vector`.
4. Enable **vector**.

If you prefer SQL: left sidebar **SQL Editor** → New query → run:

```sql
create extension if not exists vector;
```

Click **Run**. You should see success.

## 2.3 Copy the connection URI

1. Click the **gear (Project Settings)** in the left sidebar.
2. Click **Database**.
3. Find **Connection string** / **URI**.
4. Copy a URI on port **5432**. Either of these is fine:
   - **Direct connection** (`db.xxxxx.supabase.co`, user `postgres`)
   - **Session pooler** (`aws-0-….pooler.supabase.com:5432`, user `postgres.xxxxx`)
   **Do not** use the transaction pooler on port **6543**.
5. Copy the URI. Session pooler looks like:

```text
postgresql://postgres.PROJECTREF:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

6. Replace `[YOUR-PASSWORD]` or `YOUR_PASSWORD` with the real database password from 2.1.

**Special characters in the password:** if the password contains `@`, `#`, `%`, `/`, `?`, you must URL-encode them before putting them in the URI.

Examples:

| Character | Encode as |
|-----------|-----------|
| `@` | `%40` |
| `#` | `%23` |
| `%` | `%25` |
| `/` | `%2F` |

Paste the finished URI into `SUPABASE_DB_URI` in Notepad.

## 2.4 You do **not** need the rest of Supabase

This app talks to Postgres through FastAPI. Skip **Auth**, **Storage**, **Edge Functions**, and **Realtime**.

Refresh **Table Editor**. The five app tables should exist (`owners`, `dogs`, `nose_prints`, `match_logs`, `staff_users`). The red **UNRESTRICTED** tags should be gone after the API first connects (Row Level Security is enabled so the public REST key cannot dump owner phones).

Do **not** add an HNSW index yet. That is only useful after ~1,000 stored nose prints.

---

# Step 3 — Google Cloud project

Google asks for a billing account. That is normal. This demo usually stays at **$0**. Add a **budget alert of $1** so you get an email if anything unexpected happens.

## 3.1 Create the project

1. Open https://console.cloud.google.com
2. Sign in with a Google account.
3. Click the project picker (top bar) → **New project**.
4. **Project name:** `noseprints`
5. Create. Wait until it is selected in the top bar.
6. Copy the **Project ID** (not only the name) into Notepad as `GOOGLE_PROJECT_ID`.

## 3.2 Enable billing + a $1 budget

1. Open https://console.cloud.google.com/billing
2. Link a billing account to this project (debit/credit card). Google still has a free allowance for Cloud Run.
3. Open https://console.cloud.google.com/billing/budgets
4. **Create budget** → amount **1 USD** → email alerts on.

## 3.3 Enable APIs

Open this URL (it uses the current project):

https://console.cloud.google.com/apis/library

Enable these three (search each name → Enable):

- **Cloud Run API**
- **Cloud Build API**
- **Artifact Registry API**

---

# Step 4 — Install the Google Cloud CLI on this PC

1. Download and install: https://cloud.google.com/sdk/docs/install
2. Close and reopen **PowerShell**.
3. Run:

```powershell
gcloud init
```

4. Browser login → pick the same Google account.
5. Pick the `noseprints` project (`GOOGLE_PROJECT_ID`).
6. Default region: choose **`us-central1`** (this region is on the Cloud Run free allowance).

Check:

```powershell
gcloud config get-value project
```

It must print your `GOOGLE_PROJECT_ID`.

---

# Step 5 — Confirm models are on this PC (required)

Cloud Run builds from this folder. GitHub does **not** have the `.onnx` files.

```powershell
dir D:\NosePrints-Pawfriend\backend\models\*.onnx
```

You must see both files. If not, stop.

Do **not** set `DATABASE_SSL_VERIFY=false` on Cloud Run. That flag is only for this Windows PC if antivirus breaks TLS.

---

# Step 6 — Deploy from this PC

Open **PowerShell**. Replace the four `YOUR_*` values with Notepad.

`SUPABASE_DB_URI` must already have `@` in the password encoded as `%40`.

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

First build often takes **15–25 minutes**. Leave the PC on and the terminal open.

When it finishes, it prints a **Service URL** like:

```text
https://noseprints-xxxxxxxxxx-uc.a.run.app
```

Paste that into Notepad as `APP_URL` (no trailing slash).

If PowerShell mangles the URI (password / `%40`), skip `--set-env-vars` on the first command, then set variables in the Console (Step 7).

---

# Step 7 — Environment variables in the Console (if the CLI skipped them)

1. Open https://console.cloud.google.com/run
2. Click service **noseprints**.
3. **Edit & deploy new revision**.
4. **Container, Variables & Secrets, Connections, Security** → **Variables & Secrets**.
5. Add:

| Name | Value |
|------|--------|
| `DATABASE_URL` | `SUPABASE_DB_URI` from Notepad |
| `JWT_SECRET_KEY` | `JWT_SECRET` |
| `STAFF_BOOTSTRAP_PASSWORD` | `STAFF_PASSWORD` |
| `STAFF_BOOTSTRAP_EMAIL` | `STAFF_EMAIL` |
| `DEBUG` | `false` |
| `SERVE_FRONTEND` | `true` |
| `FRONTEND_DIR` | `/app/frontend_dist` |
| `CORS_ORIGINS` | your `APP_URL` with no trailing slash |

6. Confirm **Memory** is **2 GiB** (not 512 MiB).
7. Deploy.

Do **not** set `S3_*` or `SMTP_*` yet. Photos live on the container disk and can disappear when a new revision deploys. That is OK for a first test.

Same-origin PWA + API means CORS is not required for the phone/PC app itself. Set `CORS_ORIGINS` anyway so it matches `APP_URL`.

---

# Step 8 — Health check (must pass before testing the UI)

Open:

```text
https://YOUR-APP-URL/health
```

You want JSON like:

```json
{
  "status": "healthy",
  "database": "connected",
  "ml_models": {
    "nose_detector_loaded": true,
    "nose_detector_file": true,
    "embedding_extractor_loaded": true,
    "embedding_extractor_file": true,
    "embedding_mode": "real"
  }
}
```

### If health is wrong — fix this before going further

| What you see | What to do |
|--------------|------------|
| 404 / service not found | Wait for the first deploy; check Cloud Run **Logs** |
| Cold start takes 30–90s | Normal. Refresh once. |
| `"database": "disconnected"` | Wrong `DATABASE_URL`; port **5432**; password `%40` encoding |
| `"embedding_mode"` is not `"real"` | Models missing from the image. Confirm `.onnx` files exist locally, then redeploy `--source .` |
| `JWT_SECRET_KEY must be a strong unique secret` | Secret too short or still `dev-only-...` |
| Memory / OOM / killed | Memory must be **2 GiB**, not 512 MiB |
| Container failed to start | Logs → look for missing env vars |

Logs: Cloud Run service → **Logs**.

---

# Step 9 — Test the live app (PC, then phone)

## 9.1 On your PC

1. Open `APP_URL` (the `*.run.app` URL).
2. You should see the NosePrints home page (not a JSON blob).
3. Open **Register** → create owner + dog + 3 nose photos.
4. Open **Identify** → scan the same dog → likely/possible match and side-by-side photos.
5. Open `/staff` → log in with `STAFF_EMAIL` / `STAFF_PASSWORD`.
6. Confirm the match. Owner phone must appear **only here**, never on Identify.

## 9.2 On your phone

1. Use **mobile data** or any Wi‑Fi (does not need to be this PC’s Wi‑Fi).
2. Chrome (Android) or Safari (iPhone) → open `APP_URL`.
3. HTTPS padlock should be present.
4. Repeat identify + camera.
5. **Install:**
   - Android Chrome: menu → **Install app** / **Add to Home screen**
   - iPhone Safari: Share → **Add to Home Screen**

If the first load is slow, the service scaled to zero. Wait and refresh.

---

# Step 10 — You are deployed when all of this is true

- [ ] `/health` shows `database: connected` and `embedding_mode: real`
- [ ] Home page loads on HTTPS
- [ ] Register + identify work
- [ ] Staff login works
- [ ] Owner contact is hidden on Identify
- [ ] Phone camera works on the `*.run.app` URL

Until that list is complete, do not share the link with PawFriend as “live”.

---

# Troubleshooting

**Blank white page**  
- `SERVE_FRONTEND` must be `true`  
- Cloud Build logs must show `npm run build` succeeded  

**Identify returns 503**  
- Models not in the image → `.onnx` files must exist under `backend/models/` on this PC, then redeploy `--source .`  
- `.gcloudignore` must **not** list `*.onnx` (it does not)

**Staff login fails**  
- Bootstrap only runs if `staff_users` is empty  
- Email must match `STAFF_BOOTSTRAP_EMAIL` exactly  
- Password at least 8 characters  

**Database errors about `vector` / `<=>`**  
- Extension `vector` is not enabled on Supabase  

**Do not put real owner data on a public URL until you have tested staff privacy**

---

# What this deploy does *not* include

- Custom domain / pawfriend.in (later)
- Durable photo storage (Cloudflare R2 / B2) — add after the app works
- Email to owners (SMTP) — optional later
- Paying for always-on instances (Cloud Run can scale to zero)

---

# Later: attach PawFriend

Do **not** rebuild the product. Only:

1. Point a domain (e.g. `id.pawfriend.in`) at this same Cloud Run service.
2. Change `CORS_ORIGINS` to that `https://` origin.
3. Keep `DEBUG=false` and the same Supabase database.

---

# Optional: Hugging Face anyway ($9/month)

Only if you want the original Space workflow.

1. Subscribe at https://huggingface.co/pro
2. Then create a **Docker** Space, app port **7860**, CPU basic.
3. Upload this repo **including** `backend/models/*.onnx`.
4. Set the same env vars as Step 7, plus `CORS_ORIGINS` = `https://YOURUSER-noseprints.hf.space`

CPU Basic on a PRO account has **no hourly compute charge**. You pay the PRO subscription.

---

# Optional: test Docker on your PC first

Only if Docker Desktop is installed. This is **not** required to deploy.

```powershell
cd D:\NosePrints-Pawfriend
docker build -t noseprints .
```

If this build fails, Cloud Run’s build will fail too — fix the error before deploying.

---

# File map

| Path | Role |
|------|------|
| `Dockerfile` | Builds frontend, installs Python, starts API |
| `backend/start.sh` | Runs uvicorn on `$PORT` (Cloud Run sets this) |
| `backend/models/*.onnx` | Required for real matching |
| `.gcloudignore` | Uploads models; skips venv / node_modules / `.env` |
| This file | `docs/DEPLOY.md` |

# NosePrints × PawFriend — Final Deployment Plan

**Status:** Locked architecture · Cloud deploy pending credentials  
**Audience:** Farhan, mentors, PawFriend tech lead  
**Last updated:** 2026-11-16  

This is the **authoritative deployment plan** for where the system runs today, where it will run in production, and how we get there. Step-by-step CLI detail stays in [`DEPLOY.md`](./DEPLOY.md). Nationwide product readiness: [`NATIONWIDE_READINESS_ROADMAP.md`](./NATIONWIDE_READINESS_ROADMAP.md). **Costing & unit economics:** [`COST_AND_UNIT_ECONOMICS.md`](./COST_AND_UNIT_ECONOMICS.md).  
**Click-by-click deploy:** [`FINAL_DEPLOY_GUIDE.md`](./FINAL_DEPLOY_GUIDE.md).

---

## 1. One-line decision

**Deploy NosePrints as a standalone Google Cloud Run service** (React PWA + FastAPI + ONNX in one container), backed by **Supabase Postgres + pgvector**, with **durable object storage** for photos, then attach the public brand URL **`https://id.pawfriend.in`**.

Do **not** merge into the main pawfriend.in monolith. Do **not** host production on a laptop + Cloudflare tunnel.

---

## 2. Where it runs (current vs target)

| Environment | Where | Purpose | Status |
|-------------|--------|---------|--------|
| **Local / tunnel (now)** | PC (`localhost:8000` API + `localhost:5173` / Cloudflare tunnel) | Live testing, staff ops, demos | **Active** |
| **Cloud production (target)** | Google **Cloud Run** `us-central1`, service `noseprints` | Public HTTPS, scale-to-zero, always reachable | **Not deployed yet** — needs `gcloud` + Docker + billing |
| **Database (both)** | **Supabase** Postgres + `pgvector` (port **5432**) | Owners, dogs, embeddings, staff, audit | **Connected** |
| **Photos (target)** | S3-compatible bucket (Cloudflare **R2** preferred; B2/GCS OK) | Survive container restarts | **Local disk today** — must switch before prod |
| **Public brand URL (Phase B)** | Custom domain **`id.pawfriend.in`** → Cloud Run | PawFriend-facing identity product | After first `*.run.app` is stable |
| **Staging (recommended)** | Separate Cloud Run service + separate Supabase project | Safe invite/erasure/ML tests | Create before nationwide traffic |

```
Phone / laptop (HTTPS)
        │
        ▼
┌──────────────────────────────────────┐
│  Google Cloud Run — "noseprints"     │
│  Region: us-central1                 │
│  Memory: 2 GiB · CPU: 1              │
│  • React PWA (static)                │
│  • FastAPI /api/v1                   │
│  • nose_detector.onnx                │
│  • embedding_model.onnx              │
└───────────────┬──────────────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌───────────────┐  ┌─────────────────────┐
│ Supabase      │  │ Object storage       │
│ Postgres +    │  │ (R2 / B2 / GCS)     │
│ pgvector      │  │ nose + look photos  │
└───────────────┘  └─────────────────────┘
```

---

## 3. What is deployed in the Cloud Run image

Built from repo root via Dockerfile / `gcloud run deploy --source .` (models must exist on the build machine — **not** committed to GitHub):

| Layer | Contents |
|-------|----------|
| Frontend | Built Vite PWA (`SERVE_FRONTEND=true`) |
| Backend | FastAPI app under `/api/v1`, `/health` |
| ML | `nose_detector.onnx`, `embedding_model.onnx` |
| Staff | JWT auth, roles, invite/reset, match queue, registry, DPDP erase |

Helper script: [`scripts/cloud_run_deploy.ps1`](../scripts/cloud_run_deploy.ps1)  
Env template: [`.env.cloudrun.yaml.example`](../.env.cloudrun.yaml.example)

---

## 4. Deployment phases

### Phase A — Standalone cloud demo (next production step)

**Goal:** Public `https://*.run.app` URL that works without Farhan’s PC.

1. Install **Google Cloud SDK** (`gcloud`) and enable billing + **$1 budget alert**
2. Start **Docker Desktop**
3. Configure durable photos: `S3_*` + `S3_PUBLIC_BASE_URL` (R2 recommended)
4. Create `.env.cloudrun.yaml` from the example (never commit secrets)
5. Deploy:

```powershell
cd D:\NosePrints-Pawfriend
.\scripts\cloud_run_deploy.ps1 -ProjectId YOUR_GCP_PROJECT
```

6. Verify `/health` → `healthy`, `database: connected`, models loaded, `storage` = S3 mode  
7. Staff login + one identify + confirm on the Cloud Run URL  
8. Retire **public** use of the local Cloudflare tunnel  

**Locked choices for Phase A:**

| Item | Choice |
|------|--------|
| Host | Google Cloud Run `us-central1` |
| DB | Existing / production Supabase project |
| App shape | Single service (UI + API + ONNX) |
| Domain | Temporary `*.run.app` first |
| Merge into pawfriend.in | **No** |

### Phase B — Brand domain + ops hardening

**Goal:** Production-looking nationwide entry point.

1. Map **`id.pawfriend.in`** to Cloud Run  
2. Set `PUBLIC_APP_URL=https://id.pawfriend.in` (invite/reset links)  
3. Optional SMTP for staff invite + password reset + owner notify  
4. Uptime checks on `/health`; alerts on 5xx / DB disconnect  
5. Staging service (`noseprints-staging`) + separate Supabase project  
6. Link from pawfriend.in marketing site → `id.pawfriend.in` (no code merge)

### Phase C — Nationwide scale (product + ML, not a different host)

Hosting stays Cloud Run + Supabase + object storage. Scale means:

- Multi-admin staff (already in product)
- Consented dog pilot → fine-tune → promote-only-if-better ONNX
- Backups ([`SUPABASE_BACKUP_RUNBOOK.md`](./SUPABASE_BACKUP_RUNBOOK.md))
- Retention / DPDP ops ([`RETENTION_AND_DPDP.md`](./RETENTION_AND_DPDP.md))
- Keep **human-in-the-loop** staff confirmation — never claim “identifies all dogs”

---

## 5. Required secrets & env (production)

Set on Cloud Run (via `.env.cloudrun.yaml` or Console). Never commit real values.

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | Supabase async URL (port **5432**) |
| `JWT_SECRET_KEY` | Yes | 32+ unique chars; `DEBUG=false` refuses weak secrets |
| `DEBUG` | Yes | `false` in production |
| `SERVE_FRONTEND` | Yes | `true` |
| `S3_ENDPOINT_URL` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET_NAME` / `S3_PUBLIC_BASE_URL` | Yes for prod | Durable photos |
| `PUBLIC_APP_URL` | Yes after first URL known | Invite / reset links |
| `MATCH_STRICT_DEMO` | Recommended `true` | Cautious public demos |
| `STAFF_BOOTSTRAP_*` | Only if staff table empty | First admin |
| `SMTP_*` | Optional | Email invite/reset/owner notify |

Full CLI walkthrough: [`DEPLOY.md`](./DEPLOY.md) · Checklist: [`CLOUD_HOSTING_CHECKLIST.md`](./CLOUD_HOSTING_CHECKLIST.md)

---

## 6. What we explicitly will not do

| Rejected option | Why |
|-----------------|-----|
| Host production on laptop + tunnel | Unreliable, not nationwide |
| Hugging Face free / 512 MB hosts | OOM — ONNX + API need ~2 GiB |
| Merge into existing pawfriend.in web app | Keep identity service separate |
| Commit ONNX / secrets to GitHub | Size + security |
| Drop staff confirmation for “fully automatic ID” | Safety / accuracy honesty |
| Buy Nexdata without sample/licence gate | Cost + rights risk |

---

## 7. Go-live acceptance checklist

Before calling the system “deployed for public use”:

- [ ] Cloud Run URL returns `/health` = healthy with DB connected  
- [ ] Storage mode is durable (not local-only)  
- [ ] Staff login, match queue, confirm/reject work over HTTPS on phone  
- [ ] Invite + password-reset links use `PUBLIC_APP_URL`  
- [ ] Junk/test dogs purged; strict demo understood by staff  
- [ ] Budget alert set; JWT is not the example secret  
- [ ] Tunnel no longer required for external users  
- [ ] (Phase B) `id.pawfriend.in` resolves and serves the same service  

---

## 8. Current state (honest)

| Piece | State |
|-------|--------|
| Product / Staff / RBAC / audit / erasure | Implemented and running locally |
| Supabase DB | Connected |
| Local demo / tunnel | Working for testing |
| Cloud Run production deploy | **Blocked on** `gcloud` install, Docker Desktop, GCP billing, object-storage credentials |
| Custom domain | Not yet |
| Field accuracy claim | Requires consented pilot dogs — see [`ML_PILOT_PROGRAM.md`](./ML_PILOT_PROGRAM.md) |

---

## 9. Related documents

| Doc | Use |
|-----|-----|
| [`DEPLOY.md`](./DEPLOY.md) | Detailed deploy commands |
| [`PHASE_A_DEPLOYMENT.md`](./PHASE_A_DEPLOYMENT.md) | Original Phase A plan |
| [`FINAL_DEPLOY_GUIDE.md`](./FINAL_DEPLOY_GUIDE.md) | Step-by-step guide to deploy everything |
| [`COST_AND_UNIT_ECONOMICS.md`](./COST_AND_UNIT_ECONOMICS.md) | Costing parameters + unit economics (current) |
| [`PHASE_A_COST_ESTIMATE.md`](./PHASE_A_COST_ESTIMATE.md) | Earlier Phase A cost note (same model) |
| [`CLOUD_HOSTING_CHECKLIST.md`](./CLOUD_HOSTING_CHECKLIST.md) | Pre-flight checklist |
| [`NATIONWIDE_READINESS_ROADMAP.md`](./NATIONWIDE_READINESS_ROADMAP.md) | Product scale beyond hosting |
| [`SUPABASE_BACKUP_RUNBOOK.md`](./SUPABASE_BACKUP_RUNBOOK.md) | Backup / restore |

---

## 10. Owner actions to unblock production

1. Create / confirm GCP project + billing + budget alert  
2. Install `gcloud` and start Docker Desktop  
3. Create R2 (or B2/GCS) bucket and fill `S3_*`  
4. Copy `.env.cloudrun.yaml.example` → `.env.cloudrun.yaml` with real secrets  
5. Run `.\scripts\cloud_run_deploy.ps1 -ProjectId YOUR_PROJECT`  
6. Share the `*.run.app` URL for acceptance; then map `id.pawfriend.in`

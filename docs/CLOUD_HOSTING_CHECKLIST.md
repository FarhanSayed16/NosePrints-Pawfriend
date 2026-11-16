# Cloud hosting checklist (P3)

Target: Google Cloud Run (`us-central1`) + Supabase Postgres + S3-compatible durable photos. Detail: [DEPLOY.md](./DEPLOY.md), [PHASE_A_DEPLOYMENT.md](./PHASE_A_DEPLOYMENT.md).

## Prerequisites

- [ ] Google Cloud project with billing + **$1 budget alert**
- [ ] `gcloud` CLI installed and authenticated
- [ ] Docker Desktop running (Cloud Build / local image builds)
- [ ] `backend/models/nose_detector.onnx` and `embedding_model.onnx` on disk
- [ ] Supabase project **not paused**; `DATABASE_URL` uses port **5432**
- [ ] Object storage (R2 / B2 / GCS) with `S3_*` + `S3_PUBLIC_BASE_URL`
- [ ] Strong `JWT_SECRET_KEY` (32+ chars); `DEBUG=false`
- [ ] Optional SMTP for invites/resets; else use staging link copy from API
- [ ] `PUBLIC_APP_URL` set to the public HTTPS origin

## Deploy

```powershell
# From repo root
.\scripts\cloud_run_deploy.ps1 -ProjectId YOUR_GCP_PROJECT
```

Or follow `docs/DEPLOY.md` with `gcloud run deploy --source .`.

Recommended env (Cloud Run):

| Var | Notes |
|-----|--------|
| `DATABASE_URL` | Supabase async URL |
| `JWT_SECRET_KEY` | Unique secret |
| `S3_*` / `S3_PUBLIC_BASE_URL` | Durable photos |
| `PUBLIC_APP_URL` | Invite/reset links |
| `SERVE_FRONTEND=true` | Bundled in Dockerfile |
| `MATCH_STRICT_DEMO` | Keep true for cautious public demos |

Create `.env.cloudrun.yaml` for `--env-vars-file` (never commit secrets).

## After deploy

- [ ] `GET /health` → `healthy`, `database: connected`, models loaded, `storage` not ephemeral-only for prod
- [ ] Staff login works on the `*.run.app` URL
- [ ] Upload a nose photo; confirm object exists in bucket after container recycle
- [ ] Map custom domain toward `id.pawfriend.in`
- [ ] Uptime check on `/health`; alert on 5xx / DB disconnect
- [ ] Retire public reliance on local Cloudflare tunnel

## Staging vs production

Use separate Supabase projects and Cloud Run services (`noseprints-staging` / `noseprints`). Never point staging at production data for destructive tests.

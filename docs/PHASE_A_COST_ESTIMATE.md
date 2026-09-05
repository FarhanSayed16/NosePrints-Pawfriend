# NosePrints Phase A — Cost Estimation & Unit Metrics

**Audience:** Intern, mentor, PawFriend technical / finance lead  
**Scope:** Standalone demo on **Google Cloud Run** + **Supabase** (+ optional **Cloudflare R2**)  
**Region assumption:** Cloud Run in **`us-central1`** (free-tier eligible)  
**Currency:** USD  
**Status:** Estimates for planning. Always verify current list prices on vendor sites before committing budget.

**Related:** [`PHASE_A_DEPLOYMENT.md`](./PHASE_A_DEPLOYMENT.md) · [`DEPLOY.md`](./DEPLOY.md)

---

## 1. Executive summary (what to tell seniors)

| Scenario | Expected monthly bill | Notes |
|----------|----------------------|--------|
| **A — Light internship demo** (scale-to-zero, free tiers, local photos) | **~$0** | Billing card required on GCP; set **$1 budget alert** |
| **B — Closed pilot** (~10–50 dogs, staff + phones, durable R2 photos) | **~$0–5** | Usually still inside free tiers if traffic is low |
| **C — Busy NGO month** (~5k identify scans, always some cold starts) | **~$5–25** | Mostly Cloud Run CPU/memory after free allowance |
| **D — Always-on / min instances = 1** | **~$40–80+** | Avoid for Phase A — kills the free model |

**Recommendation for Phase A:** Stay on **Scenario A or B**. Do **not** set `min instances > 0`. Prefer Cloudflare R2 free tier for photos if you need durability.

**One-line pitch:**  
> Phase A is designed to run at **near-zero cost** on Cloud Run free allowance + Supabase Free + optional R2 Free. Billing is required on GCP so Google can charge *if* we exceed free limits; a **$1 budget alert** is the safety net.

---

## 2. What we pay for (cost stack)

```
┌─────────────────────────────────────────────────────────┐
│  Google Cloud (billing account required)                │
│  • Cloud Run  — compute while handling requests         │
│  • Cloud Build — image builds on deploy                 │
│  • Artifact Registry — container image storage          │
│  • Egress — bytes out to phones                         │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  Supabase Free (separate account)                       │
│  • Postgres + pgvector — metadata & embeddings          │
│  • We do NOT use Supabase Auth / Storage for Phase A    │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  Optional: Cloudflare R2 Free                           │
│  • Durable dog / nose / match photos                    │
└─────────────────────────────────────────────────────────┘
```

| Component | Required for Phase A? | If skipped |
|-----------|----------------------|------------|
| Cloud Run | **Yes** | No public HTTPS demo |
| Supabase Postgres | **Yes** | No registry / matching |
| R2 / B2 photos | **Recommended** before staff pilot | Photos on container disk vanish on redeploy |
| Custom domain | No (Phase B) | Use `*.run.app` |
| SMTP / WhatsApp | No | No owner emails |
| GPU | **No** (inference is CPU + ONNX) | — |

---

## 3. Unit metrics (how billing works)

### 3.1 Cloud Run — request-based billing (our default)

We bill only while a request is being handled (plus brief startup). Scale-to-zero when idle → **$0** while nobody uses the app.

| Unit | Meaning | Free / month (request-based, Tier-1 regions e.g. `us-central1`) | Approx list price after free* |
|------|---------|------------------------------------------------------------------|-------------------------------|
| **Request** | One HTTP call (page, `/api/...`, `/health`) | **2,000,000** | ~$0.40 / million |
| **vCPU-second** | 1 vCPU allocated for 1 second | **180,000** | ~$0.000024 / vCPU-s |
| **GiB-second** | 1 GiB RAM allocated for 1 second | **360,000** | ~$0.0000025 / GiB-s |
| **Egress** | Data out to internet (North America) | **~1 GiB** | ~$0.12 / GiB after free (varies by destination) |

\*Rates change; check [Cloud Run pricing](https://cloud.google.com/run/pricing). Free tier is per **billing account**, not per project.

**Our Phase A container sizing**

| Setting | Value | Why |
|---------|--------|-----|
| CPU | **1** | Enough for ONNX on CPU |
| Memory | **2 GiB** | Models ~112 MB + runtime; 512 MiB OOMs |
| Min instances | **0** | Scale to zero → idle cost $0 |
| Max instances | 1–3 | Cap surprise bills |
| Timeout | 300 s | Identify can be slow on cold start |

**Useful formulas (request-based)**

```text
vCPU-seconds  ≈  requests × (avg_duration_sec) × vCPU
GiB-seconds   ≈  requests × (avg_duration_sec) × memory_GiB
```

Example: **1,000** identify-style requests × **3 s** active × **1** vCPU × **2 GiB**:

```text
vCPU-s  = 1000 × 3 × 1 = 3,000      (free allowance 180,000)
GiB-s   = 1000 × 3 × 2 = 6,000      (free allowance 360,000)
```

→ Still **well inside free tier**.

**Cold starts:** First request after idle may take **30–90 s** (model load). That time counts toward CPU/memory allocation. Still cheap at demo volume.

### 3.2 Cloud Build & Artifact Registry

| Unit | Free / light use | Notes |
|------|------------------|--------|
| Cloud Build minutes | Generous free daily/monthly quotas for light use | First deploy ~15–25 min; rebuilds cost build minutes |
| Artifact Registry storage | Small fee if many large images retained | One NosePrints image (~hundreds of MB with models) is fine for a demo |

**Practice:** Delete old unused images occasionally; don’t keep dozens of revisions forever.

### 3.3 Supabase Free

| Metric | Free plan (approx.) | Phase A impact |
|--------|---------------------|----------------|
| Database size | **500 MB** Postgres data | Embeddings are 512-d floats — thousands of dogs still fit |
| Projects | **2** free active | One `noseprints` project is enough |
| Egress | **~5 GB** / month | API ↔ DB is small; photos should **not** live in Postgres |
| Pausing | Paused after **~7 days inactivity** | Hit the app weekly or restore if paused |
| Auth / Storage | Included but **unused** by us | No extra cost; we ignore them |

**We store URLs in Postgres, not image bytes.** Photo bytes go to Cloud Run disk or R2.

Supabase **Pro** (~$25/month) only if Free pauses too often or DB grows past 500 MB — **not needed for Phase A demo**.

### 3.4 Cloudflare R2 (optional durable photos)

| Metric | R2 free tier (typical published) | Phase A impact |
|--------|----------------------------------|----------------|
| Storage | **10 GB** / month | ~thousands of JPEG nose crops |
| Class A ops (write) | Millions free | Uploads on register/identify |
| Class B ops (read) | Millions free | `<img>` loads |
| Egress | Often **$0 egress** to internet on R2 | Better than paying GCP egress for every photo |

At pilot scale (tens of dogs, few hundred photos), R2 is effectively **$0**.

---

## 4. Worked scenarios (Phase A)

Assumptions unless noted:

- Region `us-central1`, request-based billing, **min instances = 0**, **2 GiB / 1 CPU**
- Average “heavy” request (identify / register upload): **2–5 s** billed
- Average “light” request (static HTML/JS/CSS after cold): **0.1–0.5 s**
- Prices approximate; free tier applied first

### Scenario A — Internship demo (target)

| Activity / month | Volume |
|------------------|--------|
| Unique visitors | 20–50 |
| Register dogs | 10–30 |
| Identify scans | 50–200 |
| Staff logins | 20 |
| Deploys | 2–5 |

| Line item | Estimate |
|-----------|----------|
| Cloud Run | **$0** (inside free CPU/RAM/requests) |
| Cloud Build | **$0–2** (occasional; usually free quota) |
| Artifact Registry | **~$0** |
| Egress | **$0** if &lt; 1 GiB |
| Supabase | **$0** Free |
| R2 | **$0** or skip |
| **Total** | **~$0** (plan for **$0–5** buffer) |

### Scenario B — Closed staff pilot (10–20 dogs)

| Activity / month | Volume |
|------------------|--------|
| Dogs registered | 10–20 |
| Nose photos each | 3–5 |
| Identify attempts | 100–500 |
| Full-dog photos | ~50–100 |
| Staff reviews | Daily |

| Line item | Estimate |
|-----------|----------|
| Cloud Run | **$0–5** |
| Supabase | **$0** |
| R2 (~1–5 GB photos) | **$0** |
| **Total** | **~$0–5** |

### Scenario C — Heavier NGO month

| Activity / month | Volume |
|------------------|--------|
| Identify scans | **5,000** @ ~3 s, 1 CPU, 2 GiB |
| Page loads / assets | **20,000** light requests |
| Photo egress via Cloud Run (no R2) | **5–10 GiB** |

Rough Cloud Run compute for 5,000 heavy requests:

```text
vCPU-s = 5000 × 3 × 1 = 15,000     → free
GiB-s  = 5000 × 3 × 2 = 30,000     → free
```

Still inside free compute. Cost risk is mainly:

- Many **cold starts** with long model load  
- **Egress** if photos are served from Cloud Run  
- Accidental **min instances = 1**

| Line item | Estimate |
|-----------|----------|
| Cloud Run compute | **$0–10** |
| Egress (if photos via GCP) | **$0–15** |
| Supabase | **$0** (watch 500 MB / pause) |
| R2 (photos) | **$0** (preferred — cuts egress) |
| **Total** | **~$0–25** |

### Scenario D — Always-on (do not use in Phase A)

`min-instances = 1`, 1 CPU, 2 GiB, billed ~24×30 hours even idle:

```text
Rough order: tens of USD / month (often ~$40–80+ depending on idle vs active rates)
```

**Decision:** Keep **min instances = 0** for Phase A.

---

## 5. Unit economics (product metrics vs cost)

Useful for NGO / internship write-ups — not billing units, but **cost per useful action**.

| Product unit | What it consumes | Cost at Phase A volume |
|--------------|------------------|------------------------|
| **1 dog registered** (owner + 3–5 noses + optional look) | ~5–15 API calls, DB rows, ~0.5–5 MB photos | **≪ $0.01** |
| **1 identify scan** | 1–3 s CPU @ 2 GiB, detector + embed + search | **≪ $0.01** inside free tier |
| **1 staff confirm** | Tiny DB + auth | Negligible |
| **1 redeploy** | Cloud Build minutes + new image | Usually free quota; watch build minutes |

**Storage sizing (order of magnitude)**

| Asset | Typical size | 100 dogs (3 noses + 1 look) |
|-------|--------------|-----------------------------|
| Nose crop JPEG | 50–200 KB | ~15–60 MB |
| Full-dog JPEG | 200–800 KB | ~20–80 MB |
| Embedding in Postgres (512×float4) | ~2 KB + indexes | &lt; 1 MB for 100 dogs |

Photos dominate disk; **put them in R2**, not Postgres.

---

## 6. Cost controls (mandatory for Phase A)

| Control | Action |
|---------|--------|
| Budget alert | GCP Billing → Budget **$1 USD** → email on threshold |
| Region | Deploy Cloud Run only in **`us-central1`** (or other free-tier regions) |
| Scale | `min instances = 0`, `max instances` low (1–3) |
| Memory | **2 GiB** (required) — do not “save money” with 512 MiB (service dies) |
| Photos | Prefer **R2** so GCP egress stays low |
| Idle Supabase | Open the app weekly so Free project is not paused mid-demo |
| Secrets | Never commit `.env`; rotate if leaked (abuse → bill) |
| Hugging Face Docker | **Skip** ($9/mo PRO) unless explicitly chosen |
| Always-on / GPU | **Out of scope** for Phase A |

---

## 7. Phase A vs later phases (cost outlook)

| Phase | Hosting shape | Expected monthly |
|-------|---------------|------------------|
| **A — Standalone demo** | Cloud Run scale-to-zero + Supabase Free + optional R2 | **$0–5** |
| **B — PawFriend subdomain** | Same Cloud Run + DNS; still scale-to-zero | **$0–10** |
| **Pilot growth** | Same + more photos/egress | **$5–30** |
| **Production NGO** (if always-on / Pro DB / custom domain) | Revisit: Supabase Pro, maybe min instances, monitoring | **$25–100+** (decision later) |

Phase A does **not** require PawFriend’s existing GCP app budget beyond sharing a billing account / project if they already have one.

---

## 8. Comparison: cheaper-looking options we rejected

| Option | Sticker price | Why not for NosePrints |
|--------|---------------|------------------------|
| Render / Koyeb free | $0 | **512 MB RAM** — ONNX OOM |
| Vercel / Netlify static | $0 | Cannot run FastAPI + ONNX |
| HF Static Space | $0 | HTML only |
| HF Docker Space | **$9/mo PRO** | Works but unnecessary if Cloud Run free holds |
| Always-on small VPS | ~$5–12/mo | Simpler ops for some teams, but **not** our Phase A plan |

---

## 9. Checklist for finance / mentor sign-off

- [ ] GCP billing account + **$1 budget alert** enabled  
- [ ] Cloud Run in **`us-central1`**, **2 GiB**, **min instances = 0**  
- [ ] Supabase Free project; note **pause after inactivity**  
- [ ] Optional R2 Free for durable photos (recommended before staff pilot)  
- [ ] No Hugging Face PRO unless explicitly approved  
- [ ] Expected Phase A bill: **~$0**, contingency **$5/month**  
- [ ] Revisit costs before Phase B custom domain / always-on  

---

## 10. Sources to re-check before a paid pilot

Prices and free allowances change. Before locking a multi-month NGO budget, re-read:

- [Cloud Run pricing](https://cloud.google.com/run/pricing)  
- [Supabase pricing](https://supabase.com/pricing)  
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)  

---

## 11. Sign-off blurb (copy/paste)

> **Phase A cost model:** NosePrints runs as one Cloud Run service (1 vCPU, 2 GiB, scale-to-zero) plus Supabase Free Postgres/pgvector. At internship / closed-pilot traffic we expect **~$0/month**, with a **$1 GCP budget alert** and a **$5 contingency**. Durable photos use Cloudflare R2 free tier when enabled. We do not use always-on instances, GPU, or Hugging Face PRO for Phase A. Unit cost per registration or identify scan is negligible under free allowances.

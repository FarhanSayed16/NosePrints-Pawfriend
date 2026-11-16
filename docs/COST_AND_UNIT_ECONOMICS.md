# NosePrints × PawFriend — Costing Parameters & Unit Economics

**Audience:** Farhan, mentors, PawFriend finance / tech lead  
**Aligned with:** [`FINAL_DEPLOYMENT_PLAN.md`](./FINAL_DEPLOYMENT_PLAN.md)  
**Currency:** USD (INR ≈ ×83–90 for rough local planning; re-check FX)  
**Status:** Planning estimates · re-verify vendor list prices before locking a paid pilot  
**Related:** Older Phase A note [`PHASE_A_COST_ESTIMATE.md`](./PHASE_A_COST_ESTIMATE.md) (same model; this file is current)

---

## 1. Short answer

| Question | Answer |
|----------|--------|
| Does deployment **require** ongoing spend? | **GCP billing card is required**, but with scale-to-zero + free tiers, expected bill for demo/pilot is **~$0/month** |
| What do we pay for? | Cloud Run (only while serving), optional build/storage, Supabase Free DB, optional R2 photos, optional SMTP/domain later |
| Biggest bill risk? | Setting **min instances = 1** (always-on ~$40–80+/mo), serving photos from Cloud Run egress, or abuse after leaked secrets |
| Unit cost (register / identify)? | **≪ $0.01** each at pilot volumes inside free allowances |

**Recommendation:** Deploy Cloud Run **1 vCPU / 2 GiB / min instances = 0**, Supabase Free, Cloudflare R2 Free for photos, **$1 GCP budget alert**. Stay in Scenarios A–B until nationwide traffic forces a revisit.

---

## 2. Cost stack (what can appear on an invoice)

```
Google Cloud (billing account required)
  ├─ Cloud Run      — CPU / RAM / requests while handling traffic
  ├─ Cloud Build    — minutes when you deploy
  ├─ Artifact Registry — container image storage
  └─ Egress         — bytes out (keep photos on R2 to reduce this)

Supabase (separate)
  └─ Free Postgres + pgvector  (or Pro ~$25/mo if Free limits break)

Cloudflare R2 (recommended)
  └─ Photo storage (free tier covers pilots)

Optional later
  ├─ Custom domain / DNS for id.pawfriend.in
  ├─ SMTP (Resend/SendGrid/etc.) for invites & owner email
  └─ Monitoring / uptime (often free tier)
```

| Component | Required for public cloud? | Typical Phase A–B cost |
|-----------|---------------------------|-------------------------|
| Cloud Run | Yes | **$0** inside free tier |
| Supabase Postgres | Yes | **$0** Free |
| R2 (or B2/GCS) photos | Strongly recommended | **$0** Free at pilot size |
| Custom domain | Phase B | DNS often $0–12/yr if domain already owned |
| SMTP | Optional | Free tier or ~$0–10/mo |
| GPU | **No** (CPU ONNX) | — |
| Laptop / tunnel | Dev only | Electricity only; not production |

---

## 3. Billing parameters (units vendors charge)

### 3.1 Cloud Run — request-based (our default)

Region: **`us-central1`** (Tier-1 free allowance). Idle with **min instances = 0** → **$0**.

| Parameter | Free / month (per billing account) | Approx list price after free |
|-----------|------------------------------------|------------------------------|
| Requests | **2,000,000** | ~**$0.40** / million |
| vCPU-seconds (active) | **180,000** | ~**$0.000024** / vCPU-s |
| GiB-seconds (active) | **360,000** | ~**$0.0000025** / GiB-s |
| Internet egress (GCP) | Small Always Free allowance | Often ~**$0.12** / GiB after free (destination-dependent) |

Sources to re-check: [Cloud Run pricing](https://cloud.google.com/run/pricing).

**Our production sizing (locked)**

| Setting | Value | Cost implication |
|---------|--------|------------------|
| CPU | 1 | Matches free-tier math |
| Memory | **2 GiB** | Required for ONNX; do **not** cut to 512 MiB |
| Min instances | **0** | Scale to zero → idle **$0** |
| Max instances | 1–3 | Caps surprise parallel cost |
| Billing | Request-based | Charge only while serving |

**Formulas**

```text
vCPU-seconds ≈ requests × avg_duration_sec × vCPU
GiB-seconds  ≈ requests × avg_duration_sec × memory_GiB
```

Example — **1,000** identify requests × **3 s** × 1 vCPU × 2 GiB:

```text
vCPU-s = 3,000   (free budget 180,000)
GiB-s  = 6,000   (free budget 360,000)
→ still free
```

Cold start after idle (model load ~30–90 s) **does** count toward allocation; still cheap at demo volume.

### 3.2 Cloud Build & Artifact Registry

| Parameter | Pilot impact |
|-----------|----------------|
| Build minutes | First deploy ~15–25 min; usually inside free/light quotas |
| Image storage | One fat image (models included) is fine; prune old revisions |

### 3.3 Supabase Free

| Parameter | Free (typical) | NosePrints impact |
|-----------|----------------|-------------------|
| DB size | ~**500 MB** | Embeddings are small; photos must **not** live in Postgres |
| Egress | ~**5 GB**/mo | API↔DB is tiny if photos are on R2 |
| Inactivity | Pause after ~**7 days** idle | Hit `/health` weekly or upgrade |
| Pro plan | ~**$25**/mo | Only if Free pauses / size / reliability fails |

### 3.4 Cloudflare R2 (durable photos)

| Parameter | Free tier (typical published) | Impact |
|-----------|-------------------------------|--------|
| Storage | ~**10 GB**/mo | Thousands of JPEG crops |
| Class A/B ops | Millions free | Register / identify / staff image loads |
| Egress to internet | Often **$0** on R2 | Better unit economics than GCP photo egress |

At 10–500 dogs, R2 is effectively **$0**.

### 3.5 Optional add-ons

| Parameter | When | Order of cost |
|-----------|------|----------------|
| SMTP (invite / reset / owner notify) | Multi-admin nationwide | Free tier → ~$0–10/mo |
| Domain `id.pawfriend.in` | Phase B | Usually existing domain; mapping free on Cloud Run |
| Uptime robot / GCP monitoring | Production | Often $0 on free checks |
| Supabase Pro | Growth / no-pause | ~$25/mo |
| Min instances = 1 | Low-latency always warm | **Avoid** — ~**$40–80+/mo** order of magnitude |

---

## 4. Monthly scenarios (expected bill)

Assumptions: `us-central1`, request-based, **min instances = 0**, **2 GiB / 1 CPU**, photos on R2 when durable.

| Scenario | Traffic shape | Expected monthly |
|----------|---------------|------------------|
| **A — Internship / closed demo** | 20–50 visitors, 50–200 identifies, few deploys | **~$0** (buffer **$0–5**) |
| **B — Staff pilot** | 10–50 dogs, 100–500 identifies, daily staff | **~$0–5** |
| **C — Busy NGO month** | ~5k identifies + light page loads | **~$0–25** (watch egress if not on R2) |
| **D — Always-on** | `min instances = 1` | **~$40–80+** — **not** our plan |
| **E — Nationwide early** | Staging + prod, SMTP, domain, still scale-to-zero | **~$0–40** typical if Free DB holds; **+$25** if Supabase Pro |

---

## 5. Unit economics (product cost per action)

These are **product units** for NGO / grant write-ups — not Cloud invoice line items.

### 5.1 Marginal infrastructure cost (at pilot volume, free tier)

| Product unit | What it consumes | Infra cost |
|--------------|------------------|------------|
| **1 dog registered** (owner + 3–5 noses + look) | ~5–15 API calls, DB rows, ~0.5–5 MB photos | **≪ $0.01** |
| **1 identify scan** | ~2–5 s @ 1 CPU / 2 GiB + vector search | **≪ $0.01** |
| **1 staff confirm / reject** | Auth + small DB + audit row | Negligible |
| **1 staff invite / password reset** | Token row + optional SMTP email | Negligible (+ SMTP if over free) |
| **1 owner erasure (DPDP)** | Cascade deletes + storage deletes | Negligible |
| **1 Cloud redeploy** | Build minutes + new image | Usually free quota |

### 5.2 Storage footprint (order of magnitude)

| Asset | Typical size | **100 dogs** (3 noses + 1 look) | **1,000 dogs** |
|-------|--------------|----------------------------------|----------------|
| Nose crop JPEG | 50–200 KB | ~15–60 MB | ~150–600 MB |
| Look JPEG | 200–800 KB | ~20–80 MB | ~200–800 MB |
| Embedding (512×float4) | ~2 KB + index | ≪ 1 MB | ~few MB |
| Match query images | Similar to noses | Ops retention policy | Use R2 + purge |

**Rule:** Photos in **R2**; only URLs + embeddings in Supabase → DB stays Free longer.

### 5.3 Worked “cost per useful outcome”

Assume Scenario B month ≈ **$5** worst-case buffer, **200** identifies, **20** successful staff-confirmed reunions (illustrative):

| Metric | Formula | Example |
|--------|---------|---------|
| Cost / identify | monthly_infra / identifies | $5 / 200 = **$0.025** (buffer case; often ~$0) |
| Cost / confirmed reunion | monthly_infra / confirms | $5 / 20 = **$0.25** |
| Cost / registered dog | monthly_infra / new dogs | $5 / 20 = **$0.25** |

Inside free tier (Scenario A), these approach **~$0**. Infrastructure is **not** the bottleneck — staff time and photo quality are.

### 5.4 What unit economics do **not** include

- Farhan / staff labor hours  
- Phone devices, field travel, shelter partnerships  
- Legal / DPDP counsel  
- Paid training data (e.g. Nexdata) if later approved  
- Accuracy risk (false matches) — mitigated by **human confirm**, not by more spend  

---

## 6. Cost controls (mandatory)

| Control | Action |
|---------|--------|
| Budget alert | GCP → Budget **$1 USD** → email |
| Scale | `min instances = 0`, `max instances` ≤ 3 |
| Region | Prefer **`us-central1`** (or other free-tier Tier-1) |
| Memory | Keep **2 GiB** |
| Photos | **R2** so GCP egress stays low |
| Supabase | Weekly traffic so Free project doesn’t pause mid-demo |
| Secrets | Strong `JWT_SECRET_KEY`; never commit `.env` |
| Always-on / GPU / HF PRO | Out of scope unless explicitly approved |

---

## 7. Phase outlook

| Phase | Hosting | Expected monthly infra |
|-------|---------|-------------------------|
| Local tunnel (now) | Laptop | $0 cloud |
| Phase A — Cloud demo | Cloud Run + Supabase Free + R2 | **$0–5** |
| Phase B — `id.pawfriend.in` | Same + DNS | **$0–10** |
| Nationwide early | Same + optional SMTP/staging | **$0–40** (+$25 if Pro DB) |
| Heavy production | Revisit always-on / Pro / multi-region | Decision later (**$50–150+** possible) |

---

## 8. Rejected “cheap” hosts

| Option | Why not |
|--------|---------|
| Free 512 MB PaaS | ONNX **OOM** |
| Static-only (Vercel/Netlify alone) | Cannot run FastAPI + models |
| HF Docker Space | Works but ~$9/mo PRO — unnecessary if Cloud Run free holds |

---

## 9. Finance sign-off blurb (copy/paste)

> NosePrints production target is one **Cloud Run** service (1 vCPU, **2 GiB**, **scale-to-zero**) plus **Supabase Free** Postgres/pgvector and **Cloudflare R2** for photos. At internship and closed-pilot traffic we expect **~$0/month** infrastructure, with a **$1 GCP budget alert** and **$5 contingency**. Unit cost per registration or identify is negligible under free allowances. We do **not** enable always-on min instances or GPU for the default plan. Revisit costs before nationwide always-warm or Supabase Pro.

---

## 10. Re-check before a paid multi-month pilot

- [Cloud Run pricing](https://cloud.google.com/run/pricing)  
- [Supabase pricing](https://supabase.com/pricing)  
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)  

Deploy how-to: [`FINAL_DEPLOYMENT_PLAN.md`](./FINAL_DEPLOYMENT_PLAN.md) · Checklist: [`CLOUD_HOSTING_CHECKLIST.md`](./CLOUD_HOSTING_CHECKLIST.md)

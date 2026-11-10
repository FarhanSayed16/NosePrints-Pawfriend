# Exact next index + ChatGPT plan response

**Date:** 10 November 2026  
**Audience:** Farhan + ChatGPT follow-up  
**Status of system:** Demo-ready with real models + strict gates; **not** “finished forever / no issues”

---

## A. Is the system completely ready? Any issues left?

### Ready for a **gated senior / internship demo** (with caveats)

| Area | Ready? | Notes |
|------|--------|-------|
| App + API + staff confirm | Yes | Real ONNX, DB connected when Supabase up |
| Detector + embedding shipped | Yes | Detector promoted; embedding = baseline |
| Strict mode | Yes | `MATCH_STRICT_DEMO=true`, strict ≥ **0.60** |
| Junk gates in code | Yes | Local synthetic tests pass (50/50 pytest) |
| Gallery cleaned | Yes | Only **Max** + **Ness** with prints |
| Phone HTTPS field acceptance | **Not done** | Still required on real phone |
| Cloud hosting | **Not done** | Needs gcloud + Docker |
| Field accuracy “much better” | **No** | Still ~AUC 0.80 lab; needs pilot dogs |
| Zero remaining issues | **No** | Domain shift, open-set, multi-print unused potential |

**Honest verdict:** Production models are **frozen and usable**. Free-data training pass is **complete**. Remaining work is **pilot data + controlled experiments**, not another CVPR-only retrain.

---

## B. Agreement with ChatGPT’s recommendations

**Agree with the central advice.** Do **not** repeat CVPR-only embedding continue-train. Freeze baselines. Collect phone data. Run Experiments A → C before D/E.

| ChatGPT item | Our decision |
|--------------|--------------|
| Freeze baselines | **Adopt** — already frozen |
| No more same-CVPR epochs | **Adopt** — already failed once |
| PawFriend phone collection first | **Adopt — #1 human blocker** |
| Experiment A multi-print aggregation | **Adopt — first code experiment (no new net)** |
| Experiment B phone detector | **Adopt after phone-test labels** |
| Experiment C open-set | **Adopt — can start offline on CVPR + expand with pilot** |
| Experiment D embedding FT | **Later** — after ≥ identities + session splits |
| Experiment E junk CNN | **Conditional** — only after labeled phone failures |
| Buy Nexdata now | **Defer** — sample/quote only |
| ResNet101 / transformer now | **Reject for now** |

---

## C. Exact indexing — what to do **right now** (ordered)

Do these in order. Do **not** skip to fine-tuning.

### Index 0 — Freeze (done)
- [x] Production ONNX + `.prev` rollbacks  
- [x] Baseline metrics documented  
- [x] Strict demo ON  
- [x] Gallery purged  

### Index 1 — **YOU (Farhan) this week** — highest priority
1. Hard-refresh phone → `https://noseprints.farhanbuilds.in`  
2. Run acceptance: keyboard reject / real nose accept ×3 / look soft-warn  
3. Start **consented** captures: **10–20 dogs**, 3–5 noses each, ideally **2 sessions**  
4. Store under `ml/data/identity/pawfriend/` (+ `detector/phone-test/` failures)  
5. Keep consent offline / separate from ML folders  

**Without Index 1, Index 3–5 cannot meaningfully improve accuracy.**

### Index 2 — **Cursor code audit / Experiment A** (can start immediately, no new dogs)
Inspect + offline compare multi-print strategies (see §D findings):
- Current behavior = **max similarity across all stored prints** (print-level pgvector search, then collapse per dog)
- Prototype/compare: best-single / max-of-prints (current) / mean template / quality-weighted  
- Deliver: short report + whether a code change is justified  
- **Do not** change production ONNX  

### Index 3 — Dataset audit (repo already partially done)
- Refresh `DATASET_INVENTORY.md` / licences  
- Confirm no duplicate CVPR download  
- Nexdata: **request sample only**, no purchase yet  
- Pose datasets (StanfordExtra etc.): optional detector research only  

### Index 4 — Open-set calibration (Experiment C)
- Scripted known/unknown eval on CVPR holdout (already have `eval_open_set.py`)  
- Re-run on **production** embedding (not continued_v1 candidate)  
- Report FAR/FRR @ 0.56 and 0.60  
- Recalibrate only on a **held-out calibration** split  

### Index 5 — After 10–20 phone dogs
- Label detector miss/wrong-box cases → phone-test v1  
- Decide YOLO FT yes/no from **recall/false-detect**, not hope  
- Only then plan embedding fine-tune (conservative / freeze early layers)  

### Index 6 — Later / optional
- Nose-vs-junk MobileNet if heuristics fail on labeled junk  
- Cloud Run hosting  
- Nexdata purchase if sample+rights pass  
- Stronger backbone  

---

## D. Repo answers ChatGPT asked Cursor for

### How is the gallery stored?
Each accepted nose print is a row in `nose_prints` with a **512-d pgvector embedding** (one embedding **per print**, not one per dog).

### Does matching use multiple enrollment prints?
**Yes — print-level search, then best score per dog.**

From `backend/app/services/matcher.py`:
- SQL orders by `np.embedding <=> query` (cosine distance) over **all nose_prints**
- Results are collapsed by `dog_id`, keeping the **first (highest similarity) print** per dog
- So identification already uses **Method 2 (max over prints)** in practice  
- It does **not** currently average embeddings into a single dog template (Method 3/4)

### Production embedding baseline checkpoint?
- ONNX: `backend/models/embedding_model.onnx`  
- Torch baseline freeze: `ml/checkpoints/embedding/best_model.baseline.pt`  
- Metrics: `ml/eval_results/embedding/metrics.txt` (AUC 0.8027, Rank-1 0.7856)

### Thresholds reproducible?
Yes from that metrics file (T_high≈0.559 → ops 0.56; T_low≈0.505 → 0.51). Strict 0.60 is a **demo safety** choice, not the lab Youden point.

### GPU
RTX 4050 Laptop ~6 GB (from inventory).

---

## E. WHAT I NEED FROM FARHAN

| # | Need | Blocking? |
|---|------|-----------|
| 1 | Phone HTTPS acceptance checklist results | Demo confidence |
| 2 | Consent + 10–20 real dog nose captures (multi-session if possible) | **Accuracy work** |
| 3 | Confirm OK to run Experiment A offline (no prod ONNX overwrite) | Can proceed |
| 4 | Nexdata: sample request yes/no | Optional |
| 5 | Cloud Run: install gcloud + start Docker when hosting wanted | Deploy only |
| 6 | Keep staff confirm mandatory (policy lock) | Assumed yes |

---

## F. One-line next action

**Farhan:** collect phone pilot dogs + run HTTPS acceptance.  
**Cursor (when you say go):** Experiment A report (multi-print aggregation offline) + production open-set metrics @ 0.56/0.60 — **no training, no ONNX promote**.

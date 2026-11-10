# Experiment C — Open-set evaluation (production embedding)

**Date:** 10 November 2026  
**Status:** Offline only — **thresholds / `.env` unchanged**  
**Raw JSON:** `ml/eval_results/experiment_c_openset/results.json`  
**ROC plot:** `ml/eval_results/experiment_c_openset/roc_known.png`  
**Script:** `ml/training/experiment_c_openset_prod.py`

---

## 1. Evaluation protocol

| Split | Definition |
|-------|------------|
| Known IDs | 85% of dog IDs (seed=0) present in gallery |
| Unknown IDs | 15% of dog IDs **absent** from gallery |
| Gallery | Train images of **known** IDs only |
| Genuine probes | Val images of known IDs |
| Unknown probes | Val images of unknown IDs |

Matcher = **production max-over-prints** (Method B).

This is a **laboratory CVPR** open-set simulation — **not** real-phone field performance.

---

## 2. Production model verification

| Check | Result |
|-------|--------|
| ONNX | `backend/models/embedding_model.onnx` |
| Torch | `ml/checkpoints/embedding/best_model.baseline.pt` |
| Parity mean cosine | **0.999999** (32 images) |
| Used continued_v1? | **No** |
| Env thresholds modified? | **No** |

Embeddings reused from Experiment A cache (same baseline model).

---

## 3. Counts

| Item | Count |
|------|------:|
| Known dog IDs | 5,100 |
| Unknown dog IDs | 900 |
| Gallery images | 11,867 |
| Known probes | 5,134 |
| Unknown probes | 910 |

---

## 4. Closed-set (known dogs) identification

| Metric | Value |
|--------|------:|
| AUC (genuine vs impostor) | 0.8053 |
| Rank-1 | 0.7877 |
| Rank-5 | 0.8319 |

---

## 5. Operating points (unchanged thresholds)

Verification-style on known probes + unknown FPIR:

| Threshold | Meaning | TAR (known) | FRR | FAR (known impostor) | Unknown FPIR (best gallery ≥ thr) |
|----------:|---------|------------:|----:|---------------------:|----------------------------------:|
| 0.51 | Possible floor (ref) | 0.789 | 0.211 | 0.236 | 0.230 |
| **0.56** | Likely | 0.768 | 0.232 | 0.068 | **0.070** |
| **0.60** | Strict demo | 0.745 | 0.255 | 0.022 | **0.025** |

Mean best similarity: known genuine ≈ **0.76**; unknown / known impostor ≈ **0.48**.

---

## 6. Open-set interpretation

- At **0.56**, ~**7%** of unknown probes would score high enough to look like “some enrolled dog” in a raw verification sense.  
- At **0.60** (strict), that falls to ~**2.5%**.  
- Strict mode therefore **materially reduces** lab false identification pressure, at ~2–3 pp TAR cost.  

Staff confirmation remains mandatory regardless.

---

## 7. Limitations / confidence

| Limitation | Impact |
|------------|--------|
| CVPR lab images ≠ Indian phone captures | **High** — do not treat FAR as field FAR |
| Train/val same dog IDs originally; we held out IDs for unknown | Protocol OK for lab open-set |
| Max-print matcher (not mean) | Matches production |
| Gallery size effect | Thresholds may shift as registry grows beyond 2→50→100 dogs |
| No session metadata on CVPR mirror | “Different session” is approximated by val vs train files |

**Confidence:** useful for **relative** threshold comparison (0.56 vs 0.60). **Low** confidence as absolute production FAR claim.

---

## 8. Threshold recommendation (do not auto-apply)

| Setting | Recommendation |
|---------|----------------|
| Keep `MATCH_STRICT_DEMO=true` / **0.60** for public demos | **Yes** — lower unknown FPIR in lab |
| Keep documented Likely **0.56** when strict off | **Yes** until phone calibration set exists |
| Change `.env` now | **No** |
| Recalibrate after pilot | **Yes** — dedicated calibration split, never on final test |

---

## 9. Is strict 0.60 suitable for continued testing?

**Yes for continued demo/testing.** It is a safer operating point on this lab open-set. Re-validate on real phone known/unknown scans before advertising any FAR number.

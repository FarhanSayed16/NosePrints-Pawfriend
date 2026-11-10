# Experiment A — Multi-print aggregation results

**Date:** 10 November 2026  
**Status:** Offline only — **production matcher unchanged**  
**Raw JSON:** `ml/eval_results/experiment_a_multiprint/results.json`  
**Script:** `ml/training/experiment_a_multiprint.py`

---

## 1. How current production matching works

From `backend/app/services/matcher.py`:

1. Each enrolled nose print stores its own **512-d** pgvector embedding.  
2. Query embedding is compared to **all** `nose_prints`.  
3. Rows are ordered by cosine similarity.  
4. Results are collapsed by `dog_id`, keeping the **first = highest** score per dog.  

→ Production = **Method B (maximum similarity over prints)**.

**Important discovery:** The documented lab baseline in `evaluate.py` / `metrics.txt` (AUC **0.8027**, Rank-1 **0.7856**) was computed with **mean centroids per dog** (Method C), **not** Method B. So lab docs and runtime matching were slightly different strategies.

---

## 2. Experimental methods

| ID | Method | Gallery representation |
|----|--------|------------------------|
| A | Best-quality single print | One print per dog with max Laplacian sharpness (enrollment only) |
| B | Max similarity | All prints kept; score = max cosine (production) |
| C | Mean template | Mean of L2-normalized print embeddings, re-normalized |
| D | Quality-weighted mean | Sharpness-weighted mean, re-normalized |

Quality weights = Laplacian variance of enrollment JPEGs only (no probe leakage). Reliable sharpness existed for all dogs in this set (`zero_quality_dogs=0`).

---

## 3. Dataset & model

| Item | Value |
|------|------|
| Data | `ml/data/identity` CVPR mirror — train gallery, val probes |
| Gallery images | 13,956 |
| Probe images | 6,044 |
| Dog IDs | 6,000 (same IDs in train/val — existing gallery-probe protocol) |
| Model | `best_model.baseline.pt` after ONNX parity |
| ONNX path | `backend/models/embedding_model.onnx` |
| Parity | mean cosine Torch↔ONNX **0.999999** on 32 images → **pass** |

Commands:

```powershell
cd D:\NosePrints-Pawfriend\ml
.\.venv\Scripts\python.exe training\experiment_a_multiprint.py `
  --identity_root data\identity `
  --out_dir eval_results\experiment_a_multiprint
```

---

## 4. Results comparison

| Method | AUC | Rank-1 | Rank-5 | Gallery vectors | ~ms/probe | FAR@0.56 | TAR@0.56 | FAR@0.60 | TAR@0.60 |
|--------|----:|-------:|-------:|----------------:|----------:|---------:|---------:|---------:|---------:|
| **A best quality** | 0.7945 | 0.7788 | 0.8221 | 6,000 | 0.28 | 0.045 | 0.745 | 0.018 | 0.720 |
| **B max (production)** | 0.8020 | 0.7842 | 0.8283 | 13,956 | 31.7 | 0.079 | 0.767 | 0.027 | 0.745 |
| **C mean template** | **0.8027** | **0.7856** | **0.8291** | 6,000 | 0.28 | **0.048** | 0.759 | **0.018** | 0.735 |
| **D quality-weighted** | 0.7998 | 0.7823 | 0.8263 | 6,000 | 0.28 | 0.048 | 0.755 | 0.018 | 0.731 |

FAR/TAR here = verification-style: genuine score vs best impostor-other-dog score (same protocol family as existing eval).

---

## 5. Advantages / disadvantages

| Method | Pros | Cons |
|--------|------|------|
| A | Smallest storage; simple | Worst AUC/Rank-1 |
| B | Matches live API; uses all prints | More vectors; slightly higher FAR@0.56 than C; slower brute-force |
| C | Best AUC/Rank-1; matches published baseline; 2.3× fewer vectors | Needs template rebuild on new enrollments |
| D | Uses quality signal | Did not beat C on this set |

---

## 6. Does anything beat current production (B)?

On **this CVPR lab protocol**: **yes — Method C (mean) slightly beats B** on AUC/Rank-1 and has lower FAR at 0.56/0.60.

Magnitude is **small** (~0.0008 AUC, ~0.13 pp Rank-1). Not enough alone to force an emergency production change without phone validation.

---

## 7. Recommendation

| Decision | Detail |
|----------|--------|
| **Keep production Method B for now** | Live system already uses it; staff confirm remains |
| **Do not implement D** | No gain over C |
| **Do not implement A** | Clear regression |
| **Optional follow-up (needs Farhan approval)** | Offline A/B on **phone pilot** data; if C still wins, implement dog-level mean templates behind a flag + rebuild-on-enroll |
| **Doc fix** | Note that historical `metrics.txt` reflects **mean**, not max |

**No production matcher code changes in this pass.**

# Next ML decision report (Index 2 + 3 + 4)

**Date:** 10 November 2026  
**Authority:** Farhan approval to run offline experiments only  
**Production ONNX / `.env` / DB:** **unchanged**

Plain-English explainer of the ChatGPT brief: [`WHAT_CHATGPT_APPROVED.md`](./WHAT_CHATGPT_APPROVED.md)

---

## 1. What was investigated

- Multi-print gallery aggregation (A/B/C/D) vs live `matcher.py`  
- Open-set unknown-dog scores at 0.51 / 0.56 / 0.60 using **production** embedding  
- Dataset inventory + licensing refresh  
- ONNX ↔ Torch baseline numerical parity  

## 2. What was actually executed

| Task | Executed? | Output |
|------|:---------:|--------|
| Experiment A | Yes | `EXPERIMENT_A_MULTIPRINT_RESULTS.md` + `ml/eval_results/experiment_a_multiprint/` |
| Experiment C | Yes | `EXPERIMENT_C_OPEN_SET_RESULTS.md` + `ml/eval_results/experiment_c_openset/` |
| Dataset inventory | Yes | Updated `DATASET_INVENTORY.md` (+ existing `DATA_LICENSES.md`) |
| Model training | **No** | Forbidden |
| Production promote / threshold edit | **No** | Forbidden |

## 3. Exact commands used

```powershell
cd D:\NosePrints-Pawfriend\ml

.\.venv\Scripts\python.exe training\experiment_a_multiprint.py `
  --identity_root data\identity `
  --out_dir eval_results\experiment_a_multiprint

.\.venv\Scripts\python.exe training\experiment_c_openset_prod.py `
  --identity_root data\identity `
  --out_dir eval_results\experiment_c_openset
```

Parity: Torch `best_model.baseline.pt` vs ONNX `embedding_model.onnx` → mean cosine **0.999999**.

## 4. Datasets / splits

| Use | Data |
|-----|------|
| Gallery | `ml/data/identity/train` (CVPR mirror) |
| Probes | `ml/data/identity/val` |
| Open-set holdout | 15% of IDs unknown (seed 0); gallery = remaining known train images |

## 5. Experiment A results (summary)

| Method | AUC | Rank-1 | FAR@0.56 |
|--------|----:|-------:|---------:|
| A best quality | 0.7945 | 0.7788 | 0.045 |
| **B max = production** | 0.8020 | 0.7842 | 0.079 |
| **C mean** | **0.8027** | **0.7856** | **0.048** |
| D quality-weighted | 0.7998 | 0.7823 | 0.048 |

**Decision:** Keep production **max** for now. Mean is slightly better on lab + cheaper storage; revisit after phone pilot. Do **not** ship D or A.

## 6. Experiment C results (summary)

| Threshold | Known TAR | Known FAR | Unknown FPIR |
|----------:|----------:|----------:|-------------:|
| 0.56 | 0.768 | 0.068 | **0.070** |
| 0.60 strict | 0.745 | 0.022 | **0.025** |

**Decision:** Keep strict demo **0.60** for public testing. Do **not** change `.env`. Recalibrate only with phone calibration data later.

## 7. Dataset inventory conclusions

- CVPR identity + Roboflow/merged detector **already on disk** — do not re-download duplicates.  
- **PawFriend phone set missing** — primary gap.  
- Nexdata = sample/quote only.  
- PetFace = blocked for commercial product.  
- Pose/face datasets ≠ nose-print biometrics.

## 8–9. Decision table

| Enhancement | Evidence | Recommendation | Required input |
|-------------|----------|----------------|----------------|
| Multi-print aggregation | Exp A: C ≥ B slightly on lab | **Keep B now**; optional C later after phone A/B | Phone pilot for confirmation |
| Open-set threshold | Exp C: 0.60 cuts unknown FPIR ~7%→2.5% lab | **Keep strict 0.60**; no auto change | Real phone known/unknown scans |
| YOLO fine-tuning | No new phone-test labels | **Defer** | Real phone images + boxes |
| ArcFace fine-tuning | CVPR continue-train already failed | **Defer** | ≥10–20 then ≥50 consented IDs |
| Nose-vs-junk classifier | No labeled field failure set | **Conditional / defer** | Labeled phone junk failures |
| Nexdata | Licence/paid | **Defer purchase** | Farhan approval + sample |

## 10. Supported vs postponed

**Supported by evidence now**
- Freeze production models (already done)  
- Keep strict demo for safety  
- Collect PawFriend phone data as #1 accuracy lever  
- Document that lab `metrics.txt` used **mean**, API uses **max**

**Rejected / postponed**
- Another CVPR-only training run  
- Immediate matcher rewrite to mean templates  
- Buying Nexdata / backbone upgrade / junk CNN without field failures  

---

## WHAT I NEED FROM FARHAN NEXT

1. **Phone HTTPS acceptance** on `https://noseprints.farhanbuilds.in` (keyboard / real nose / look) — short pass/fail notes.  
2. **Consented pilot captures:** start **10–20 dogs**, 3–5 nose photos each (ideally 2 sessions).  
3. Confirm whether you want a **follow-up approval** later to implement mean templates (Method C) behind a feature flag after phone comparison.  
4. Nexdata: say if you want Cursor to draft a **sample request email** (still no purchase).  
5. Nothing else required for GPU (RTX 4050 already used) or repo access.

**Do not** send another CVPR retrain request until pilot data exists.

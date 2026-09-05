# Accuracy appendix — internship write-up (honest numbers)

Do **not** quote 98–99% as NosePrints production accuracy. Those figures come from curated lab papers (e.g. Bae et al. DNNet), not this deployment.

## What we trained

| Model | Data | Result |
|---|---|---|
| YOLOv8n nose detector | Roboflow Dog_nose YOLOv8 | val mAP50 **0.54**, test mAP50 **0.68**; labeled close-up recall improved to **~70%** with pad + lower-conf retry |
| ResNet50 + ArcFace embedding | CVPR 2022 Pet Biometric Challenge mirror (6,000 dogs) | gallery-probe **rank-1 78.6%**, **AUC 0.80** |

Source file: `ml/eval_results/embedding/metrics.txt`

## Thresholds in production

| Band | Cosine | Meaning |
|---|---|---|
| Likely | ≥ **0.56** (FAR ~5% on this val set) | Strong candidate; staff still confirms |
| Possible | **0.51–0.56** (FAR ~20%) | Extra caution |
| No match | < 0.51 | Offer found-dog intake; **API returns `candidates: []`** |

Lost dogs get a **+0.03 ranking boost only**. The score shown to users is raw cosine.

### Strict demo mode (G2)

For public links / senior demos, set:

```env
MATCH_STRICT_DEMO=true
MATCH_THRESHOLD_STRICT=0.60
```

Effects:

- The **possible** band is off — only scores ≥ `MATCH_THRESHOLD_STRICT` are `match_found`.
- Staff queue shows **likely / matched** only (no weak “possible” spam).
- Below threshold: `match_found=false`, **empty candidates**, Identify UI shows **No match**.

Optional without full strict mode: `MATCH_QUEUE_LIKELY_ONLY=true` to keep possible matches in the API but hide them from the staff queue.

## CVPR bar we did not hit

Challenge winners reported **86.67% AUC** on a blind test. We are **below** that. Fine-tune later on ≥50 real PawFriend dogs.

## Product implication

AI proposes candidates. **PawFriend staff confirm** before any owner contact is revealed. That is the reunion product, not a fallback.

## Garbage / non-nose inputs (G0–G1)

Cosine similarity on junk (keyboards, walls) is **meaningless**. Register and identify must **reject** non-nose photos in `prepare_nose_scan` (detector + heuristics) before any embedding is stored or searched. Do not treat a high score between two junk images as a successful ID. See [`GARBAGE_PHOTO_FALSE_MATCH_PLAN.md`](./GARBAGE_PHOTO_FALSE_MATCH_PLAN.md).

### Look photos (G3 — soft only)

Full-body / face photos are **not** biometric. Keyboard/blank-looking uploads soft-warn (`POST /dogs/look-check`; profile-photo / identify appearance without `force` / `force_appearance` → 422 `soft_warn`). User may confirm **Use anyway**. Staff can purge junk dogs under Staff → Registry cleanup. Found-intake embeds only after `prepare_nose_scan`.

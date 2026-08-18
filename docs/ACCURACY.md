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
| No match | < 0.51 | Offer found-dog intake |

Lost dogs get a **+0.03 ranking boost only**. The score shown to users is raw cosine.

## CVPR bar we did not hit

Challenge winners reported **86.67% AUC** on a blind test. We are **below** that. Fine-tune later on ≥50 real PawFriend dogs.

## Product implication

AI proposes candidates. **PawFriend staff confirm** before any owner contact is revealed. That is the reunion product, not a fallback.

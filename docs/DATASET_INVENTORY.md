# Dataset & Model Inventory (refreshed 10 Nov 2026)

**Track:** Index 3 audit (non-destructive)  
**GPU:** NVIDIA GeForce RTX 4050 Laptop GPU (~6 GB)  
**Rule:** Face / pose / landmark datasets ≠ nose-print biometric identity data.

---

## Model artifacts (production frozen)

| File | Role |
|------|------|
| `backend/models/nose_detector.onnx` | Production detector (merged_v1, mAP50 0.54057) |
| `backend/models/nose_detector.prev.onnx` | Rollback |
| `backend/models/embedding_model.onnx` | Production embedding (baseline) |
| `backend/models/embedding_model.prev.onnx` | Rollback copy |
| `backend/models/embedding_model.candidate.onnx` | Continued-train candidate — **not production** |
| `ml/checkpoints/embedding/best_model.baseline.pt` | Torch baseline for offline eval |
| `ml/eval_results/embedding/metrics.txt` | AUC 0.8027 · Rank-1 0.7856 |

ONNX↔Torch parity (Experiment A, 32 images): mean cosine **0.999999** → Torch baseline OK as production-equivalent offline substitute.

---

## On disk today

### Identity / ArcFace (Group A)

| Source | Path | Dogs | Images | Nose-print ID labels | Already have? | Commercial notes |
|--------|------|-----:|-------:|:--------------------:|:-------------:|------------------|
| CVPR 2022 Pet Biometric mirror | `ml/data/identity/{train,val}` | 6000 | 13956 + 6044 | Yes | **Yes** | Reuse on-disk; see `DATA_LICENSES.md` |
| PawFriend pilot | `ml/data/identity/pawfriend/` | 0 | 0 | — | **No** | Highest priority to collect |
| Continued-train outputs | `ml/checkpoints/embedding_continued_v1/` | — | — | — | Yes (failed promote) | Do not use as baseline |

### Detector / YOLO (Group B)

| Source | Path | Images | Labels | Nose leather boxes | Already have? |
|--------|------|-------:|-------:|:------------------:|:-------------:|
| Roboflow Dog_nose v4 | `ml/data/detector/dog_nose_yolov8/` | 4693 | 4693 | Yes | **Yes** (CC BY 4.0) |
| Synthetic negatives | `ml/data/detector/negatives/` | 240 | n/a | Hard-neg style | **Yes** |
| Merged v1 | `ml/data/detector/merged_v1/` | 6133 | YOLO | Yes + negs/augs | **Yes** |
| Phone-test fixtures | `ml/data/detector/phone-test/` | synthetic junk set | — | For gate smoke | Partial (not real phones) |

---

## External candidates (audit only — do not auto-download paid/restricted)

| Dataset | Nose-print biometric? | Identity labels? | Boxes / keypoints / seg | YOLO useful? | ArcFace useful? | Licence / status | Action |
|---------|:---------------------:|:----------------:|-------------------------|:------------:|:---------------:|------------------|--------|
| **CVPR 2022 / Kaggle zekunn** | Yes | Yes | Crops/challenge format | Indirect | **Yes** | Challenge/Kaggle terms | **Keep existing** — do not duplicate |
| **Nexdata Dog Nose Print** | Yes (claimed) | Yes (~1073 dogs) | Seg masks claimed | Possible | Possible | **Paid commercial** | Sample + quote only — **no purchase** |
| **StanfordExtra** | No (dog instances) | No biometric IDs | Keypoints + seg | Weak (nose keypoint ≠ leather box) | No | Mixed image rights | Defer research |
| **Animal-Pose** | No | No | 20 keypoints incl. nose | Weak | No | Check sources | Defer |
| **Ultralytics Dog-Pose** | No | No | Nose keypoint | Weak | No | Ultralytics dataset terms | Defer |
| **Zenodo Pet Face** | No (face) | No nose-print IDs | Face box + eye/nose landmarks | Weak | No | Licence field unclear | Defer / seek permission |
| **Oxford-IIIT Pet** | No | Breed-level | Head boxes / seg | Weak | No | CC BY-SA style attribution | Defer |
| **PetFace** | No (face IDs) | Face IDs | Face | No for nose ID | No | **Non-commercial** | **Blocked** for product |

**Distinction enforced:** dog face photo ≠ nose landmark ≠ nose-leather biometric print.

---

## Duplication risk

Re-downloading Kaggle CVPR mirrors into `ml/data/identity` would **duplicate** the prepared 6000-ID tree. Do not.

---

## Recommended acquisition order

1. **PawFriend consented phone captures** (not a download)  
2. Nexdata **sample** (if Farhan requests)  
3. Optional pose sets only if phone-test proves YOLO leather-box failures need keypoint pretraining  

See `DATA_LICENSES.md` for approval status.

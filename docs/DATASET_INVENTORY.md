# Dataset & Model Inventory (Phase 0 freeze)

**Frozen:** 9 November 2026  
**Track:** ML Accuracy Enhancement — Free Public Track  
**GPU:** NVIDIA GeForce RTX 4050 Laptop GPU, 6141 MiB  
**Torch:** 2.6.0+cu124, CUDA available

---

## Model artifacts (SHA256)

| File | Bytes | SHA256 |
|------|------:|--------|
| `backend/models/nose_detector.onnx` | 12,265,315 | `D0DD3FCE839D1E0223CF83D71ADD4EF3DB24B7B287D108F4880A566FA18AF0D2` |
| `backend/models/embedding_model.onnx` | 104,475,221 | `F17888A35CBB7E39DE40320E23E24440286E7E52D07E4CB38002C32C1FFA2F9D` |
| `ml/checkpoints/embedding/best_model.pt` | 338,665,730 | `1ECAA2368DE4DCFFD55F14C7EC94531A64323FD0FA1245012DDE17A659BB0886` |

Rollback copies created in later phases as `*.prev.onnx` / `best_model.baseline.pt`.

---

## Identity dataset (embedding / ArcFace)

| Split | Dog folders | Images |
|-------|------------:|-------:|
| `ml/data/identity/train` | 6000 | 13956 |
| `ml/data/identity/val` | 6000 | 6044 |

Source: CVPR 2022 Pet Biometric Challenge mirror (see DATA_LICENSES.md).

---

## Detector dataset (YOLOv8 nose boxes)

Base: `ml/data/detector/dog_nose_yolov8/` (Roboflow Dog_nose v4)

| Split | Images | Labels |
|-------|-------:|-------:|
| train | 4313 | 4313 |
| valid | 340 | 340 |
| test | 40 | 40 |
| **Total** | **4693** | **4693** |

Class: `dog-nose` (nc=1). Export resized 640×640 stretch. Licence: CC BY 4.0 (Roboflow Universe).

---

## Baseline embedding metrics (frozen copy)

File: `ml/eval_results/embedding/metrics_baseline_2026-08.txt` (copy of `metrics.txt`)

| Metric | Value |
|--------|------:|
| AUC | 0.802713 |
| Rank-1 | 0.785572 |
| T_high (FAR~5%) | 0.558650 |
| T_low (FAR~20%) | 0.505441 |
| Protocol | gallery-probe |
| Probes / Gallery images | 6044 / 13956 |

Prior detector notes (docs): val mAP50 ~0.54, test mAP50 ~0.68.

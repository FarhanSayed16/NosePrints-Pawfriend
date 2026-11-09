# Data licence register

**Updated:** 9 November 2026  
**Rule:** Do not train product models on `blocked` or unresolved `pending` sources.

| Source | Path / URL | Licence | Status | Notes |
|--------|------------|---------|--------|-------|
| Roboflow Dog_nose v4 | `ml/data/detector/dog_nose_yolov8/` · [Universe](https://universe.roboflow.com/dog-ddgsn/dog_nose-6yo9t/dataset/4) | CC BY 4.0 | **approved** | 4693 images, YOLOv8 export |
| CVPR 2022 Pet Biometric mirror | `ml/data/identity/` · Kaggle zekunn/pet-biometric-challenge | See Kaggle card / challenge terms | **approved** (reuse on-disk) | Already prepared train/val folders; do not re-download blindly |
| Synthetic hard negatives | `ml/data/detector/negatives/` | Generated in-repo | **approved** | 240 images: keyboard/fabric/blank/ui/fur |
| Merged detector v1 | `ml/data/detector/merged_v1/` | CC BY 4.0 base + synthetic | **approved** | 6133 images (Roboflow + negs + offline augs). No Roboflow API — extra Universe zips deferred |
| Roboflow backup nose sets | `ml/data/detector/raw/*` | Per-project (expect CC BY) | **deferred** | No API key/kaggle.json on this machine |
| Nexdata Dog Nose Print | Commercial | Paid | **blocked** (this track) | Needs purchase + commercial rights |
| PetFace (ECCV 2024) | Application required | Non-commercial research | **blocked** (product) | Not for product ONNX |
| StanfordExtra / Animal-Pose / Zenodo pet-face | External | Mixed / unclear | **deferred** | Keypoints ≠ leather boxes; not in this track |

## Checksums of downloads

Filled during Phase 1 as zips arrive:

| File | SHA256 | Date |
|------|--------|------|
| *(none yet)* | | |

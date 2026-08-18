# Phase 2 dataset — identity (which dog is this?)

This is **not** the YOLO detector set.  
You need **several photos per dog**, with a dog ID. Boxes are optional here.

Do **not** start embedding training until this folder exists:

```
ml/data/identity/train/<dog_id>/*.jpg
ml/data/identity/val/<dog_id>/*.jpg
```

---

## What to download (pick this)

**Best public set:** CVPR 2022 Pet Biometric Challenge mirror on Kaggle (~515 MB, ~20k nose photos).

- Page: https://www.kaggle.com/datasets/zekunn/pet-biometric-challenge
- After unzip you should see `pet_biometric_challenge_2022/train/images/` plus a CSV of dog IDs.

**Backup:** Google Drive dump from a CVPR 2022 3rd-place write-up  
https://drive.google.com/drive/folders/1_7pdSRTvD_XdTu8z0MxrM9PDoEuX-tjf

**Plan B if both fail:** 30–80 real dogs × 5–10 close nose photos (NGO / friends). Accuracy will be lower. That is still a valid internship result if we publish ROC honestly.

---

## Steps (Kaggle)

1. Create a free Kaggle account.
2. Open https://www.kaggle.com/settings, scroll to **API**, create a token. Save `kaggle.json` as `%USERPROFILE%\.kaggle\kaggle.json`.
3. In PowerShell from the repo:

```powershell
cd d:\NosePrints-Pawfriend\ml
.\.venv\Scripts\pip.exe install kaggle
mkdir data\identity\raw -Force
.\.venv\Scripts\kaggle.exe datasets download -d zekunn/pet-biometric-challenge -p data\identity\raw --unzip
.\.venv\Scripts\python.exe training\prepare_identity_dataset.py --src data\identity\raw\pet_biometric_challenge_2022
```

If the unzipped folder name differs, pass that path to `--src`.

4. Reply in chat: **“identity dataset is in ml/data/identity”**

Do not commit `ml/data/`. It is gitignored.

---

## After the folders exist

Training (GPU, Python 3.12 venv — not 3.14):

```powershell
cd d:\NosePrints-Pawfriend\ml
.\.venv\Scripts\python.exe training\train_embedding.py --data_dir data\identity --epochs 50 --batch_size 16 --num_workers 0 --checkpoint_dir checkpoints\embedding
```

Then ROC + ONNX export. Do not present placeholder matching as real ID until `backend/models/embedding_model.onnx` exists and `DEBUG=false` refuses placeholders.

# Phase 1 dataset — download guide

This is **only** for the nose **detector** (YOLOv8).  
It is **not** the identity dataset for matching dogs (that is Phase 2).

You need photos with a **box drawn around the nose**. Classification folders of “dog nose” pictures without boxes will not work.

---

## What to download (pick this one)

**Best fit for this project:** Roboflow `Dog_nose` (object detection, class `dog-nose`, ~631 images).

- Page: https://universe.roboflow.com/dog-ddgsn/dog_nose-6yo9t
- Why: it is already labeled as **dog-nose boxes**, exportable as **YOLOv8**, large enough to fine-tune YOLOv8-nano, free.

**Backup if that page is private / empty:**

1. https://universe.roboflow.com/pireco/dog-nose-detector (~460 images)
2. https://universe.roboflow.com/bachelors-ll4ki/dog-nose (~396 images, class includes `dog-nose`)
3. Kaggle: https://www.kaggle.com/datasets/pratikmore33/dog-nose-detection-yolo  
   (use only if the Kaggle page shows **YOLO `.txt` labels**, not just raw photos)

**Do not download for Phase 1:**

- images.cv “361 dog nose” — classification, no boxes
- “detect the whole dog” / breed datasets
- Nexdata 64k noses — that is for **identity** (Phase 2), often paid

---

## Steps (Roboflow — recommended)

### 1. Create a free account
1. Open https://roboflow.com and sign up (Google login is fine).
2. Confirm your email if asked.

### 2. Open the dataset
1. Open: https://universe.roboflow.com/dog-ddgsn/dog_nose-6yo9t
2. Click **Dataset** / the latest **Versions** number (v1 is fine).
3. Click **Download Dataset** (or **Use this Dataset** → Download).

### 3. Export format (this matters)
On the download popup:

| Setting | Choose |
|---|---|
| Format | **YOLOv8** (sometimes shown as “YOLOv8 PyTorch TXT”) |
| Train / valid split | Keep the default (do not put 100% in train) |
| Augmentation | **Off** (we augment during training) |
| Resize | **Stretch to 640×640** is OK, or “Fit within 640×640” |

Then download the ZIP. It is usually 20–80 MB.

### 4. Check the ZIP before you send it
Unzip and confirm you see something like:

```
data.yaml
train/
  images/     ← .jpg / .png
  labels/     ← matching .txt files
valid/        ← or val/
  images/
  labels/
```

`data.yaml` should mention a class like `dog-nose` or `nose`.

If you only see folders of images and **no** `labels/` and **no** `.txt` files, it is the wrong export. Download again as **YOLOv8**.

### 5. Give it to this project
Either:

**A. Drop the zip in the repo (preferred)**  
Put the file here (zip is enough; I will unpack it):

```
d:\NosePrints-Pawfriend\ml\data\detector\dog-nose-yolov8.zip
```

Create the folders if they do not exist: `ml` → `data` → `detector`.

**B. Or attach the zip in this Cursor chat**

Do not commit the zip to git. `ml/data/` is already gitignored.

---

## Steps (Kaggle backup)

1. Create a free account at https://www.kaggle.com
2. Open https://www.kaggle.com/datasets/pratikmore33/dog-nose-detection-yolo
3. Click **Download** (top right).
4. Unzip once and check there are `.txt` YOLO label files next to (or beside) images.
5. Zip it again if needed and put it at:

```
d:\NosePrints-Pawfriend\ml\data\detector\dog-nose-yolov8.zip
```

---

## Optional extra (not required for download)

If you can, take **10 phone photos** of real dog noses (close, in focus) and put them in:

```
d:\NosePrints-Pawfriend\ml\data\detector\phone-test\
```

That is only for checking the trained model later. It is not the training set.

---

## After you drop the zip

Reply here: **“dataset is in ml/data/detector”**  
Then training scripts + YOLOv8-nano fine-tune can start.

---

## When Phase 1 is done

Identity matching needs a **different** dataset (many photos per dog). See [identity-download-guide.md](./identity-download-guide.md).

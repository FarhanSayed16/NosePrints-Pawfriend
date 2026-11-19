# What to upload to Gemini (file locations)

**Repo root:** `D:\NosePrints-Pawfriend`  
**How to use:** Upload the **Tier 1** set first (required). Add Tier 2 if Gemini allows more files. Tier 3 is optional code. Do **not** upload `.env`, passwords, or large image datasets.

Also open and paste: [`GEMINI_PROMPT.md`](./GEMINI_PROMPT.md)

---

## Tier 1 — Required (upload these)

| # | Full path | Why |
|---|-----------|-----|
| 1 | `D:\NosePrints-Pawfriend\docs\GEMINI_FIELD_DETECTION_BRIEF.md` | Current issue brief for Gemini |
| 2 | `D:\NosePrints-Pawfriend\docs\GEMINI_PROMPT.md` | (You paste this; upload optional) |
| 3 | `D:\NosePrints-Pawfriend\docs\SYSTEM_STATUS_AND_ENHANCEMENT_PLAN.md` | Full system status |
| 4 | `D:\NosePrints-Pawfriend\docs\ACCURACY.md` | Honest metrics |
| 5 | `D:\NosePrints-Pawfriend\docs\DATASET_INVENTORY.md` | What data exists on disk |
| 6 | `D:\NosePrints-Pawfriend\docs\GARBAGE_PHOTO_FALSE_MATCH_PLAN.md` | Junk / false-match history |
| 7 | `D:\NosePrints-Pawfriend\docs\NEXT_ML_DECISION_REPORT.md` | Latest ML decisions |
| 8 | `D:\NosePrints-Pawfriend\docs\CAPTURE_UX.md` | Capture UX rules |
| 9 | `D:\NosePrints-Pawfriend\docs\G0_G3_AUDIT_FIXES.md` | Gate audit (G0–G3) |

**Windows tip:** In File Explorer go to `D:\NosePrints-Pawfriend\docs`, multi-select the files above, drag into Gemini.

---

## Tier 2 — Strongly recommended

| # | Full path | Why |
|---|-----------|-----|
| 10 | `D:\NosePrints-Pawfriend\docs\ML_ENHANCEMENT_MASTER_PLAN.md` | Longer ML roadmap |
| 11 | `D:\NosePrints-Pawfriend\docs\ML_PILOT_PROGRAM.md` | Phone pilot design |
| 12 | `D:\NosePrints-Pawfriend\docs\EXPERIMENT_A_MULTIPRINT_RESULTS.md` | Gallery aggregation results |
| 13 | `D:\NosePrints-Pawfriend\docs\EXPERIMENT_C_OPEN_SET_RESULTS.md` | Unknown-dog FPIR |
| 14 | `D:\NosePrints-Pawfriend\docs\DATA_LICENSES.md` | Licence constraints |
| 15 | `D:\NosePrints-Pawfriend\docs\VIVA_EXPLANATION_GUIDE.md` | How you explain the project |
| 16 | `D:\NosePrints-Pawfriend\docs\PROJECT_STATUS.md` | Short status |
| 17 | `D:\NosePrints-Pawfriend\docs\WHAT_CHATGPT_APPROVED.md` | Prior advisor constraints |

---

## Tier 3 — Training / inference code (for Gemini to reason about recipes)

| # | Full path | Why |
|---|-----------|-----|
| 18 | `D:\NosePrints-Pawfriend\ml\training\train_detector.py` | YOLO fine-tune entrypoint |
| 19 | `D:\NosePrints-Pawfriend\ml\training\train_embedding.py` | ArcFace train entrypoint |
| 20 | `D:\NosePrints-Pawfriend\ml\training\build_merged_detector_v1.py` | How merged detector data was built |
| 21 | `D:\NosePrints-Pawfriend\ml\training\export_onnx.py` | ONNX export |
| 22 | `D:\NosePrints-Pawfriend\ml\training\augmentations.py` | Existing augs |
| 23 | `D:\NosePrints-Pawfriend\backend\app\services\nose_detector.py` | Runtime detect + zoom/rotation |
| 24 | `D:\NosePrints-Pawfriend\backend\app\services\capture_pipeline.py` | Accept/reject before embed |
| 25 | `D:\NosePrints-Pawfriend\backend\app\services\nose_heuristics.py` | Leather / skin / junk scores |
| 26 | `D:\NosePrints-Pawfriend\backend\app\services\look_gate.py` | Appearance soft gate (false keyboard) |
| 27 | `D:\NosePrints-Pawfriend\backend\app\config.py` | Thresholds |

Optional dataset yaml (small text file):

| # | Full path |
|---|-----------|
| 28 | `D:\NosePrints-Pawfriend\ml\data\detector\dog_nose_yolov8\data.yaml` |
| 29 | `D:\NosePrints-Pawfriend\ml\data\detector\merged_v1\data.yaml` *(if present)* |

---

## Do NOT upload

| Path / type | Reason |
|-------------|--------|
| `backend\.env` | Secrets (DB password, JWT) |
| `backend\models\*.onnx` | Large binaries; Gemini doesn’t need weights |
| `ml\data\identity\**\*.jpg` | Huge; summarize via `DATASET_INVENTORY.md` |
| `ml\data\detector\**\images\` | Thousands of images |
| `ml\checkpoints\**\*.pt` | Large; mention paths in chat instead |
| Staff passwords / Supabase keys | Security |

If Gemini asks “where are the weights?”, answer in chat:

- Detector: `D:\NosePrints-Pawfriend\backend\models\nose_detector.onnx`
- Embedding: `D:\NosePrints-Pawfriend\backend\models\embedding_model.onnx`
- Torch baseline: `D:\NosePrints-Pawfriend\ml\checkpoints\embedding\best_model.baseline.pt`

---

## Optional: phone failure screenshots

If you want Gemini to see the UX failures, upload a **few** screenshots only (not dozens):

`C:\Users\farha\.cursor\projects\d-NosePrints-Pawfriend\assets\`

Examples from 19 Nov testing:

- Look-photo false “keyboard” on real dog  
- Assist crop on whiskers / loose nose box  
- Correct reject on pants / blurry keyboard  

---

## Suggested Gemini chat sequence

1. Upload **Tier 1** (+ paste prompt from `GEMINI_PROMPT.md`).  
2. Wait for Option matrix + recommended plan.  
3. Upload **Tier 3 code** and ask: “Refine the ML recipe against these exact scripts and thresholds.”  
4. Ask a follow-up: “Given RTX 4050 6GB and empty PawFriend phone set, what is the minimum labeling plan for 7 days?”

---

## Quick copy list (Tier 1 only)

```
D:\NosePrints-Pawfriend\docs\GEMINI_FIELD_DETECTION_BRIEF.md
D:\NosePrints-Pawfriend\docs\SYSTEM_STATUS_AND_ENHANCEMENT_PLAN.md
D:\NosePrints-Pawfriend\docs\ACCURACY.md
D:\NosePrints-Pawfriend\docs\DATASET_INVENTORY.md
D:\NosePrints-Pawfriend\docs\GARBAGE_PHOTO_FALSE_MATCH_PLAN.md
D:\NosePrints-Pawfriend\docs\NEXT_ML_DECISION_REPORT.md
D:\NosePrints-Pawfriend\docs\CAPTURE_UX.md
D:\NosePrints-Pawfriend\docs\G0_G3_AUDIT_FIXES.md
```

Paste prompt from:

```
D:\NosePrints-Pawfriend\docs\GEMINI_PROMPT.md
```

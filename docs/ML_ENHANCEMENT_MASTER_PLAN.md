# NosePrints × PawFriend — ML Enhancement Master Plan

**Status:** Approved engineering plan (decision locked by repo audit)  
**Date:** 9 November 2026  
**Inputs:** Jagjit / ChatGPT dataset research · [`NOSEPRINTS_ML_DATASET_RESEARCH_AND_CURSOR_HANDOFF.md`](./NOSEPRINTS_ML_DATASET_RESEARCH_AND_CURSOR_HANDOFF.md) · [`PROJECT_STATUS.md`](./PROJECT_STATUS.md) · [`ACCURACY.md`](./ACCURACY.md) · live `ml/` inventory  
**Rule:** This file is the **work plan**. The research handoff is background. If they conflict, follow this file.

---

## 0. One-line decision

> **Do not replace the architecture.** Keep YOLOv8-nano + ResNet50/ArcFace/ONNX.  
> **Constraint (locked 9 Nov 2026):** No PawFriend / clinic / shelter photo collection for now. Work only with **data already on disk** + **free public downloads I can fetch**, then retrain/evaluate/export.  
> Field accuracy on Mumbai phone photos will stay limited until real pilot data exists later — that is an accepted trade-off for this phase.

### 0.1 What we can do *without* you collecting data

| Can do now | How |
|------------|-----|
| Inventory + baseline freeze | Already have CVPR + Roboflow on disk |
| **Retrain / continue-train embedding** on 6,000-dog CVPR set | More epochs, aug/LR/margin experiments from `best_model.pt` |
| **Retrain YOLO detector** on Roboflow ~4.7k images | Longer train, stronger aug, hard-negative backgrounds |
| Download **extra free YOLO nose sets** (Roboflow CC BY backups) if useful | Merge carefully; re-eval |
| Generate **synthetic junk** (keyboard/fabric/wall) for gate + detector background | No owner photos needed |
| Open-set / ROC re-eval on held-out CVPR IDs | Recalibrate thresholds if scores move |
| Export new ONNX + A/B vs current models | Keep `*.prev.onnx` rollback |
| Product/heuristic polish | Thresholds, capture UX — no new photos |

### 0.2 What we cannot do without your collection / money

| Cannot do | Why |
|-----------|-----|
| Guarantee better **real phone** accuracy in the field | CVPR ≠ street/phone domain |
| Buy **Nexdata** or other paid sets | Needs your budget + licence |
| Use **PetFace** in product | Non-commercial research only |
| Hit CVPR-winner **0.86 AUC** as a promise | May or may not move with public data alone |

### 0.3 Maximum-accuracy track **without** your photo collection (what we will actually run)

Goal: push **benchmark** accuracy (AUC / rank-1 / detector mAP) as far as public data allows.

| Wave | Action | Adds data? | Expected effect |
|------|--------|------------|-----------------|
| **W1** | Freeze baseline hashes + metrics | No | Fair A/B |
| **W2** | Download extra **free YOLO nose-box** sets (Roboflow backups: pireco, bachelors, etc.) + merge with current 4.7k | **Yes — more detector images** | Better nose find / fewer misses |
| **W3** | Build synthetic hard-negative backgrounds (keyboard, fabric, blank, UI) for YOLO + gate tests | **Yes — synthetic** | Fewer junk false detections |
| **W4** | Optional public landmark sets → auto nose-box proposals (StanfordExtra / Animal-Pose / Zenodo) **only if licence OK**, then filter | **Yes — detector** | More localization variety |
| **W5** | Harder **embedding** training on full CVPR 6k: continue from `best_model.pt`, more epochs, stronger but safe aug, LR schedule, ArcFace margin sweep | No new IDs (reuse 20k imgs) | Best chance to lift AUC/rank-1 |
| **W6** | Optional architecture A/B on same data: EfficientNet / larger input / light triplet+ArcFace — **only if W5 plateaus** | No | Maybe small lift; costlier |
| **W7** | Full ROC + open-set on held-out CVPR IDs → new thresholds → ONNX export + rollback | No | Ship only if metrics win |
| **W8** *(blocked on you)* | Nexdata purchase (~64k images / 1k dogs) | **Yes — biggest external nose-print set** | Largest possible public-style jump without PawFriend dogs |

**Realistic outcome:** W1–W7 can improve **lab/CVPR-style** scores and detector robustness. They will **not** fully fix muddy street-phone photos. W8 needs your money. Real PawFriend dogs later are still the field unlock.

**Approx compute (RTX 4050 6GB):** detector retrain hours; embedding continue-train overnight-class. Disk: keep downloads under `ml/data/` (gitignored).

---

---

## 1. What we verified in *this* repo (facts)

| Item | Evidence |
|------|----------|
| Detector ONNX | `backend/models/nose_detector.onnx` (~11.7 MB) |
| Embedding ONNX | `backend/models/embedding_model.onnx` (~99.6 MB) |
| Identity data already present | `ml/data/identity/train/` ≈ **6000** dog folders (CVPR mirror) |
| Detector data present | `ml/data/detector/dog_nose_yolov8/` |
| Checkpoints | `ml/checkpoints/` (`best_model.pt`, `final_model.pt`) |
| Training code | `ml/training/train_detector.py`, `train_embedding.py`, `evaluate.py`, `export_onnx.py`, … |
| Documented metrics | `ml/eval_results/embedding/metrics.txt` → AUC **0.803**, rank-1 **0.786**, T_high **0.559**, T_low **0.505** |

**Implication:** Do **not** re-download CVPR “to get started.” Audit and reuse. External downloads are only for *new* value (phone detector fails, Nexdata if licensed, pilot dogs).

---

## 2. What we take from the research (adopt)

| Idea from research | Our decision | Why |
|--------------------|--------------|-----|
| Two different datasets for YOLO vs ArcFace | **Adopt** | Already true in our docs; keep folders separate forever |
| CVPR first — audit, don’t duplicate | **Adopt** | 6000 IDs already on disk |
| PawFriend ≥50 dogs, 5–10 images, multi-session | **Adopt as P0** | Only path to field accuracy; matches MASTER_PLAN |
| ~384 px min nose-region width (Petnow-informed) | **Adopt as soft capture target** | Guide crop UX + reject tiny ROIs; not a hard magic number |
| Session IDs + metadata (device, lighting, angle, consent) | **Adopt** | Prevents train/test leakage and burst duplicates |
| Nexdata as commercial lead | **Adopt as optional P0 lead only** | Request sample + quote; **no purchase until ID labels + commercial rights confirmed** |
| StanfordExtra / Animal-Pose / Zenodo for detector help | **Adopt as P1 helpers only** | Keypoints ≠ leather boxes; human-review before YOLO labels |
| Hard negatives (keyboard, fabric, fur, screens) | **Adopt** | Extends G0–G3; feed detector + gate eval set |
| Fine-tune from existing checkpoint | **Adopt** | Do not train ArcFace from scratch |
| Leakage-safe splits + open-set unknown-dog tests | **Adopt** | Required for honest “no match” |
| Keep staff confirmation | **Adopt (locked)** | Product safety; ML never auto-releases contact |
| Controlled one-change experiments | **Adopt** | No big-bang architecture swap |

---

## 3. What we reject or defer (do not do now)

| Idea | Decision | Why |
|------|----------|-----|
| Replace ResNet50 / ArcFace / YOLO with a paper’s fancy stack | **Reject for now** | No evidence our errors are capacity vs data/crop |
| Switch loss to triplet/circle “because CVPR paper did” | **Defer** | Only after baseline fine-tune + measured gap |
| PetFace as training data | **Reject for product** | Non-commercial research restriction |
| AI-generated dog noses | **Reject** | Not real identities |
| Instagram / Google Images scrape | **Reject** | Licence + label quality |
| Oxford-IIIT / Multi-pose as identity set | **Defer / reject for ArcFace** | Heads ≠ nose prints |
| images.cv 361 noses for ArcFace | **Reject for identity** | No dog IDs; tiny |
| Buy Nexdata immediately | **Reject until sample gate** | Must prove per-dog IDs, sessions, commercial deploy rights |
| Claim “we will hit 86% AUC” from 50 dogs | **Reject as promise** | 50 dogs = pilot start; metric after held-out eval only |
| Auto-wipe production DB / overwrite ONNX without rollback | **Reject** | Ops safety |

---

## 4. Goal metrics (honest)

| Metric | Current baseline | Enhancement target | Notes |
|--------|------------------|--------------------|-------|
| Embedding AUC (protocol as in `metrics.txt`) | **0.80** | Improve on **same protocol** first; stretch toward **≥ 0.86** only if data allows | Never claim paper scores as ours |
| Rank-1 gallery-probe | **78.6%** | Measurable lift on held-out | Report N dogs / images beside score |
| Detector close-up recall (phone) | ~70% (lab) | Higher on **PawFriend phone set** | Measure separately from Roboflow val |
| Junk false-accept (keyboard/fabric/fur) | Gated in code | Keep / improve with labelled fail set | Product gate, not only ML |
| Unknown dog → no match | Threshold bands exist | Calibrate on open-set holdout | Staff still confirms |

---

## 5. Workplan phases (start here)

### Phase A — Freeze baseline & inventory (1–2 days) ✅ start immediately

**Do:**
1. Record hashes/sizes of both ONNX files + `best_model.pt`.
2. Write `docs/DATASET_INVENTORY.md`: counts for `identity/train|val`, detector splits, disk use (no PII).
3. Spot-check 20 identity folders (IDs, duplicates, tiny images).
4. Confirm `/health` → `embedding_mode: real` when API runs.
5. Copy current `metrics.txt` into the inventory as **Baseline-2026-08**.

**Do not:** download anything, retrain, change thresholds.

**Exit:** Written inventory + “baseline frozen” note in this plan’s changelog.

---

### Phase B — Licence & source gate (2–3 days, parallel)

Create `docs/DATA_LICENSES.md` with status per source:

| Source | Status to set |
|--------|----------------|
| Existing CVPR mirror on disk | `approved` (reuse) after card/terms note |
| Nexdata | `pending` until sample + commercial quote |
| StanfordExtra / Animal-Pose / Zenodo | `pending` until rights reviewed |
| PetFace | `research_only` / blocked for product |
| PawFriend pilot | `approved` only with consent text |

**Owner action needed:** Decide whether to email Nexdata for a sample (yes/no + budget).

---

### Phase C — PawFriend pilot capture (ongoing; target 50 dogs)

**This is the #1 accuracy lever.**

| Spec | Value |
|------|-------|
| Dogs | ≥ **50** (stretch 100) |
| Images / dog | **5–10** usable nose crops |
| Sessions | Prefer **≥2 days** or ≥2 lighting conditions — not one burst |
| Min nose width | Soft target **≥ ~384 px** after crop |
| Consent | Explicit training/eval use; store `consent_id`; **no phones in ML metadata** |
| Capture mix | Frontal + slight L/R; indoor + outdoor; different phone if possible |

**Product hooks (small engineering, high value):**
- Opt-in checkbox on register: “Allow anonymised nose images for model improvement.”
- Export path: staff tool or script → `ml/data/pawfriend_pilot/raw/<dog_pseudo_id>/<session_id>/*.jpg` + `manifest.csv`.
- Reject near-duplicates (same burst) in export.

**Folder layout (new):**

```text
ml/data/pawfriend_pilot/
  raw/<dog_id>/<session_id>/*.jpg
  crops/<dog_id>/<session_id>/*.jpg   # after YOLO/manual
  manifest.csv
  consents.jsonl                      # ids only, no phones
```

**Exit:** ≥50 dogs with multi-angle crops + manifest.

---

### Phase D — Detector improvement (1–2 weeks after first phone fails)

1. Collect **failure gallery**: missed noses, wrong boxes, pink/dark noses, muddy, angled (from pilot + acceptance).
2. Manually label **tight nose-leather boxes** (Label Studio / Roboflow / CVAT).
3. Add **hard negatives** (keyboard, fabric, fur, screens) for false-positive training/eval.
4. Optional: StanfordExtra / Animal-Pose only to **propose** boxes → human fix → YOLO labels.
5. Retrain YOLOv8n from current recipe; keep old ONNX as `nose_detector.prev.onnx`.
6. Eval: mAP + phone fail-set recall; do not ship if phone recall regresses.

**Commands (verify `--help` before run):**

```powershell
cd D:\NosePrints-Pawfriend\ml
.\.venv\Scripts\activate
cd training
python train_detector.py --epochs 40 --batch 8 --imgsz 640 --device 0
```

---

### Phase E — Embedding fine-tune (1–3 weeks once ≥50 pilot dogs)

1. Merge **approved** pilot crops into identity layout (pseudonymous IDs).
2. Keep CVPR as pretrain / large-scale regularizer; fine-tune from `checkpoints/.../best_model.pt`.
3. Split by **dog_id** (and session for gallery/probe). Freeze a final test set.
4. Train **one change at a time** (data first; loss/backbone later only if needed).
5. Run `evaluate.py`; save new `ml/eval_results/embedding/metrics_<date>.txt`.
6. Recalibrate `MATCH_THRESHOLD` / `MATCH_THRESHOLD_LOW` from **new** ROC — do not keep 0.56/0.51 blindly.
7. Export ONNX → `embedding_model.candidate.onnx` → parity test → promote with rollback.

```powershell
cd D:\NosePrints-Pawfriend\ml
.\.venv\Scripts\python.exe training\train_embedding.py `
  --data_dir data\identity --epochs 50 --batch_size 16 --num_workers 0 `
  --checkpoint_dir checkpoints\embedding
```

**Exit:** Candidate beats baseline on frozen protocol **or** clearly helps field pilot with documented trade-offs; staff confirm still on.

---

### Phase F — Open-set + gates + phone acceptance (parallel with E)

1. Unknown-dog set (identities never in gallery train).
2. Measure false-accept at Likely threshold; tune / enable `MATCH_STRICT_DEMO` for demos if needed.
3. Label residual junk that still passes G0–G3; threshold tweak **before** adding a binary classifier.
4. Real-phone HTTPS checklist: keyboard reject, fabric/fur reject, real nose accept ×3, look soft-warn.

---

### Phase G — Optional Nexdata (only if Phase C saturates)

1. Request sample: confirm **stable dog_id**, images/dog, sessions, resolution, mask format, **commercial train+deploy** rights, price.
2. If sample fails ID/rights → stop.
3. If pass → owner approves purchase → ingest under `ml/data/raw/nexdata/` with licence register → controlled fine-tune experiment vs pilot-only model.

---

## 6. Engineering deliverables checklist

| Deliverable | Path / artifact |
|-------------|-----------------|
| This plan | `docs/ML_ENHANCEMENT_MASTER_PLAN.md` |
| Inventory | `docs/DATASET_INVENTORY.md` (create in Phase A) |
| Licence register | `docs/DATA_LICENSES.md` (create in Phase B) |
| Pilot manifest schema | `ml/data/pawfriend_pilot/manifest.csv` |
| Baseline metrics freeze | copy of `metrics.txt` |
| Candidate ONNX + rollback | `backend/models/*.candidate.onnx` / `*.prev.onnx` |
| New eval logs | `ml/eval_results/embedding/metrics_YYYYMMDD.txt` |

---

## 7. What I need from you (only if blocking)

You can start **Phase A** with zero extra input. Provide these when ready:

1. **Nexdata:** Yes/No to request a sample + max budget.  
2. **Consent copy:** Confirm PawFriend legal OK for “training opt-in” wording (or paste preferred text).  
3. **Pilot channel:** Who recruits the first 50 dogs (clinics / shelters / existing owners)?  
4. **GPU:** Confirm training machine still available (RTX used previously).  
5. **Strict demo:** Keep `MATCH_STRICT_DEMO` off or on for senior demos?

I do **not** need you to paste ChatGPT research again — it is already folded into this plan. I do **not** need another architecture redesign.

---

## 8. Immediate next actions (this week)

1. Run Phase A inventory (no downloads).  
2. Purge junk registry dogs if still polluted (ops — separate from ML).  
3. Draft consent + pilot capture SOP (can live in `docs/STAFF_SOP.md` addendum).  
4. Start collecting first 10 pilot dogs with session discipline.  
5. Log every phone detector miss into a fail folder for Phase D.

---

## 9. Changelog

| Date | Note |
|------|------|
| 2026-11-09 | Plan created from Jagjit research + repo audit. Architecture frozen; PawFriend pilot + audit prioritized over new nets / premature Nexdata buy. |

---

*Related: [`PROJECT_STATUS.md`](./PROJECT_STATUS.md) · [`ACCURACY.md`](./ACCURACY.md) · [`dataset-download-guide.md`](./dataset-download-guide.md) · [`identity-download-guide.md`](./identity-download-guide.md) · research handoff (background only).*

# NosePrints — Final End-to-End Field Betterment Plan

**Status:** AGREED (owner clarification + Gemini review, 19 Nov 2026) · **Phase 0–1 implemented; 1.5 scaffolded; 2–3 gated on labels**  
**Target:** Real dog phone photos succeed ≥ **2 of 3** attempts → Nose crop ready → match/register  
**Demo:** `https://noseprints.farhanbuilds.in`  
**Hardware for train:** RTX 4050 6GB  

This is the **single source of truth** for what is wrong and what we execute next.  
Do not mix keyboard/dark post-fail screenshots into diagnosis.

**Implementation progress**

| Phase | Status |
|-------|--------|
| 0 Measure | Done — `phone_eval` seeded + `FAILURE_MAP.md` (dominant: Stage-2 miss / assist) |
| 1 UX | Done — stale error clear, leather-fill copy, vignette, Tighten pulse, API issues |
| 1 retest | Checklist — [PHASE1_RETEST_CHECKLIST.md](./PHASE1_RETEST_CHECKLIST.md) |
| 1.5 Dataset | Scaffold + backups + negatives — owner labels 30–100 leather boxes |
| 2 Train | Script ready (`scale`/`mosaic`/`hsv`) — run after labels |
| 2 Promote | `scripts/promote_nose_onnx.py` gates on phone_eval |
| 3 Polish | [PHASE3_POLISH.md](./PHASE3_POLISH.md) — thresholds frozen until evidence |

---

## Part 1 — What is happening (locked diagnosis)

### Confirmed failure chain on real dog photos

```
Real dog photo (1–3 m / face / snout)
        │
        ▼
Stage-1 COCO dog     → often OK (head ROI)
        │
        ▼
Stage-2 nose YOLO    → MISS or very low conf on distance shots  ← PRIMARY GAP
        │
        ▼
Heuristic assist box → inherently LOOSE (fur / whiskers / muzzle)
        │
        ▼
User taps "Use this crop" without pinching to leather only
        │
        ▼
prepare_nose_scan    → rejects low nose_likeness  ← CORRECT (keep strict)
        │
        ▼
Camera reopens with STALE error banner still visible  ← UX BUG
        │
        ▼
Screenshots of dark/keyboard idle preview  ← IGNORE (not the input)
```

### What worked once

Tight / leather-dominant crop → **Nose crop ready** → proves embed + gates + matching path work when leather fills the crop.

### What is already correct (do not undo)

| Keep | Why |
|------|-----|
| Strict `NOSE_MIN_LIKENESS` / soft-miss | Loose fur/paw must not enter pgvector |
| No full-frame nose search after dog found | Stops paw/shadow false locks |
| Batch-1 whisker/edge assist penalty | Best-effort math until YOLO improves |
| Staff confirm before owner contact | Product safety |
| ArcFace embedder this sprint | Not the bottleneck |

### Success definition (“everything works well”)

| Metric | Now (field) | Target |
|--------|-------------|--------|
| Real dog attempts → Nose crop ready | ~1/3 | **≥2/3** |
| Assist/YOLO box near leather (IoU≥0.5 vs GT) | Low | **≥70%** on held-out phone set |
| Stale error on camera reopen | Yes (bug) | **Never** |
| Confirm shows exact reject reason | Weak/generic | **Always** |
| Junk accidentally embedded | Must stay ~0 | **Stay ~0** (gates stay strict) |

---

## Part 2 — Two-step precision strategy (Gemini-aligned)

| Step | When | Goal |
|------|------|------|
| **1. Manual precision (UX)** | This week — start immediately | Recover failed attempts by forcing leather-tight crops + clear stale errors + real API messages |
| **2. Automated precision (ML)** | Next week after 30–100 labels | Stage-2 YOLO finds tiny noses at phone distance so users fight the crop UI less |

UX alone improves success without training.  
Fine-tune alone is the permanent fix.  
**Do both in order. Do not lower likeness gates to fake demos.**

---

## Part 3 — Execution roadmap (end-to-end)

### WEEK 0 / Day 1 — Phase 0: Measure (truth before code)

| ID | Task | Output |
|----|------|--------|
| P0.1 | Collect **only real dog** fail + success JPEGs from the phone session into `ml/data/phone_eval/` | Folder populated (no keyboard snaps) |
| P0.2 | Run `scripts/eval_phone_detect.py` | Table: `dog_conf`, `nose_conf`, `hint`, per file |
| P0.3 | Reproduce one fail → capture exact `prepare_nose_scan` / API error body | Logged reason string |
| P0.4 | Tag each file: Stage-1 miss / Stage-2 miss / loose assist / likeness reject / success | Failure map |

**Exit gate:** We can name the dominant fail stage (expected: Stage-2 miss + loose assist + likeness).

---

### WEEK 1 — Phase 1: Immediate UX precision (highest ROI now)

Implement before any training. No threshold weakening.

| ID | Task | Detail | Done when |
|----|------|--------|-----------|
| P1.1 | **Clear stale error on camera reopen** | Reset error state when retry capture / camera remounts (`setError(null)` or equivalent in identify/capture flow) | Dark/idle preview never shows previous “No dog nose…” |
| P1.2 | **Force tighten copy** | Crop UI: *“Pinch until ONLY the wet black/pink nose leather fills the circle, then confirm.”* | Copy live on crop screen |
| P1.3 | **Optional circular vignette guide** | Transparent center mask on crop editor (visual only — not auto-crop) | User sees fill-the-circle target |
| P1.4 | **Surface real API reject reasons** | On failed “Use this crop”, show backend text (e.g. likeness / leather) | No silent/generic “no outcome” |
| P1.5 | **Prompt Tighten** | Emphasize Tighten control when box is large vs leather | One clear action path |
| P1.6 | **No auto-tighten blob logic** | Gemini: risk of snapping to one nostril → ruins ArcFace geometry | Manual pinch only this sprint |

**Exit gate (phone retest on same dogs):**

- Stale banner gone.  
- At least some previously failing dogs reach crop-ready **after guided tighten**.  
- Informal success trending up from ~1/3 (even if not yet 2/3).

---

### WEEKEND — Phase 1.5: Dataset build (feeds Phase 2)

| ID | Task | Spec |
|----|------|------|
| D1 | Shoot / gather **30–100** street dog phone photos at **1–3 m** (and some closer faces) | Same domain as field fails |
| D2 | Label **tight nose leather only** (YOLO boxes) | Not whole muzzle / eyes / face |
| D3 | Add **20–30 hard negatives** (paws, concrete, hands, faces, keyboards) | **Empty** label `.txt` files = background |
| D4 | Hold out **~20%** phone images for eval only | Never train on them |
| D5 | Keep a copy of current `nose_detector.onnx` + `merged_v1` `.pt` as rollback | Safe promote/rollback |

**Dataset layout (suggested):**

```
ml/data/detector/phone_v1/
  train/images + train/labels
  val/images   + val/labels     ← held-out phone shots
  negatives/   (empty labels merged into train)
  data.yaml
ml/data/phone_eval/             ← quick runtime smoke (same as script)
```

---

### WEEK 2 — Phase 2: Stage-2 fine-tune (permanent precision)

**Hardware:** RTX 4050 6GB · **Model:** YOLOv8n · **Base:** current `merged_v1` weights · **Freeze:** none (train end-to-end)

| ID | Setting | Value |
|----|---------|-------|
| T1 | epochs | **50** (early stop patience **15**) |
| T2 | imgsz | **640** |
| T3 | batch | **16** (fits 6GB for nano; drop to 8 if OOM) |
| T4 | scale | **0.5–0.6** (force tiny-nose learning / zoom-out domain) |
| T5 | mosaic | **1.0** |
| T6 | hsv_s / hsv_v | Mild variance (pink/brown + wet/muddy) |
| T7 | Negatives | ~20% empty-label backgrounds |
| T8 | Script | `ml/training/train_detector.py` (+ phone_v1 `data.yaml`) |
| T9 | Export | ONNX → candidate `nose_detector.onnx` (do not overwrite until promote) |

**Promotion criteria (strict — ignore vanity lab mAP):**

Promote **only if** on held-out / `phone_eval` dog set:

1. Higher Stage-2 confidence on previously failing dog photos, **and**  
2. Tighter boxes (better IoU vs leather GT or visibly leather-centered), **and**  
3. Macro close-up success **does not regress**, **and**  
4. No spike in accepting paws/keyboards into embed path.

If not met → keep old ONNX, adjust data/augs, retrain. Never “promote to look busy.”

**Exit gate:** Repeat live phone test on the **same dogs** → **≥2/3** → Nose crop ready with less fighting the crop UI.

---

### WEEK 2–3 — Phase 3: Polish (only after promote)

| ID | Task | Rule |
|----|------|------|
| P3.1 | Soft-miss / likeness review | **Only with labeled evidence** — default = leave strict |
| P3.2 | In-camera coaching (“fill circle with leather before shutter”) | Reduce whole-body misuse |
| P3.3 | Dog-face Stage-1 | Only if Phase 0 proves COCO dog miss is common |
| P3.4 | Staff match UX | Separate from detector |

---

## Part 4 — What we will NOT do

1. Diagnose from post-fail keyboard/dark screenshots.  
2. Lower `NOSE_MIN_LIKENESS` / soft-miss to make demos smoother.  
3. Re-enable full-frame nose search when Stage-1 found a dog.  
4. Build auto-tighten from dark pixel blobs (nostril snap risk).  
5. Replace ArcFace or drop staff confirmation this sprint.  
6. Claim lab mAP/AUC as field accuracy.  
7. Freeze YOLO layers “to be safe” on YOLOv8n 6GB — train full nano end-to-end.  
8. Promote ONNX without `eval_phone_detect.py` improvement on real dog photos.

---

## Part 5 — Week-by-week checklist

### This week (UX + data start)

- [ ] P0.1–P0.4 measure complete  
- [ ] P1.1 clear stale error  
- [ ] P1.2–P1.5 crop copy / reasons / tighten emphasis  
- [ ] Phone retest: stale banner gone; some fails recoverable by pinch  
- [ ] Start labeling phone_v1 leather boxes  

### Next week (train + promote)

- [ ] 30–100 leather labels + 20–30 empty-label negatives + holdout  
- [ ] Train YOLOv8n from merged_v1 (recipe above)  
- [ ] Eval vs old ONNX on phone holdout  
- [ ] Promote only if criteria pass  
- [ ] Live: **≥2/3** real dog attempts → Nose crop ready  

### After stabilize

- [ ] Optional threshold review with evidence  
- [ ] Optional Stage-1 upgrade if dog-miss proven  
- [ ] Document before/after numbers in repo  

---

## Part 6 — File / command map

| Area | Path / command |
|------|----------------|
| Two-stage detect | `backend/app/services/nose_detector.py` |
| Assist + likeness | `backend/app/services/nose_heuristics.py` |
| Confirm gate | `backend/app/services/capture_pipeline.py` |
| Preview API | `backend/app/routers/matching.py` |
| Thresholds | `backend/app/config.py` (**do not weaken yet**) |
| Capture / crop UI | Frontend identify/camera + NoseCropEditor |
| Phone smoke eval | `scripts/eval_phone_detect.py` |
| Train | `ml/training/train_detector.py` |
| Export | `ml/training/export_onnx.py` |
| Models | `backend/models/nose_detector.onnx`, `dog_detector_coco.onnx` |

Example eval (Windows):

```bat
set PYTHONPATH=D:\NosePrints-Pawfriend\backend
backend\venv\Scripts\python.exe scripts\eval_phone_detect.py
```

---

## Part 7 — Risk register

| Risk | Mitigation |
|------|------------|
| Lowering gates pollutes pgvector | Forbidden until labeled proof; prefer better boxes |
| Fine-tune overfits black noses only | hsv augs + pink/brown leather in labels |
| Train OOM on 6GB | batch 16 → 8; keep nano |
| Promote weak ONNX | Hard phone_eval gate + rollback `.onnx` |
| Users still confirm loose boxes | Vignette + copy + real error text (Phase 1) |
| Auto-tighten nostril snap | Not building this sprint |

---

## Part 8 — One-page summary

**Problem:** Stage-2 misses noses at phone distance → loose assist → likeness correctly rejects → stale error on camera reopen.  
**Not the problem:** Keyboard/dark idle screenshots; ArcFace; Supabase.  
**Fix now:** Clear error + force leather-fill UX + show real reject reasons.  
**Fix next:** Label 30–100 phone leathers + negatives → fine-tune YOLOv8n (scale 0.5–0.6, mosaic, batch 16, 50 epochs) → promote only if phone_eval improves.  
**Keep strict:** Likeness gates, no full-frame-after-dog, no staff-bypass.  
**Done when:** ≥2/3 real dog field attempts reach Nose crop ready without luck.

---

*Gemini agreement locked into this plan. Execute Phase 1 immediately; Phase 2 after labels.*

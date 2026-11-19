# NosePrints — Gemini Handoff: Corrected Field Status (Suggestions Only)

**Date:** 19 November 2026 (corrected)  
**Gemini review:** AGREED — locked into [`FINAL_FIELD_BETTERMENT_PLAN.md`](./FINAL_FIELD_BETTERMENT_PLAN.md)  
**How to use:** Paste/upload this file to Gemini (historical ask). For execution, use the FINAL plan.  
**Companion plan:** [`FIELD_DETECTION_STATUS_AND_PLAN.md`](./FIELD_DETECTION_STATUS_AND_PLAN.md)  
**Optional:** [`GEMINI_COMPLETE_PROJECT_DOCUMENT.md`](./GEMINI_COMPLETE_PROJECT_DOCUMENT.md) · `gemini_batch1_runtime.zip`

---

## Your role

Senior CV + product advisor.  
Critique diagnosis, prioritize fixes, give train/UX/threshold suggestions with risks.  
**Do not** redesign the stack. **Do not** re-implement Stage-1 (already live).

---

## CRITICAL — do not misread the screenshots

Owner confirmation:

- **Every scan attempt used a real dog image.**  
- Roughly **1/3 succeeded**; the other attempts **failed detection / crop completion**.  
- After failure, the app returned to the **live camera loop**.  
- Screenshots showing a **dark frame or laptop keyboard** were taken **after** failure, while the camera was idle/ready for the next shot.  
- Those frames are **not** the inputs that failed. **Ignore them completely** for diagnosis.

| Valid evidence | Invalid / ignore |
|----------------|------------------|
| Crop editor on outdoor / held dogs | Dark camera with leftover error banner |
| “Nose crop ready” on tight leather | Keyboard / RGB backlight idle preview |
| Owner report: ~1/3 success on real dogs | Any “junk reject worked this session” claim |

If you reason from keyboard/dark as failed scans, your advice will be wrong.

---

## Product (one paragraph)

Phone PWA for **dog nose-leather** biometrics (not face). Flow: capture → crop confirm → quality gates → ArcFace 512-d → Supabase pgvector → **staff** confirm before owner contact. Demo: Cloudflare tunnel → local Vite.

---

## Already shipped (Batch-1)

| Item | Status |
|------|--------|
| Stage-1 COCO dog → head ROI → Stage-2 nose YOLO | Live |
| No full-frame nose search when dog was found | Live |
| Look-gate dog bypass (keyboard false-warn) | Live |
| Heuristic assist + whisker/edge penalty | Live |
| `scripts/eval_phone_detect.py` | Ready |

Files: `nose_detector.py`, `dog_detector.py`, `nose_heuristics.py`, `look_gate.py`, `capture_pipeline.py`, `matching.py`, `config.py`.

### Thresholds

```
DOG_STAGE1_ENABLED = True
DOG_DETECTOR_CONF ≈ 0.25
DETECTOR_CONF_THRESHOLD ≈ 0.32
DETECTOR_RETRY_CONF_THRESHOLD ≈ 0.15
DETECTOR_MIN_ACCEPT_CONF ≈ 0.28
DETECTOR_PREVIEW_SUGGEST_CONF ≈ 0.15
NOSE_MIN_LIKENESS ≈ 0.36
NOSE_SOFT_MISS_MIN_LIKENESS ≈ 0.48
```

Lab: merged_v1 mAP50 ≈ **0.54**, mostly **tight nose** boxes — weak on Indian phone whole-dog / top-down shots.

---

## Corrected field observation

Public: `https://noseprints.farhanbuilds.in`

1. **Inputs:** real dog photos only.  
2. **Outcome:** ~**1/3** reached a full usable result (**Nose crop ready**); rest failed mid-pipeline.  
3. **Success case:** leather-dominant / close nose crop.  
4. **Failure cases (real dogs):** crop UI often opened with a **loose** box (fur, whiskers, muzzle, paw); Stage-2 often weak; confirm/likeness path did not finish reliably.  
5. **After fail:** camera reopened; dark/keyboard screenshots are **post-fail UI only**.

### Our diagnosis (challenge if wrong)

- Failure is on **real dog distance/angle/crop quality**, not junk.  
- Dies at **detect-preview** (Stage-2 miss → weak assist) and/or **`prepare_nose_scan`** (leather gates on loose boxes).  
- Embed/matching not reached when crop never becomes ready.  
- Batch-1 improved assist/honesty; **did not** make typical phone dog shots succeed ~2/3+ of the time.  
- Stale error banners on the reopened camera confused screenshots — UX clear-on-reset is part of the fix.

---

## Plan we intend (critique priority)

### Phase 0 — Measure real dog fails
Save **failed + success dog JPEGs** (not keyboard snaps) → `ml/data/phone_eval/` → run eval → log exact confirm-fail API reasons → map Stage-1 vs Stage-2 vs likeness.

### Phase 1 — UX so dog attempts recover
Leather-must-fill copy · surface real reject reasons · **clear error when camera reopens** · prompt Tighten on fur-heavy boxes · soft block obviously loose confirms.

### Phase 2 — Main fix: Stage-2 phone fine-tune
Label tight leather on phone dog shots + hard negatives → fine-tune nose YOLO → ONNX promote only if dog phone_eval improves → retest same dogs until **≥2/3** succeed.

### Phase 3 — Thresholds later
Touch likeness/soft-miss **only with labels**; optional dog-face Stage-1 only if Stage-1 miss rate proven.

---

## Ask Gemini (answer in this structure)

### A. Diagnosis check
Agree/disagree that the session failures are **real-dog Stage-2 / loose-crop / likeness**, and that keyboard/dark shots must be ignored?

### B. Priority
Best single action this week to push success from ~1/3 → ≥2/3 on real dog photos?

### C. Stage-2 fine-tune recipe
For 30–100 labeled phone leather boxes + negatives: freeze strategy, epochs, imgsz, augs, negative mix, pink/brown leather, promotion criteria vs lab mAP.

### D. Heuristics / thresholds
Change whisker/edge assist now? Touch `NOSE_MIN_LIKENESS` / soft-miss **before** fine-tune or only after? Gates too harsh for dirty/wet Indian street noses?

### E. UX
Best pattern so users tighten leather before confirm? How to clear stale errors when returning to camera after fail? Risks of auto-tighten?

### F. What not to do
Anti-patterns (e.g. diagnosing from post-fail keyboard frames, blindly lowering junk gates, re-enabling full-frame after dog found, accuracy vanity claims).

### G. Out of scope
No ArcFace replace this sprint. No dropping staff confirm. No FastAPI/React rewrite.

---

## Constraints

- AI suggests; humans confirm matches.  
- Honesty over vanity metrics.  
- ONNX CPU-friendly (PC + tunnel demo).  
- Incremental fixes preferred.

---

## One-line status

**~1/3 real dog attempts succeed; keyboard/dark screenshots are post-fail camera only — ignore them; fix measure → clear/tighten UX → phone Stage-2 fine-tune until ≥2/3 dog photos reach Nose crop ready; advise recipe and priority, not a rewrite.**

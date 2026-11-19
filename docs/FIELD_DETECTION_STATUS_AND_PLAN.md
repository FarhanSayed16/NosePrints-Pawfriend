# NosePrints — Field Detection: Corrected Status & Complete Plan

**Date:** 19 November 2026 (corrected same day after owner clarification)  
**Public demo:** `https://noseprints.farhanbuilds.in`  
**FINAL executable plan (Gemini-agreed):** [`FINAL_FIELD_BETTERMENT_PLAN.md`](./FINAL_FIELD_BETTERMENT_PLAN.md)  
**Companion for Gemini:** [`GEMINI_CURRENT_STATUS_HANDOFF.md`](./GEMINI_CURRENT_STATUS_HANDOFF.md)

> Prefer **FINAL_FIELD_BETTERMENT_PLAN.md** for all execution. This file remains the diagnosis narrative.

---

## 0. Critical clarification (do not ignore)

**Keyboard / dark / blank camera screenshots are NOT the failing inputs.**

What actually happened on the phone:

1. Owner submitted **real dog photos** (camera or gallery).  
2. Detection / crop-confirm **failed** for most of those dog shots (~2 of 3; only one path reached a full result).  
3. After failure, the UI returned to the **live camera loop**, ready for another attempt.  
4. Screenshots of a dark frame or laptop keyboard were taken **in that reset state** — they show leftover error banners on an idle camera, **not** what was scanned.

| Treat as evidence | Ignore completely |
|-------------------|-------------------|
| Outdoor dog / face / snout crop screens | Dark camera after fail |
| “Nose crop ready” success (tight leather) | Keyboard / RGB backlight after fail |
| Loose blue boxes on real dogs | Any “junk reject worked” story from those frames |

**Do not** diagnose this session as “junk rejection is working.” That mixes post-fail UI with the real dog failures.

---

## 1. Executive verdict (corrected)

**Problem:** On **real dog images**, the field pipeline often fails to finish a usable nose crop. Roughly **1/3 succeeded**; the rest never reached a reliable “Nose crop ready” outcome.

**What the successful case was:** A tight / close nose-leather crop (last success image).

**What the failing cases were:** Real dogs — often whole body, face, or snout from phone distance/angle — where:

- Stage-2 nose YOLO frequently does **not** lock leather confidently, and/or  
- Assist crop box is **too loose** (fur, whiskers, muzzle, paw), and/or  
- After “Use this crop”, leather/likeness gates reject the crop → user sees failure then camera again.

**Goal of this plan:** Make **real dog photos** complete the path to crop-ready + search/register reliably, without false comfort from unrelated post-fail camera frames.

---

## 2. What the system does today

```
Real dog photo (camera shutter or gallery)
        │
        ▼
 detect-preview
   Stage-1: COCO dog → head ROI
   Stage-2: YOLO dog-nose on head
   If no dog: full-frame nose search
   If dog found but nose miss: do NOT full-frame (anti paw/shadow)
        │
        ├─ Strong YOLO + heuristics → detected=true + box
        └─ Weak / miss → detected=false + heuristic assist box (or hard fail msg)
        │
        ▼
 NoseCropEditor (user must tighten onto leather, confirm)
        │
        ▼
 prepare_nose_scan (likeness / leather / skin / re-detect)
        │
        ├─ PASS → “Nose crop ready” → embed → match/register
        └─ FAIL → error → UI returns to camera loop  ← keyboard screenshots happen HERE
```

### Models

| Stage | Role |
|-------|------|
| `dog_detector_coco.onnx` | Find dog / head |
| `nose_detector.onnx` | Find nose leather (weak on phone distance) |
| `nose_heuristics.py` | Assist box + post-confirm leather gates |
| `embedding_model.onnx` | Matching — **not** the observed failure |

### Already applied (Batch-1)

Two-stage detect · no full-frame after dog found · look-gate dog bypass · assist + edge penalty.

These help assist/honesty. They **do not** yet make typical phone dog shots auto-succeed.

---

## 3. Real evidence from this session

### A. Real dog attempts that did not fully succeed

Crop-editor screens on outdoor / held dogs show:

- Suggested or manual boxes often **not leather-only** (snout fur, whiskers, shadow, paw edge).  
- Detection path is partial: editor opens, but pipeline does not consistently finish to crop-ready.  
- Owner report: **only ~1/3** of real attempts produced a proper result.

### B. The success case

- Close-up / leather-dominant crop → **“Nose crop ready”**.  
- Proves embed path works **when leather fills the crop**.

### C. Explicit non-evidence

- Dark / keyboard frames after fail = **camera reset**, not test inputs.  
- Do not use them to claim “junk rejection validated this run.”

---

## 4. Root cause (focused)

| Layer | Issue on real dog photos |
|-------|---------------------------|
| Stage-2 YOLO | Trained mainly on tight lab noses; phone distance/angle/top-down → low conf / miss |
| Assist box | Often lands on snout band, not tight leather |
| Confirm gates | Correctly want leather; loose boxes fail → “no outcome” |
| UX after fail | Error may linger while camera reopens → confusing screenshots |
| Embed / DB | Not implicated when crop never becomes ready |

**Primary product bug for this session:** unreliable end-to-end success on **normal dog photos**, not “keyboard junk.”

---

## 5. Complete plan — make the system work on real dogs

### Phase 0 — Measure only real dog failures (Day 1)

| # | Task | Done when |
|---|------|-----------|
| 0.1 | Save **the actual dog JPEGs** that failed + the one that succeeded into `ml/data/phone_eval/` (not keyboard snaps) | ≥ the session’s real attempts on disk |
| 0.2 | Run `scripts/eval_phone_detect.py` | Table: dog_conf, nose_conf, hint per file |
| 0.3 | Capture the **exact API error** when “Use this crop” fails on a dog photo | Gate reason string logged |
| 0.4 | Note per attempt: stopped at preview vs crop vs confirm | Clear failure stage map |

**Metric:** Every failed dog photo labeled as Stage-1 miss / Stage-2 miss / loose assist / likeness reject.

---

### Phase 1 — UX so dog failures are recoverable (2–3 days)

| # | Task | Why |
|---|------|-----|
| 1.1 | On crop: force clarity — **leather must fill the box** before confirm | Loose snout confirms are killing real dogs |
| 1.2 | Show **exact** backend reject reason after failed confirm | User knows to tighten, not “nothing happened” |
| 1.3 | Clear error banner when reopening camera after fail | Stops leftover “No dog nose” on empty preview (the confusion in screenshots 1/4) |
| 1.4 | Highlight **Tighten** when box is mostly fur | One-tap path toward leather |
| 1.5 | Soft client block if crop is obviously too large vs image | Fewer doomed confirms |

**Metric:** Same previously failing dog photo → crop-ready after one guided tighten ≥50% informal retests.

---

### Phase 2 — Fix detection on real phone dogs (1–2 weeks) — main fix

| # | Task | Detail |
|---|------|--------|
| 2.1 | Label **tight nose leather** on failed + new phone dog shots | Leather only, not whole muzzle |
| 2.2 | Hard negatives in train set | Paws, eyes, hands, pavement (keyboards OK as negatives, but not as “this session’s failure”) |
| 2.3 | Fine-tune Stage-2 from current nose weights | Keep Stage-1 unless Phase 0 shows dog miss |
| 2.4 | Export ONNX → promote only if phone_eval on **dog** set improves | Before/after table required |
| 2.5 | Live phone retest on the **same dogs** that failed | ≥2/3 → crop-ready without heroic luck |

**Metric:** Held-out phone dog set: Stage-2 hit or assist IoU≥0.5 vs leather GT on ≥70%; success rate on repeat field dogs ≥2/3 without changing junk-gate honesty.

---

### Phase 3 — Thresholds only with evidence

| # | Task | Rule |
|---|------|------|
| 3.1 | Review `NOSE_MIN_LIKENESS` / soft-miss | **Only after** labeled phone set + Phase 2; never first |
| 3.2 | In-camera “fill circle with leather” coaching | Reduce whole-body misuse |
| 3.3 | Extra Stage-1 (dog-face) | Only if Phase 0 proves COCO dog miss is common |

---

### Phase 4 — Gemini (optional advisor)

Upload [`GEMINI_CURRENT_STATUS_HANDOFF.md`](./GEMINI_CURRENT_STATUS_HANDOFF.md).

Ask for: train recipe, assist/threshold risks, UX priority.  
**Do not** ask Gemini to analyze keyboard screenshots as failed scans.

---

## 6. Priority order

```
1. Save REAL failed dog images + eval          ← truth
2. Clear post-fail error + crop tighten UX     ← stop confusion + recover attempts
3. Label + fine-tune Stage-2 on phone dogs     ← fix detection
4. Gemini on train recipe / thresholds         ← optional
5. Lower gates only with measured evidence     ← last
```

---

## 7. Acceptance — “no issues” for field dogs

- [ ] On typical outdoor dog / face / snout phone photos, user reaches **Nose crop ready** in **≥2 of 3** attempts (same bar owner used).  
- [ ] Assist or YOLO box lands on or next to leather; Tighten gets leather-fill in one step.  
- [ ] Failed confirm shows a **clear leather/tighten message**, then camera reopens **without** stale error on empty preview.  
- [ ] Macro leather close-ups still pass (no regression).  
- [ ] `eval_phone_detect.py` on the session’s dog files shows measurable Stage-2 / assist improvement after ONNX promote.  
- [ ] Staff still confirm matches.

Junk rejection remains a separate safety check — **not** the explanation for this session’s failures.

---

## 8. File map

| Concern | Path |
|---------|------|
| Two-stage detect | `backend/app/services/nose_detector.py` |
| Dog Stage-1 | `backend/app/services/dog_detector.py` |
| Assist + leather gates | `backend/app/services/nose_heuristics.py` |
| Confirm gate | `backend/app/services/capture_pipeline.py` |
| Preview / messages | `backend/app/routers/matching.py` |
| Thresholds | `backend/app/config.py` |
| Crop UI / error linger | `frontend/` NoseCropEditor + identify capture flow |
| Phone eval | `scripts/eval_phone_detect.py` → `ml/data/phone_eval/` |

---

## 9. One-sentence summary

**Real dog photos are failing most of the time because Stage-2 + loose crops don’t produce leather-ready prints; keyboard/dark shots were only the post-fail camera loop — ignore them, measure the dog failures, fix UX clear/tighten, then fine-tune Stage-2 until ≥2/3 real dog attempts succeed.**

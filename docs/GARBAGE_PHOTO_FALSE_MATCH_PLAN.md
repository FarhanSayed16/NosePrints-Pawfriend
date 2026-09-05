# Garbage Photos & False Matches — Issue Analysis & Fix Plan

**Status:** Remediation plan for senior review  
**Date:** 5 September 2026  
**Audience:** Intern, mentor, PawFriend technical lead  
**Related:** [`ACCURACY.md`](./ACCURACY.md) · [`MASTER_PLAN.md`](./MASTER_PLAN.md) · [`PHASE_A_DEPLOYMENT.md`](./PHASE_A_DEPLOYMENT.md) · [`G0_G3_AUDIT_FIXES.md`](./G0_G3_AUDIT_FIXES.md) (post-implementation audit)

---

## 1. What the senior observed (reproduced)

| Observation | Example from testing |
|-------------|----------------------|
| Can upload **non-dog** images as “nose prints” | Laptop keyboard saved as nose crops; registration of “Jack” completes with 3 keyboard crops |
| Identify returns a **dog profile** for garbage | Keyboard scan → “Likely match” **72.7%** to Jack (also registered with keyboard) |
| Low similarity still looks like a real hit | Candidate shown with **7.5%** and “REGISTERED” badge |
| Full-dog photo can also be garbage | Earbud stored as Jack’s profile “look” photo |

**Senior’s conclusion is correct:** today the product does not reliably enforce “this must be a dog nose” before storing or matching, and the UI can look like a confident ID even when it should not.

---

## 2. Root causes (technical)

There are **three separate bugs / design gaps**, not one.

### Cause A — Client crop bypass (`pre_cropped=true`) — **FIXED (G0.1)**

**Historical bug (before G0):**

1. User picks any photo → crop editor → confirms box.  
2. Frontend sends `preCropped=true`.  
3. Backend ran YOLO; **if no nose was found** and `pre_cropped` was true → **used the whole image anyway**.

**Current behavior:** `prepare_nose_scan()` always requires a detector hit at ≥ `DETECTOR_MIN_ACCEPT_CONF`. Client crop is a hint only (skips *frame coverage* when re-detect is on). There is **no** full-image fallback. See [`CAPTURE_UX.md`](./CAPTURE_UX.md) and [`G0_G3_AUDIT_FIXES.md`](./G0_G3_AUDIT_FIXES.md).

```text
File: backend/app/services/capture_pipeline.py
```

Sharp keyboards can still pass blur checks if YOLO falsely fires — that is why G1 heuristics exist.

### Cause B — Embeddings match similar garbage to similar garbage

The embedding model answers: “how similar are these two textures?”  
It does **not** answer: “is this a dog nose?”

If Jack was registered with keyboard photos, and you identify with another keyboard photo:

- Cosine similarity can be high (e.g. **0.73**).  
- Our thresholds treat ≥ **0.56** as **likely** and ≥ **0.51** as **possible**.  
- So the API correctly says “likely match” for wrong content — the gallery itself is polluted.

**Garbage in → garbage out.** Thresholds cannot fix a polluted gallery alone.

### Cause C — UI presents nearest neighbors like confident IDs

- Backend always returns up to **top_k** candidates from pgvector (nearest dogs), then sets `match_found` from thresholds.
- Identify UI shows a green **“Likely / Possible match”** banner and full dog cards whenever `match_found` is true.
- Even below-threshold scores can appear as **#2 / #3** under a match that passed on #1.
- **“REGISTERED”** is the dog’s *status badge* (lost/registered/found), **not** “AI confirmed this is the dog.” That wording confuses seniors and users.
- Owner contact is correctly held — but the screen still *looks* like a successful ID.

Also: a **7.5%** row should never feel like a hit. If `match_found` is false, UI should be **No match** only (no dog cards). If an old build still shows cards below threshold, that is a UI bug to close.

---

## 3. What is *not* the issue

| Misconception | Reality |
|---------------|---------|
| “Matching is broken because 72% on keyboards” | Matching is doing cosine on whatever embeddings were stored; keyboards look alike to the model |
| “We need 99% accuracy first” | We need **input gates** first; lab accuracy does not stop garbage uploads |
| “Staff confirm alone is enough” | Staff confirm protects phone numbers; it does **not** stop a bad demo that shows “Likely match” on junk |

---

## 4. Fix goals (Definition of Done)

After this work, seniors should be able to try the same keyboard test and see:

1. **Register:** keyboard / earbud / blank wall → **rejected** with a clear message (cannot save as nose print).  
2. **Identify:** garbage photo → **No match** (or hard reject before search), **no** dog name cards.  
3. **Identify:** real nose below `T_low` (0.51) → **No match**, offer found intake — **no** “Likely match” banner.  
4. **Identify:** score ≥ threshold → show candidates, but copy says **“AI suggestion — staff must confirm”**, not “this is the dog.”  
5. Optional look photo: reject obvious non-animal if easy; at minimum require user confirmation and never treat look as biometric.  
6. Existing polluted test dogs (Jack + keyboard) can be **deleted** or flagged so demos are clean.

---

## 5. Remediation plan (ordered)

### Phase G0 — Stop the bleeding (1–2 days) 🔒 ✅ in progress / implemented in code

**Goal:** Garbage cannot enter the gallery; low scores cannot look like hits.

| # | Work item | Status |
|---|-----------|--------|
| G0.1 | Never accept “no nose” when `pre_cropped=true` | **Done** — full-frame fallback removed |
| G0.2 | Min detector accept confidence (`DETECTOR_MIN_ACCEPT_CONF=0.40`) | **Done** |
| G0.3 | Identify UI gate on `match_found` + band | **Done** |
| G0.4 | Hide sub-threshold candidates (API + UI) | **Done** |
| G0.5 | Honest copy / badge (“In registry”, suggestion-only) | **Done** |
| G0.6 | Clean demo data | **Done** — Staff → Registry cleanup delete dogs |

**Exit:** Keyboard register → 422. Keyboard identify → No match (or 422). Real low score → No match.

---

### Phase G1 — Stronger “is this a nose?” gate (3–5 days) 🎯 ✅ implemented

**Goal:** Detector + crop quality actually filter field junk.

| # | Work item | Status |
|---|-----------|--------|
| G1.1 | Re-detect on confirmed crop (`NOSE_REDETECT_ON_CROP`) | **Done** |
| G1.2 | Coverage + aspect / edge / grid heuristics | **Done** (`nose_heuristics.py`) |
| G1.3 | Shared `prepare_nose_scan` before embed/match | **Done** (register + identify) |
| G1.4 | Classical nose-likeness + blank/flat reject | **Done** |
| G1.5 | Synthetic fixtures + tests | **Done** (`tests/fixtures/`, `test_g1_nose_gate.py`) |

**Exit:** Automated tests block keyboard/blank; nose-like fixture passes heuristics.

---

### Phase G2 — Matching honesty (2–3 days) 🧠 ✅ implemented

**Goal:** Open-set behavior matches product story.

| # | Work item | Status |
|---|-----------|--------|
| G2.1 | Empty candidates when `match_found=false` | **Done** (G0 + confirmed) |
| G2.2 | `MATCH_STRICT_DEMO` + `MATCH_THRESHOLD_STRICT` | **Done** |
| G2.3 | Staff queue: likely-only when strict / `MATCH_QUEUE_LIKELY_ONLY` | **Done** |
| G2.4 | Document in [`ACCURACY.md`](./ACCURACY.md) | **Done** |

**Exit:** API contract matches UI; seniors cannot get a named dog under threshold (or under strict demo threshold).

**Enable for senior demos** (in `backend/.env`):

```env
MATCH_STRICT_DEMO=true
MATCH_THRESHOLD_STRICT=0.60
```

Restart uvicorn after changing env.

---

### Phase G3 — Look photo + registration hygiene (1–2 days) ✨ ✅ implemented

| # | Work item | Detail | Status |
|---|-----------|--------|--------|
| G3.1 | Look upload soft gate | `look_gate.py` + `POST /dogs/look-check`; profile-photo `force` override; UI “Are you sure? / Use anyway” | **Done** |
| G3.2 | Breed/color or explicit Unknown | Backend normalizes blanks → `Unknown`; Register requires text or Unknown chip | **Done** |
| G3.3 | Staff delete / purge | Staff → **Registry cleanup** lists dogs and deletes (nose prints + photos) | **Done** |

---

### Phase G4 — Longer-term (after pilot) 

- Fine-tune detector on **reject** examples (phones, keyboards, hands).  
- Fine-tune embedder on ≥50 real PawFriend dogs.  
- Consider open-set / “none of the above” calibration beyond simple cosine thresholds.  
- Liveness / multi-frame capture (stretch).

---

## 6. Suggested implementation order (this week)

```text
Day 1   G0.1 + G0.2 + G0.6     Backend reject + delete junk dogs
Day 1–2 G0.3 + G0.4 + G0.5     Identify UI honesty
Day 2–3 G1.1 + G1.5            Re-detect on crop + fixture tests
Day 3–4 G2.1 + G2.2            API empty candidates + optional strict demo
Day 4–5 G3.*                   Look hygiene + staff delete
        Senior retest script   Section 8 below
```

---

## 7. Acceptance test script (for senior)

Run on phone over HTTPS after deploy/rebuild.

| # | Action | Expected |
|---|--------|----------|
| 1 | Register → Nose → upload **keyboard** → confirm crop | **Rejected** — “No dog nose detected” (or equivalent) |
| 2 | Register → Nose → upload **real nose** close-up → confirm | Accepted; can save 3 prints |
| 3 | Identify → **keyboard** | **No match** — no dog name, no “Likely match” |
| 4 | Identify → **real nose of unregistered dog** | **No match** (or possible only if score ≥ T_low) |
| 5 | Identify → **real nose of registered dog** (good light) | Suggestion ≥ threshold; copy says staff must confirm; **no phone number** |
| 6 | If any candidate shown | Score ≥ **51%** (T_low); no 7% rows |

If any row fails, Phase G0/G1 is not done.

---

## 8. Communication rules (after G0+G1)

**Allowed:**  
“Client-side crop used to skip the nose detector; that bypass is closed. We also reject junk with heuristics, empty below-threshold candidates, and soft-warn look photos. Purge any polluted demo dogs before showing seniors.”

**Forbidden:**  
“The AI identified the keyboard as Jack.”  
“We’re 99% accurate.”  
“It’s just a UI bug” (it was **backend gate + gallery pollution + UI**).

If a demo still shows a keyboard match, the gallery is polluted — use Staff → Registry cleanup.

---

## 9. Effort & risk

| Item | Estimate |
|------|----------|
| G0 (bleed stop) | **1–2 days** |
| G1 (stronger gate) | **3–5 days** |
| G2 (API honesty) | **2–3 days** |
| G3 (hygiene) | **1–2 days** |
| **Total to senior-safe demo** | **~1–1.5 weeks** calendar |

| Risk | Mitigation |
|------|------------|
| Stricter detector rejects some real street photos | Tune conf on 20 real phone noses; keep staff override later if needed |
| Existing junk dogs still match each other | Delete / purge before demo (G0.6) |
| Users frustrated by more rejects | Clear error copy + tips (already partially in `NO_NOSE_DETAIL`) |

---

## 10. Decision needed from seniors

1. Approve **G0+G1** as blocking before any external PawFriend demo.  
2. Prefer **strict demo mode** (higher threshold / no “possible” band) for public links? **Yes / No**.  
3. OK to **wipe polluted test registrations** on the current Supabase project? **Yes / No**.

---

## 11. Sign-off blurb

> G0–G3 close the original `pre_cropped` full-frame bypass, add nose heuristics, empty below-threshold candidates (API `top_score=0` on no-match), soft-warn look photos on register and identify, gate found-intake embeds, and give staff registry purge. Remaining demo risk is mainly **polluted gallery data** and **stale frontend builds**. Run Staff cleanup + rebuild tunnel, then execute §7 acceptance on phone HTTPS.

See also [`G0_G3_AUDIT_FIXES.md`](./G0_G3_AUDIT_FIXES.md).

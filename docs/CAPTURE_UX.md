# Capture UX — phone overflow, crop, Look step, image accept

**Date:** 18 August 2026  
**Status:** Plan for the phone registration bugs seen on `noseprints.farhanbuilds.in`  
**Scope:** Register Look + Nose steps, Identify appearance photo, quality gate. Not a new biometric.

If this file conflicts with `docs/MASTER_PLAN.md` on identity rules, follow the master plan. Coat/body photos stay a staff check, not a second biometric.

---

## What went wrong (from the phone screenshots)

| # | What you saw | Cause |
|---|---|---|
| 1 | Page “goes outside”; footer has a white strip on the right; crop buttons sit off to one side | Mobile `.btn-lg { width: 100% }` inside a **row** of Back / Skip / Next. Buttons also use `white-space: nowrap`. Crop overlay used a `9999px` box-shadow that paints past the viewport. |
| 2 | Crop box will not tighten onto the nose leather | Corner handles bubble `pointerdown` to the box, which **starts a move drag instead of resize**. Handles are 18px (too small for thumbs). No edge handles. |
| 3 | “All photos failed quality check” after a crop that still included eyes/snout | (a) Generic error hid the real API reason. (b) Canvas `Blob` often has **no filename / MIME**, so FastAPI can reject the file before quality. (c) After you crop, the API runs YOLO **again** and demands the nose fill ≥15% of *that* image — a face-wide crop fails coverage. (d) Laplacian ≥ 100 is harsh on phone JPEGs of a cropped street photo. |
| 4 | Look step only opens the camera | `capture="environment"` on the file input. Android Chrome then **skips the gallery**. |

---

## Plan (execute in this order)

### 1. Contain the page on a phone

- `#root` / `.page`: `max-width: 100%`, `overflow-x: clip`, `min-width: 0`.
- `.form-actions`: wrap; on ≤768px stack full-width buttons (allow wrapping text).
- Do not force `.btn-lg { width: 100% }` when it sits next to other buttons in a row.
- Crop dimming: four inset panels, **not** a 9999px shadow.
- Extra bottom padding so the Install banner does not cover actions.
- Crop action buttons: full width, stacked on small screens.

### 2. Make the crop box actually adjustable

- `stopPropagation` on every handle so resize ≠ move.
- Eight handles (corners + edges), ~44px touch targets.
- Shrink / grow buttons for people who cannot drag.
- Live preview of the cropped nose.
- Warn if the crop is under ~160px — that print will never pass quality.
- Copy: box should cover **nose leather only**, with a little muzzle — not eyes or the whole head.

### 3. Look step: camera **and** gallery

- Two explicit controls, no `capture` on the gallery input.
- **Take photo** → `capture="environment"`.
- **Choose from gallery** → `accept="image/*"` only.
- Same pattern on Identify’s optional full-dog photo.
- Show a preview after either path.

### 4. Accept usable images; still reject mush

Keep a quality gate (master plan). Change *how* we fail, not “accept anything”.

**Client**

- Convert picks (including HEIC when the browser can decode them) to a named `File` `image/jpeg`.
- Send `pre_cropped=true` after the crop editor.
- Show the API `message`, `issues`, and `suggestions` — never a single generic line.
- If some of 3–5 prints succeed, keep going; list which ones failed.

**Server**

- Sniff JPEG/PNG/WebP magic bytes when MIME is empty, `image/jpg`, or `octet-stream`.
- `pre_cropped=true`: skip **coverage** (the user already framed the nose). If YOLO misses, use the whole uploaded crop.
- Still check sharpness + brightness on the nose region.
- Field sharpness floor **70** (was 100). Coverage **15%** stays for live camera frames that are not pre-cropped.

### 5. Ship it through the Cloudflare tunnel

`npm run tunnel` serves **`dist/`**. After these edits, rebuild and restart preview or the phone will still show the old UI.

---

## Done when

- Look step shows **Take photo** and **Choose from gallery**.
- Crop handles resize on a thumb; shrink/grow works; page does not scroll sideways.
- A tight nose crop from the gallery can register; a blurry whole-dog zoom still gets a **specific** error, not “all photos failed”.
- Identify uses the same Look + crop behaviour.

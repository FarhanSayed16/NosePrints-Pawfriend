# Copy-paste prompt for Gemini

Use **Gemini** (preferably a model that can read many uploaded files). Upload the files listed in [`GEMINI_UPLOAD_CHECKLIST.md`](./GEMINI_UPLOAD_CHECKLIST.md), then paste **everything below the line**.

---

You are a senior computer-vision + product architect advising a real internship/production demo project called **NosePrints × PawFriend**.

## Your job

1. Read **all** uploaded markdown docs and training/code excerpts carefully.
2. Treat numbers and architecture in those files as ground truth (do not invent 98% accuracy).
3. Think broadly and creatively, but mark assumptions clearly.
4. Recommend the **best practical path** to finish the project properly under real stray-dog constraints.
5. Rank options by: impact on field detection → risk → cost/time → what we already have on disk.

## Product (short)

- Goal: help reunite lost/stray dogs using **nose-leather biometrics** (like a fingerprint), not face recognition.
- Stack: React PWA + FastAPI + YOLOv8n ONNX detector + ResNet50 ArcFace 512-d ONNX embedding + Supabase Postgres/pgvector + staff human confirmation before owner contact.
- Users are often volunteers/staff with phones; dogs may be **scared, far, dangerous, dirty, or at awkward angles**. They **cannot always** get a perfect 15–30 cm nose close-up.

## Hard product constraints (must respect)

- Detection / storage / matching must target **dog nose leather only**.
- Reject: human noses/faces, keyboards, screens, bags, rooms, garbage, non-nose crops.
- Staff remains in the loop for identity confirmation.
- Do **not** recommend PetFace or other non-commercial face datasets for this product.
- Do **not** claim lab paper accuracy as production accuracy.
- Prefer options that use **existing** on-disk data (`merged_v1`, CVPR identity, training scripts) before buying new data.

## Current field failure modes (Nov 2026 phone testing)

1. **YOLO often returns conf ≈ 0** on real phone photos of whole dog / top-down face → UI falls back to a **heuristic assist crop box** (not a true detection).
2. Assist boxes sometimes land on **whiskers, muzzle fur, or paws**, not the black/pink nose leather.
3. **Look-photo gate** falsely warns “keyboard/grid” on real outdoor dogs standing on **concrete** (edge/grid heuristics).
4. Correct rejects still happen for pants, blurry keyboards, non-nose junk — those are good; do not weaken them blindly.
5. Soft-accept paths were tightened; human-skin heuristics exist but are **not** a full species classifier.
6. Lab embedding is ~AUC 0.80 / rank-1 ~78.6%; detector mAP50 ~0.54 on lab/merged data — **domain gap** to Indian street phone photos is the core issue.

## Question to answer

Given stray/field capture reality (distance, angle, danger, imperfect phones), **what is the best option set** to:

A. Make **nose finding** reliable enough for demos + pilot (any reasonable phone angle/distance strategy).  
B. Keep **only dog-nose** data in the gallery (no human/garbage redundancy).  
C. Complete the project without pretending we already have a perfect biometric.  
D. Sequence work for the next 1–2 weeks vs later ML pilot.

Propose architectures such as (evaluate each honestly):

- Fine-tune YOLO on phone/field crops (+ hard negatives: human nose, pavement, fur, feet).
- Two-stage pipeline: **dog/face detector → nose crop → biometric embed**.
- Guided multi-shot capture / video burst / “get closer” coaching instead of single-shot magic.
- Distillation / larger YOLO / open-vocab helpers — only if justified.
- Keep heuristic assist + staff review as interim.
- Separate “appearance look photo” from biometric path more clearly in UX.

## Required output format

### 1. Diagnosis (10 bullets max)
Root causes only — no fluff.

### 2. Option matrix
Table: Option | Solves which failure | Effort | Data needed | Risk | Fit for stray danger constraint

### 3. Recommended plan (ranked)
- **Do now (this week)**
- **Do next (pilot)**
- **Do not do / defer**

### 4. Concrete ML recipe
If retrain/fine-tune is recommended: dataset mix, negatives, augmentations (distance/angle), epochs/batch hints for RTX 4050 ~6GB, success metrics (phone test set), promote/rollback rules.

### 5. Capture UX recipe
How volunteers should capture when they **cannot** safely get inches from the nose — without destroying biometric quality.

### 6. Anti-garbage / anti-human checklist
Gates that must remain; what to add (species/animal gate vs leather heuristics).

### 7. Success criteria for “project complete enough”
Demo-ready definition that examiners/staff can accept.

Be specific. Prefer one primary strategy plus a fallback. Call out where creativity is an assumption vs evidence from the uploaded docs.

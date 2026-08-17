# PawFriend Dog Nose Print Biometric ID — Project Plan

A lightweight, web-integrated system for identifying dogs by their nose prints (a biometric analogous to human fingerprints), built to help PawFriend reunite lost dogs with owners and register found strays.

---

## 1. Feasibility check — is this real?

**Nose prints: yes, well-validated.**
The idea that a dog's nose print is unique — like a human fingerprint — is not just folklore. Peer-reviewed research (Bae et al., Yonsei University, published in IEEE Access) built a CNN-based Siamese network called DNNet specifically for this task and reported an average rank-1 identification accuracy of about 98.97% across multiple datasets. A follow-up 2023 study using a nose-print masking technique reported top-1/top-2/top-3 recognition rates of roughly 94.93% / 97.10% / 97.10%, while noting accuracy drops with poor-quality images.

This is also a shipped consumer product already: the South Korean startup **Petnow** trained its model on roughly 200,000 dog and cat snout images and claims accuracy in the 98–99.9% range in its own materials. It won Best of Innovation at CES 2022 and originally published its methodology in IEEE Access in 2021. In other words — this is a proven, buildable idea, not a stretch goal.

**Retina scanning: real technology, but not practical here — recommend dropping for v1.**
Retina scanning images the blood-vessel pattern at the back of the eye using an infrared beam. It's extremely accurate, but even in humans it's rarely used outside high-security facilities (military bases, power plants) because of the cost of the equipment and the need to shine light directly into the eye while the subject stays still and cooperative. That combination — specialized hardware, controlled lighting, a calm and stationary subject — is the opposite of "lightweight app anyone can use on a random street dog with their phone." Recommendation: build nose-print ID as the core product; mention iris/retinal recognition only as a documented future-research direction (there is prior work on iris recognition for other animals, e.g. racing pigeons), not something to build now.

**Honest accuracy caveat:** the ~98–99% figures above are lab-condition numbers on curated datasets. Real-world accuracy with muddy, moving street dogs photographed by random people will be lower. Design the system so a PawFriend staff member always confirms a match before any contact information is shared — never auto-resolve a match.

---

## 2. Recommended approach

Build this as a **PWA (progressive web app)** integrated directly into pawfriend.in, using the browser's camera API (`getUserMedia`) rather than a native mobile app. This means:
- No install required — critical for "a stranger just found a stray dog on the street and needs to check right now."
- One codebase, integrates directly with the existing website as requested.
- A native app can be a later phase once there's real traction — don't build it first.

---

## 3. System architecture

```
Camera capture (PWA)              — owner registers, or finder scans a stray
        |
        v
Backend API                       — auth, validation, routing
        |
        v
ML pipeline                       — detect nose → check image quality → extract embedding
        |
   -----+-----
   |         |
   v         v
Save profile        Vector similarity search
(Postgres +          (compares embedding
 photo storage)       against the database)
[registration              |
 flow ends here]           v
                    Match decision
                    (notify owner via NGO staff,
                     or flag as newly found dog
                     if no match)
```

Two flows share the same pipeline:
- **Register** — a new dog's embedding is generated and stored.
- **Identify** — a scanned dog's embedding is compared against all stored embeddings; a strong match surfaces a candidate owner, and no match creates a new "found dog" listing.

---

## 4. The AI/ML layer — how "rectifying" a dog actually works

There are two fundamentally different problems here, and mixing them up is the most common mistake in this kind of system:

- **Verification (1:1):** "Is this photo the same dog as this specific profile?" — easy, high accuracy.
- **Identification (1:N, open-set):** "Which dog in our entire database — if any — is this?" — this is what PawFriend actually needs, and it's harder, because the correct answer might be "none of them, this dog isn't registered at all."

### Runtime matching flow

1. New photo comes in → nose detection + image quality gate → embedding vector generated (e.g. 512 numbers).
2. That vector is compared against **every stored embedding** using cosine similarity (or Euclidean distance) — producing a similarity score between 0 and 1 for each dog in the database.
3. Sort by score, take the top few candidates.
4. **Threshold decision:** if the best score clears a chosen cutoff (e.g. 0.85), it's shown as a likely match. If nothing clears the threshold, the system reports "no match — possibly unregistered."
5. **Human confirmation, always.** The match is shown to a PawFriend staff member with the candidate photo side-by-side, not auto-resolved. They confirm before any owner contact info is released — this is the main defense against both false positives (privacy risk of revealing the wrong owner's number) and real-world accuracy being lower than lab numbers.

The threshold isn't guessed — it's tuned using an ROC curve (see Section 7 below), because there's a direct trade-off: a loose threshold catches more real matches but also produces more false matches, and a strict threshold does the opposite.

### Model pipeline

1. **Nose/face detection** — a lightweight object detector (fine-tuned YOLOv8-nano, or a MediaPipe-style model) localizes and crops the nose region, removing backgrounds, hands, and clutter automatically.

2. **Image quality gating** — before accepting a scan, check:
   - Sharpness (Laplacian variance — a standard, cheap blur-detection method used in the published research itself)
   - Brightness/exposure
   - Distance/framing (nose fills enough of the frame)
   
   Auto-retry with on-screen guidance ("move closer," "hold steady") rather than relying on the user to tap the shutter at the right moment.

3. **Feature extraction (the actual "print")** — a Siamese or triplet-loss CNN, not a plain classifier. The model learns to output an embedding vector such that two photos of the *same* dog's nose land close together in vector space, and different dogs land far apart. Same family of technique as FaceNet for human face recognition — and it's the right choice because it doesn't need retraining every time a new dog is registered.

4. **Matching** — store every dog's embedding in a vector index; for a new scan, generate its embedding and run a nearest-neighbor / cosine-similarity search.

---

## 5. Which models to actually use, and why

**Step 1 — nose detector.** Fine-tune YOLOv8-nano on a nose-bounding-box dataset. This step doesn't need per-dog identity labels, just "here's where the nose is," so it's cheap to bootstrap — free annotated sets exist on Kaggle for exactly this purpose (see Section 8).

**Step 2 — the embedding/recognition model.** This is the hard part. What's actually been proven to work in published research on this exact task:
- **Backbone:** ResNet50, pretrained on ImageNet, fine-tuned. This is what the original 2021 Yonsei paper used, and it remains a strong, well-supported choice with lots of tooling. A lighter MobileNetV3/EfficientNet-lite backbone is worth considering later for faster on-device inference, but start with ResNet50 for accuracy while validating the approach.
- **Loss function:** don't rely on plain triplet loss alone if you can help it. The strongest published results on this exact task (the CVPR 2022 Pet Biometric Challenge, run on a dataset from Ant Group) came from combining **cross-entropy + triplet loss + pairwise circle loss** during training, with heavy offline data augmentation to compensate for having only a few images per dog — exactly the situation PawFriend will start in. A simpler and still solid starting point is **triplet loss alone**, or an **ArcFace-style additive angular margin loss** (the current standard in human face recognition) — both are well documented with off-the-shelf PyTorch implementations. Start simple, measure, then add complexity only if the numbers demand it.
- **Realistic expectation:** the actual CVPR 2022 challenge winners scored **86.67% AUC** on a genuinely blind test set — worth remembering next to the ~98–99% figures companies advertise, which come from friendlier, curated conditions. Calibrate your own targets accordingly.

---

## 6. How the data is stored

Three separate stores, each holding a different kind of thing:

**PostgreSQL — structured records**
```
owners        (id, name, phone, email, address, consent_given_at)
dogs          (id, owner_id, name, breed, color, sex, approx_dob,
               microchip_id [optional], status [registered/lost/found], created_at)
nose_prints   (id, dog_id, embedding vector(512),  -- pgvector column
               image_url, quality_score, captured_at, is_primary)
```

Deliberate choices:
- **Store multiple embeddings per dog, not just one.** Nose print matching is sensitive to angle and lighting, so keep 3–5 embeddings per dog (from different registration photos) and match against all of them, taking the best score. This meaningfully improves real-world recall over relying on a single "canonical" embedding.
- **Never store raw image files in the database.** Photos go to object storage (S3-compatible); Postgres only holds the URL/path. The embedding vector is the only biometric data in the hot-path database, and it's a one-way derived representation — not reversible into a photo, unlike the photo itself.
- Once past a few thousand embeddings, add a `pgvector` approximate-nearest-neighbor index (HNSW or IVFFlat) so similarity search stays fast — brute-force cosine comparison works fine at hundreds of dogs but not much beyond that.

**Object storage — the actual photos**, referenced by URL from the `nose_prints` table.

**Compliance note (India-specific):** owner phone numbers, addresses, and pet photos count as personal data under India's Digital Personal Data Protection Act (DPDP Act, 2023). Get explicit consent at registration, store only what's needed, and support deleting a person's data on request — build this in from day one rather than retrofitting later.

---

## 7. How to measure and improve accuracy

1. Build a validation set of **positive pairs** (two photos, same dog) and **negative pairs** (two photos, different dogs).
2. Run every pair through the model to get a similarity score for each.
3. Plot an **ROC curve** — showing, at every possible threshold, the trade-off between:
   - **False Accept Rate (FAR):** wrongly saying two different dogs are the same one — the privacy risk (wrong owner contacted).
   - **False Reject Rate (FRR):** wrongly saying the same dog is two different ones — a real match gets missed.
4. Pick a production threshold deliberately based on which failure mode matters more — given the privacy angle, err toward a stricter threshold (lower FAR) and lean on the human-review step to recover missed matches.
5. Report **AUC** (area under the ROC curve) as the headline accuracy number — it's the standard metric in every paper cited in this document, so it's directly comparable to published results, and more honest than a single "accuracy %" that depends on which threshold was picked.

---

## 8. Where the training data actually comes from

This is the question that usually kills projects like this, so here's a concrete list rather than a vague "collect data":

| Source | Size | Good for | Access |
|---|---|---|---|
| CVPR 2022 Pet Biometric Challenge (Ant Group) | ~6,000 dogs, 20,000 nose-print images + labeled pos/neg pairs | Pretraining the embedding model | Originally released for the competition; check current availability with the workshop organizers — several papers note the original download is no longer live, but the winning teams' training code is public on GitHub (`muzishen/Pet-ReID-IMAG`, `wkrcarry/Pet_Biometric_Challenge`), valuable even without their exact data |
| Nexdata commercial dataset | 64,378 images, 1,073 dogs, indoor/outdoor, multiple breeds, segmentation-annotated | A serious pretraining set if budget allows | Paid (nexdata.ai); a small free sample subset exists on Kaggle/GitHub for prototyping only |
| Kaggle nose-detection sets | Few hundred bounding-box-annotated images | Training the Step 1 detector | Free |
| images.cv dog nose set | 361 annotated images | Same — detector bootstrapping | Free |
| PawFriend's own registrations | Grows over time | Fine-tuning the embedding model to real deployment conditions (Indian street dogs, phone cameras, real lighting) | Yours — the most important one long-term |

**Practical strategy:** pretrain or fine-tune the embedding model's early layers using a public dataset (Nexdata's free sample plus whatever training code can be run from the CVPR challenge repos) to learn general "what does nose-print texture look like" features, then fine-tune the final layers specifically on PawFriend's own collected dogs. You are not training a nose-print recognizer from zero on a few hundred of your own photos — that would badly underperform. You're specializing an already-competent model to your specific population and conditions, which is realistic within an internship timeframe.

---

## 9. Suggested tech stack

| Layer | Suggestion | Why |
|---|---|---|
| Client | PWA — React/Next.js, `getUserMedia` for camera | No install, integrates directly into pawfriend.in |
| Backend API | FastAPI (Python) or Node.js | FastAPI keeps ML serving and API in one language |
| ML inference | PyTorch model exported to ONNX or TFLite | Fast, cheap inference — no GPU needed in production |
| Embeddings + relational data | PostgreSQL + `pgvector` extension | One database instead of a separate vector DB — simpler ops for a small team |
| Photo storage | S3-compatible object storage (Cloudflare R2, Backblaze B2) | Cheap, simple |
| Notifications | WhatsApp Business API / SMS / email | WhatsApp has the highest reach for this use case in India |
| Hosting | Render / Railway / a single small VPS | Avoid over-engineering infra for NGO-scale traffic |

---

## 10. User flows

**Registering a dog:** owner or NGO staff captures 3–5 nose photos + basic profile (name, breed, color, contact, optional microchip ID) → quality-checked → embedding generated and stored → profile saved.

**Reporting lost:** owner flags their dog as lost, optionally with last-seen location, boosting that dog's profile in matching results and optionally triggering a community alert.

**Identifying a found/stray dog:** anyone opens the "Identify a Dog" page → scans the nose → embedding generated → similarity search runs. On a strong match, route through PawFriend staff or an in-app contact-reveal step rather than exposing the owner's phone number directly. On no match, offer "list this dog as found," creating a new record and notifying staff — growing the database with every use, not just at registration time.

---

## 11. Phased roadmap (internship-realistic)

1. **Phase 1 — ship the skeleton fast:** registration + a searchable directory (breed, color, location). No ML yet — get something real in front of users quickly.
2. **Phase 2:** add nose/face detection + image quality gating.
3. **Phase 3:** add the embedding model (transfer learning) + `pgvector` similarity search — the core deliverable.
4. **Phase 4:** polish the capture UX (auto-capture on a sharp frame, guided overlay), add WhatsApp/SMS alerts.
5. **Phase 5 (stretch/future):** native app, partnership with municipal shelters or a microchip registry, and — only with real appetite — R&D into iris pattern recognition as a secondary biometric.

---

## 12. Positioning note

Don't pitch this as a *replacement* for microchipping — pitch it as a free, install-nothing complement. Most people who find a stray dog on the street have no microchip scanner, but almost all of them have a phone. That's the strongest and most honest case for why this matters.

# NosePrints × PawFriend — ML Dataset Research, Enhancement Plan & Cursor Handoff

**Research attribution:** Jagjit  
**Prepared for:** NosePrints × PawFriend engineering team  
**Research / review date:** 9 November 2026  
**Purpose:** Give Cursor AI the research findings, dataset links, technical recommendations, risks, and questions needed to decide whether and how to improve the existing NosePrints system.

> **How to use this file:** Open the NosePrints repository in Cursor, place this Markdown file in the repository root (or keep it accessible in the workspace), and send Cursor the short prompt in Section 1. Cursor must inspect the real repository before deciding what to implement. This document is research input, not permission to download, train, overwrite models, change thresholds, modify production data, or deploy anything automatically.

---

## 1. Short prompt to give Cursor AI

Copy this prompt into Cursor Chat/Agent after adding this file to the workspace:

```text
Read the entire file @NOSEPRINTS_ML_DATASET_RESEARCH_AND_CURSOR_HANDOFF.md.

This is the external dataset and ML-enhancement research compiled by Jagjit for our NosePrints × PawFriend project. First inspect our actual repository, current data, training scripts, model artifacts, evaluation code, and documentation. Compare the research against what we have already implemented.

Do NOT immediately download datasets, install packages, train models, edit production code, replace ONNX files, change thresholds, delete/wipe registry data, or deploy. Start with a read-only technical audit. Verify each dataset's current availability, actual annotations, identity labels, terms/licence, and fit for our two separate tasks: (1) YOLO nose localization and (2) dog nose-print identity embeddings.

Then give me a clear decision report: what is useful, what is not useful, what we already have, what should be improved, what can realistically improve accuracy/robustness, which dataset(s) you recommend, how to acquire them safely, what the implementation/training/evaluation plan should be, risks/cost/storage/GPU requirements, and exactly what information or approvals you need from me. Cite repository file paths and evidence. Separate verified facts from assumptions.

Do not claim a metric improvement until it is measured on a clean held-out evaluation set. Preserve the current working models and create a rollback plan. Ask for my approval before any data download, code change, training run, model export, threshold update, DB operation, or deployment. Your first response should be the audit and decision report only.
```

**Important:** If Cursor's workspace name or file reference differs, adjust `@NOSEPRINTS_ML_DATASET_RESEARCH_AND_CURSOR_HANDOFF.md` to the actual filename. Cursor should read all sections, not only the prompt.

---

## 2. Executive summary — what this research is telling us

NosePrints is a dog nose-print biometric identification system. The ML pipeline has two different data requirements, and they must not be confused:

1. **Nose localization / detection:** Find the dog's nose inside a full phone photograph. This task needs full dog-face/muzzle images with accurate nose bounding boxes, segmentation masks, or landmarks that can be converted into reviewed boxes.
2. **Nose-print identity recognition:** Decide whether two close-up nose-leather images belong to the same individual dog. This task needs genuinely close nose crops with reliable, repeatable `dog_id` labels and multiple captures of each dog.

A dataset containing thousands of ordinary dog photographs does not automatically help the identity-embedding model. A nose-keypoint dataset does not automatically provide a tight nose-leather crop. A folder of nose photographs without stable dog identities cannot train or properly evaluate an ArcFace/re-identification model.

### Initial recommendations

- **First:** Audit the benchmark already used by our current embedding model. Confirm exactly which CVPR/Pet Biometric Challenge mirror, files, labels, splits, and preprocessing are already present. Avoid downloading a duplicate.
- **Second:** Evaluate the paid Nexdata Dog Nose Print dataset as the strongest external nose-print-data lead. Do not purchase it until the vendor confirms per-dog identity labels, images per dog, session/capture variation, image quality, licence scope, and commercial model-training/deployment rights.
- **Third:** Build our own consented PawFriend pilot dataset. The existing project plan already targets at least 50 real dogs with approximately 5–10 good nose captures per dog. Prioritise different capture sessions, phones, angles, and lighting rather than near-identical burst frames.
- **Fourth:** Evaluate dog-pose/face datasets such as StanfordExtra, Animal-Pose, DogFLW, and the Zenodo pet-face dataset for detector/landmark assistance only, subject to image-rights review. These are not substitutes for the nose-print identity dataset.
- **Fifth:** Use the 2021 canine nose-pattern study and 2024 pet-biometric paper to inform capture design and image-quality checks, not as proof that our model will achieve the same results.
- **Do not change the production architecture or thresholds just because a dataset exists.** Run controlled experiments against our current baseline and keep staff confirmation in the workflow.

### Main expected benefit

The strongest likely gains are from cleaner and more representative data, improved nose crops, correct identity/session labels, hard-negative evaluation, open-set calibration, and consistent capture quality. A new backbone or more training epochs alone may not solve poor photographs, label errors, polluted registry data, or leakage between train and test splits.

---

## 3. Existing NosePrints project baseline — from the project status snapshot

The following is copied from the NosePrints project status document dated 9 November 2026. **Cursor must verify every item in the actual repository, model files, logs, and runtime configuration.** Do not assume this snapshot proves that the current workspace still has the exact same state.

### 3.1 Product purpose and workflow

NosePrints is an AI-powered dog nose-print biometric ID system built for PawFriend.in.

Current intended user flow:

| Flow | Intended behaviour |
|---|---|
| Register | Owner details, dog profile, optional full-body “look” photo, and 3–5 successful nose crops |
| Identify | Scan a found dog's nose; AI proposes candidate dogs; staff confirms before owner contact is revealed |
| Lost / found | Mark a dog lost; after no-match, allow found-dog intake/listing |
| Staff | Login, review match queue, confirm/reject, and clean registry records |

V1 scope described in the project status:

- Dog nose-print identification only; no retina/iris identification.
- Progressive Web App with browser camera, not a native app.
- Human-in-the-loop: AI suggests candidates; staff decides.
- It is a complement to microchips, not a microchip replacement.

### 3.2 Runtime ML flow

```text
Phone camera → JPEG upload
    → YOLOv8-nano: locate / crop nose (reject if no valid detection)
    → Quality checks + junk-photo heuristics
    → ResNet50 + ArcFace ONNX: 512-dimensional embedding
    → pgvector cosine search against stored nose embeddings
    → Likely / Possible / No-match bands
    → Staff confirmation
    → Owner contact shown only after staff confirmation
```

### 3.3 Reported existing model results

| Model | Reported artifact | Reported result in status snapshot |
|---|---|---|
| Nose detector | `backend/models/nose_detector.onnx` | YOLOv8n; validation mAP50 0.54, test mAP50 0.68; close-up recall approximately 70% with padding + retry |
| Nose embedding model | `backend/models/embedding_model.onnx` | ResNet50 + ArcFace; 512-d embeddings; gallery-probe rank-1 78.6%, AUC 0.80 on a CVPR 2022 mirror of approximately 6,000 dogs |

Reported current cosine bands (from the status snapshot):

| Band | Cosine similarity | Meaning |
|---|---:|---|
| Likely | ≥ 0.56 | Strong candidate; staff still confirms |
| Possible | 0.51–0.56 | Lower-confidence candidate; can be disabled with `MATCH_STRICT_DEMO=true` |
| No match | < 0.51 | Return no candidates and offer found-dog intake |

**Do not present these numbers as independently verified by this research.** Cursor must locate evaluation code, split files, metric logs, model hashes, and threshold config and establish whether the results can be reproduced. The existing project status explicitly says not to claim 98–99% accuracy or claim the CVPR solution's 86.67% AUC as our own result.

### 3.4 Reported application and data-quality work already implemented

The status snapshot says these are in the repository:

- React PWA: Register, Identify, Directory, Lost, Found intake, Staff.
- FastAPI + PostgreSQL/Supabase + pgvector.
- Staff JWT authentication; owner contact is staff-only.
- Explicit consent and privacy-safe identify responses.
- Nose upload → detect → quality gate → embedding → store.
- Identify → match bands → staff confirmation queue.
- Lost/found intake.
- Rate limits, health checks, combined registration.
- Camera/crop editor and look-photo soft warning.
- G0–G3 junk/false-match gates and follow-on heuristics.
- Shared `prepare_nose_scan`; no accepting the whole image when YOLO misses.
- Detector minimum confidence and client-crop re-detection.
- Heuristics for aspect ratio, edges, grid/keyboard patterns, colourfulness/hue/fabric, leather-centre appearance for dark or pink noses.
- Register requires at least three successful nose prints.

Cursor must inspect the implementation and tests to confirm these behaviours are present and still working.

### 3.5 Previously noted non-ML / pilot tasks

The project status snapshot also records the following outstanding work:

1. Purge junk dog registrations through Staff → Registry cleanup (only after reviewing backups and getting approval; do not wipe automatically).
2. Rebuild the Cloudflare tunnel after UI changes and hard-refresh the phone.
3. Run real-phone HTTPS acceptance tests: reject keyboard/junk, accept a real nose, soft-warn on look photos.
4. Decide whether to use strict demo mode; decide about optional DB wipe only after backup and explicit approval.
5. Phase 4 hosting: Cloud Run/durable R2 photos/`DEBUG=false`.
6. Closed pilot with real dogs and good captures.
7. Optional later work: WhatsApp notification and `id.pawfriend.in`.

These tasks are separate from the dataset research. More model training will not clean up a polluted gallery or repair a bad capture UX by itself.

---

## 4. Dataset taxonomy — choose data for the correct ML task

| Data category | What it contains | Helps which part? | Can it train nose-print identity directly? |
|---|---|---|---|
| Nose-print biometric images with dog IDs | Close-up nose leather images; several images per dog; stable identity labels | ResNet50/ArcFace/re-ID, genuine-vs-impostor evaluation | **Yes**, if quality, labels, and rights are suitable |
| Nose masks / segmentation | Nose-region polygon or pixel mask, potentially with dog ID | Crop refinement, segmentation, detector/quality preprocessing | Only if images also have reliable dog IDs and multiple samples per dog |
| Full dog images with nose boxes | Full face/muzzle image and nose rectangle | YOLO nose detector | **No**, not by itself |
| Dog face landmarks / nose keypoint | Nose point plus eyes/face/head landmarks | Nose localisation or crop proposals | **No**, not by itself |
| Dog face re-identification images | Repeated dog faces with dog IDs, but not nose crops | Auxiliary identity research / face-based baseline | Not for nose-print-specific embedding without actual nose crops |
| Dog-nose classification images without identity | Nose vs non-nose or one class called “dog nose” | Basic classifier/quality gate if labels support it | **No**; no dog-level identity supervision |
| Junk / negative images | Fabric, keyboard, screen, fur, other animals, blur, objects, non-nose regions | False-positive rejection and quality gate | No; useful for detector/classifier testing |

**Key rule:** Do not mix the above into one folder and call it a “nose dataset”. Keep source, task, labels, licence, and preprocessing provenance for every image.

---

## 5. Dataset findings and direct links

The links below are research leads. Cursor must re-check access and terms at the time of use. Where the licence is unclear, the dataset must remain blocked from training/deployment until rights are established.

### 5.1 Dedicated dog nose-print biometric datasets

#### A. CVPR 2022 Pet Biometric Challenge / dog nose-print benchmark

**Potential use:** Existing benchmark for dog nose-print re-identification and embedding evaluation. The project status says our current embedding model was evaluated on a CVPR 2022 mirror of approximately 6,000 dogs. A 2022 challenge paper describes the dog nose-print matching task and reports a competition result; a later research discussion describes the challenge dataset as approximately 6,000 dog identities and 20,000 nose-print images. Do not attribute other teams' scores to our implementation.

Links:

- [Kaggle — Pet Biometric Challenge](https://www.kaggle.com/datasets/zekunn/pet-biometric-challenge)
- [CVPR third-place solution — Pet-ReID-IMAG](https://github.com/muzishen/Pet-ReID-IMAG)
- [Additional implementation / training reference](https://github.com/dashengge/pet-biometrics)
- [DogNosePrintIdentification repository referencing the Kaggle dataset](https://github.com/liuhaoyutz/DogNosePrintIdentification)
- [Research paper — A Competitive Method for Dog Nose-print Re-identification](https://arxiv.org/abs/2205.15934)
- [Original challenge website referenced by the paper](https://www.vislab.ucr.edu/Biometrics2022/index.php)

**Important status and caution:**

- The Kaggle page is a candidate mirror, not a guarantee that the complete files, metadata, or licence are currently downloadable.
- The original challenge host may no longer provide the original dataset. The Kaggle route is referenced by third-party code; Cursor should test whether it is still available and inspect the actual archive before relying on it.
- Read the Kaggle dataset card and terms, identify original source/licence, and preserve attribution. Do not assume a GitHub repository's MIT licence covers the dataset images.
- Inspect the split structure. Determine whether the data includes train/validation/test images, per-image dog IDs, and the original gallery/probe or pair protocol.
- Confirm whether the local copy already exists in this repository. Do not download a second copy unnecessarily.
- If the mirror is missing, corrupted, incomplete, or legally unclear, do not scrape random Kaggle mirrors. Ask for a source/rights decision and prioritise PawFriend data or a properly licensed source.

**Research relevance:** The 2022 paper discusses class imbalance, few images per identity, augmentation, and metric-learning losses including cross-entropy, triplet and pair-wise circle loss. These are ideas for controlled experiments, not automatic instructions to replace our current ArcFace training objective.

#### B. Nexdata — Dog Nose Print Biometric Dataset

**Potential use:** Strongest commercial nose-print dataset lead identified in this research.

- [Official Nexdata dataset product page](https://www.nexdata.ai/datasets/computervision/1051)
- [Nexdata pet-biometric overview](https://www.nexdata.ai/company/news/727)

Published product-page description:

| Attribute | Vendor-published detail |
|---|---|
| Number of dogs | 1,073 |
| Images | 64,378 |
| Capture | Cellphone; images in JPG; videos in MP4/MOV |
| Content | Videos of dog heads and nose-print images |
| Conditions | Multiple lights; indoor/outdoor scenes are listed |
| Dog types | Examples include Teddy, Labrador, Shiba Inu |
| Annotation | Segmentation annotation on the dog's nose |
| Price | Paid dataset; vendor quote required |

**Critical purchasing questions:** The product page says multiple scenes are represented, but also notes that the collection scene of the same dog did not change. Do not infer that every dog has repeat captures across multiple environments or separate visits. Before purchase, obtain written answers to all of these:

1. Does every image/video carry a stable, consistent dog identity ID?
2. Are the 64,378 images distributed across 1,073 IDs, and what is the per-dog image-count distribution (minimum, median, maximum)?
3. Are images from different dates/sessions per dog, or mostly adjacent video frames from a single recording?
4. Are raw images and original videos provided, or only nose crops?
5. What is the distribution of nose-region pixel widths and image resolution? How many images have at least 384 pixels across the nose region?
6. Are segmentation masks supplied per image? Which format (PNG masks, polygons, COCO, etc.)?
7. Are there duplicate/near-duplicate frames and quality labels?
8. Are dog IDs reliable across all files? Is there a metadata CSV/JSON manifest?
9. Does the licence expressly permit training, fine-tuning, evaluation, and commercial deployment of a model trained on the dataset for PawFriend/NosePrints?
10. Can the resulting weights/ONNX model be deployed commercially? Are there restrictions on derivative models, storage, redistribution, or number of deployments?
11. Can a representative sample and complete schema be reviewed before payment?
12. What are the price, delivery format, support, refresh rights, and refund terms if labels do not meet the specification?

**Recommendation:** Request a small sample, schema, licence, and per-identity distribution before purchase. This dataset could be valuable, but the quality and identity/session structure matter more than the headline image count.

### 5.2 Dog datasets useful for nose localisation / detector work

These datasets can help locate a face, muzzle or nose point. They do not automatically provide a tight nose-leather box or an identity-labelled nose crop.

#### C. StanfordExtra

- [GitHub — StanfordExtra](https://github.com/benjiebob/StanfordExtra)
- [Stanford Dogs image source](http://vision.stanford.edu/aditya86/ImageNetDogs/)

Published details: approximately 12,000 labelled dog instances in the wild, with 2D keypoint and segmentation annotations. The repository says annotations are available after filling out a Google form; original image files are downloaded separately from Stanford Dogs.

**Use:** Investigate whether the nose keypoint and related landmarks can generate coarse nose crop proposals or help train an auxiliary landmark model. Cursor must inspect the annotation schema and map the exact nose keypoint field before attempting conversion.

**Rights caution:** The repository states its annotation package became MIT licensed on 2 November 2024. That does not automatically grant a commercial licence to every original Stanford Dogs/Flickr image. Verify the source image rights separately before commercial model training or redistribution.

#### D. Animal-Pose Dataset

- [Official project page and dataset description](https://sites.google.com/view/animal-pose/)
- [GitHub repository](https://github.com/noahcao/animal-pose-dataset)
- [Keypoint-labelled animal data — Google Drive](https://drive.google.com/drive/folders/1xxm6ZjfsDSmv6C9JvbgiGrmHktrUjV5x?usp=sharing)
- [Bounding-box-only animal data — Google Drive](https://drive.google.com/drive/folders/1-yOSGWts2ZDYFx29u7vPcX4CdGJkPx1w?usp=sharing)

Published details: 6,000+ labelled instances across 4,000+ images for dog, cat, cow, horse, and sheep. The keypoint schema includes 20 points, including the nose. Some other animal categories have bounding-box annotations only. The project page states that images come from multiple sources, including the internet and other datasets, and asks users to review data-source acknowledgements/rights.

**Use:** Nose keypoint localisation and crop proposal research. It is not a nose-print identity dataset.

**Rights caution:** No blanket commercial image licence was established from the project landing page. Verify original image-level rights before including any images in a commercial training set.

#### E. DogFLW — Dog Facial Landmarks in the Wild

- [GitHub — DogFLW](https://github.com/martvelge/DogFLW)

Published details: 4,335 dog-face images, 46 facial landmarks and a face bounding box. The repository indicates Kaggle download access and publishes the annotation format.

**Use:** Face localisation and nose landmark/crop proposal research. Cursor must inspect the landmark index definition and determine whether nose coordinates can be used robustly to construct coarse bounding boxes.

**Licence:** The repository states CC BY-NC 4.0. This is non-commercial. Do not use it in a commercial PawFriend/NosePrints training/deployment pipeline unless explicit permission or a different applicable licence is obtained. It may be suitable for non-commercial exploration subject to the licence.

#### F. Pet Face Detection Dataset — Zenodo

- [Zenodo record and download — pet face detection dataset-1](https://zenodo.org/records/7604865)

Published details: approximately 15,000 dog and cat images; pet-face bounding boxes and three landmarks (two eyes and nose); YOLO-style `xywh` labels. The record says it samples from AnimalWeb, Cats Dataset, TsingHua Dog, and other dog/cat sources.

**Use:** Potential source for pet-face boxes and nose landmarks. It does not provide a precise nose-leather segmentation or nose biometric identity labels.

**Rights caution:** The Zenodo record does not provide a clearly established licence for the complete image collection. The archive is assembled from multiple upstream datasets. Do not treat public download availability as a commercial training licence. Investigate each source/rights statement before use.

#### G. Oxford-IIIT Pet Dataset

- [Official Oxford VGG dataset page](https://www.robots.ox.ac.uk/~vgg/data/pets/)
- [Images archive](https://thor.robots.ox.ac.uk/~vgg/data/pets/images.tar.gz)
- [Annotations archive](https://thor.robots.ox.ac.uk/~vgg/data/pets/annotations.tar.gz)
- [Zenodo mirror](https://zenodo.org/records/8067751)

Published details: 37 cat/dog categories, roughly 200 images per category, with variation in scale, pose and lighting. Annotations include species/breed, head bounding box (ROI), and foreground/background trimap segmentation.

**Use:** Dog-head/face localisation pretraining and general capture diversity. The box is around the head, not the nose. The labels do not provide repeated individual dog identities for nose-print matching.

**Licence:** Official page states CC BY-SA 4.0 and notes that image copyright remains with original owners. Review attribution/share-alike obligations and obtain legal review for any commercial training/deployment interpretation. Do not assume that a head box can be converted into a precise nose box without extra annotation.

### 5.3 General dog re-identification / classification datasets (secondary only)

#### H. Multi-pose Dog Dataset — Mendeley Data

- [Mendeley Data — Multi-pose dog dataset](https://data.mendeley.com/datasets/v5j6m8dzhv/1)

Published details: 1,657 images of 192 dogs, roughly 9 images per dog on average. Captured with a Xiaomi 9 and manually filtered to remove highly similar images. It was proposed for general dog Re-ID and includes different postures and perspectives.

**Licence:** CC BY 4.0 is shown on the Mendeley record.

**Use:** Auxiliary dog identity/re-identification research and evaluation of identity-aware data handling. It is not described as a nose-print dataset. Use it for nose-print training only if the images contain sufficiently clear noses, nose crops can be produced, and the identity mapping is reliable. More likely useful as a general dog-face/dog-body re-ID comparison, not as a main ArcFace data source.

#### I. PetFace — ECCV 2024

- [Official PetFace project/repository](https://github.com/mapooon/PetFace)
- [ECCV 2024 paper page](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/2660_ECCV_2024_paper.php)
- [arXiv paper](https://arxiv.org/abs/2407.13555)

Published details: 257,484 unique individuals across 13 animal families and 319 breed categories. It is an animal-face identification dataset, not a dedicated dog nose-print corpus. Access is by Google form and manual approval.

**Licence/use restriction:** The project README explicitly states the dataset, code and pretrained models are for non-commercial research purposes only. Do not use it in a commercial PawFriend/NosePrints product or production model without written permission that expressly covers that use.

**Use:** Non-commercial research into general animal face re-identification and unseen-identity evaluation methodology, subject to the licence. Not the priority source for NosePrints nose embeddings.

#### J. images.cv — Dog Nose Image Classification Dataset

- [Dog Nose image classification dataset — images.cv](https://images.cv/dataset/dog-nose-image-classification-dataset)
- [images.cv dataset catalogue](https://images.cv/)
- [images.cv FAQ / licence notes](https://images.cv/faq)
- [images.cv GitHub documentation](https://github.com/images-cv/images.cv)

Published details: 361 labelled images in a single `Dog nose` category, in an ImageFolder-style train/validation/test ZIP. The website tells users to review the original source licence. Its current public format is image classification folders; it does not promise YOLO boxes, masks, or stable per-dog identity labels.

**Use:** Small supplementary visual QA or a preliminary nose/non-nose classifier only if the downloadable samples actually match that task and the underlying licences permit it. Because it is a single positive class, it does not by itself provide negative images for a binary classifier. Not suitable for ArcFace dog identity training.

### 5.4 Academic research useful for capture strategy and evaluation

#### K. Study on the Viability of Canine Nose Pattern as a Unique Biometric Marker (2021)

- [Open-access paper — PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC8697952/)
- [MDPI article](https://www.mdpi.com/2076-2615/11/12/3372)

The study reports 180 nose images from 60 dogs captured at three different time points, approximately 3–4 months apart. It also describes an enlarged set of 278 images from 70 dogs across 19 breeds. The paper's main relevance for us is longitudinal capture: collect the same dog's nose on different visits, rather than collecting only a burst of near-identical frames.

**Important limitation:** The paper does not establish that a complete downloadable, reusable image archive is available under a dataset licence. Do not scrape images from the paper or treat the research figures as a downloadable training dataset. Contact authors if we want to request research data and clarify permission.

The paper's reported matching separation is specific to its study sample and methodology. It is not evidence that our ResNet50/ArcFace system will achieve perfect matching or the same accuracy.

#### L. A Competitive Method for Dog Nose-print Re-identification (2022)

- [arXiv paper](https://arxiv.org/abs/2205.15934)
- [Code — Pet-ReID-IMAG](https://github.com/muzishen/Pet-ReID-IMAG)

The paper discusses the CVPR 2022 dog nose-print challenge. It explores offline augmentation and a combination of classification and metric-learning objectives (cross-entropy, triplet, and pair-wise circle losses) and reports 86.67% AUC for its competition solution.

**Use:** Methodology reference for imbalance, metric learning, augmentation, and model comparison. Do not claim that score for NosePrints. Cursor should compare the method with our existing ArcFace loss pipeline before recommending any controlled experiment.

#### M. Advancing Pet Biometric Identification: A State-of-the-Art Unified Framework for Dogs and Cats (2024)

- [IEEE Access article / DOI](https://doi.org/10.1109/ACCESS.2024.3516130)

The paper describes a pet-biometric capture pipeline and reports a minimum nose-region width of 384 pixels in its capture-quality process, while discussing that some CVPR 2022-derived nose regions could be as small as approximately 70 pixels.

**Use:** Treat 384 px as a useful published design reference for a capture-quality target, not as a universal biometric standard or guaranteed threshold for our camera pipeline. Cursor should inspect actual image distributions and our resize/preprocessing path before applying any minimum.

---

## 6. What these sources can and cannot do for us

| Dataset/source | YOLO nose detector | Nose segmentation/crop | ArcFace nose identity | General dog Re-ID | Main caveat |
|---|---|---|---|---|---|
| CVPR 2022 nose benchmark mirror | Possibly, depending on included original/full images and labels | Nose crops available in some forms; inspect archive | **Potentially yes** if IDs/splits are intact | Yes | Kaggle mirror and licence must be verified; likely already used |
| Nexdata 64,378 / 1,073 | Potentially, if full images/videos and annotations are included | **Yes, vendor claims segmentation** | **Potentially yes**, only if stable dog IDs and usable split/session diversity are confirmed | Yes | Paid; confirm IDs, session structure, and commercial rights |
| StanfordExtra | Potentially via landmarks / image-level labels | Coarse nose landmark, not necessarily tight mask | No direct nose identity data | Potentially | Original image rights differ from annotation licence |
| Animal-Pose | Potentially via nose keypoint | Nose point only; crop proposal | No | Not the primary purpose | Multi-source images; rights vary |
| DogFLW | Face box + nose landmark | Nose point only | No | Not the primary purpose | CC BY-NC 4.0; not commercial without permission |
| Zenodo pet-face | Face box + nose landmark | Nose point only | No | Not the primary purpose | Licence/source rights unclear |
| Oxford-IIIT Pet | Head box only; no direct nose box | No precise nose mask | No | Breed classification only | Head box not nose; CC BY-SA 4.0; image rights remain with owners |
| Multi-pose dog | Not primarily | Could crop visible noses after review | Not nose-specific; possible research experiment only | **Yes** | General dog Re-ID, 9 images/dog average |
| PetFace | Animal face detection/ID | Face, not nose-print mask | No direct nose-print data | **Yes, animal-face Re-ID** | Non-commercial research only |
| images.cv Dog Nose | Possibly a small classification/QA sample | No promised boxes/masks | No identity labels | No | Only 361 images; source licence must be checked |
| 2021 canine nose study | No ready detector labels | Nose images in paper/research | Evidence/methodology, not a public dataset | No | No known licensed dataset download |

---

## 7. Recommended data strategy for NosePrints

### 7.1 Priority order

| Priority | Source/action | Why | Cursor decision required |
|---|---|---|---|
| P0 | Audit existing CVPR mirror and current processed data | Avoid duplicate downloads; reproduce current baseline | Locate path, manifest, labels, split, licence, preprocessing, and metrics |
| P0 | Build consented PawFriend pilot | Data reflects our own phones, capture UX, and target population | Propose schema, consent flow, storage, and split protocol |
| P0 | Request Nexdata sample/specification/licence/quote | Most promising external dedicated nose dataset | Decide go/no-go based on stable identities, sessions, quality, cost, rights |
| P1 | Evaluate StanfordExtra / Animal-Pose / DogFLW / Zenodo for detector | Nose point/face annotations can assist localization | Verify exact schema, image rights, and conversion workload |
| P1 | Evaluate detector-specific real phone-test images | Exposes failures our existing benchmarks may miss | Build failure taxonomy and annotation plan |
| P2 | Evaluate Multi-pose Dog for auxiliary Re-ID | More general dog identity and viewpoint variation | Use only as a separate experiment, not blended into nose biometric training |
| P2 | Consider PetFace only for non-commercial research | Large animal-face identity benchmark | Do not use commercially without explicit permission |
| P2 | images.cv small dog nose set | Small supplementary visual QA | Verify source rights and whether it provides any useful negatives/labels |

### 7.2 Build our own PawFriend pilot dataset

The existing project plan calls for at least 50 real dogs, ideally 5–10 good nose captures per dog. Treat this as a starting pilot and field-evaluation milestone, not a guarantee of reaching a particular AUC.

Suggested collection plan:

- Start with 50+ dogs, representing different breeds/mixes, muzzle shapes, nose sizes, and nose pigmentation where possible.
- Aim for 5–10 usable nose images per dog across at least two capture sessions/visits where feasible.
- Do not collect all images as a rapid burst. Include separate visits/days, lighting, angles, phone cameras, and small changes in distance.
- For registration, continue to require at least 3 accepted nose images if that remains the product decision. Keep extra research captures separate from the minimum product requirement.
- Capture a clear frontal nose, moderate left/right angles, and natural variation. Avoid forcing animals into uncomfortable poses.
- Keep the full original image, crop, detection box/mask, capture metadata, quality decision, and consent reference linked by a random sample ID.
- Capture some hard but valid samples: black, brown, pink, mottled noses; mild angle; indoor/outdoor; slight natural moisture/reflection; different phone sensors.
- Capture invalid samples separately with explicit labels: fur, mouth, paw, other animal, human skin, fabric, keyboard, screen/printed photo, toy, floor, blur, occlusion, overexposure, and no dog nose.
- Get explicit owner consent for use of images in biometric model development and evaluation. Explain purpose, retention, withdrawal/contact route, and whether use includes external/vendor data or a commercial model.

### 7.3 Capture quality guidance

Use the 2024 paper's 384-pixel nose-width reference as an initial target for QA discussions. Do not blindly hard-code it until Cursor checks the dimensions after crop/resize, current detector behaviour, real phone samples, and trade-off between rejection rate and image quality.

Suggested image QA fields:

- nose ROI width/height in original pixels;
- sharpness/focus score;
- exposure/brightness and glare indicators;
- occlusion percentage;
- nose crop completeness (both alar edges and central leather visible, as appropriate);
- angle estimate or coarse angle label;
- camera/device model if available and consented;
- capture session ID and timestamp (store appropriately; do not expose unnecessary metadata);
- human review label: accepted / retake / rejected and reason.

Do not artificially upscale tiny images and count them as high-resolution captures. Upscaling does not recreate lost biometric texture.

### 7.4 Suggested capture consent and privacy approach

- Use a clear opt-in for biometric image collection and ML training. Consent for ordinary pet profile photos must not be silently treated as consent for biometric research/training.
- Maintain owner contact details in the application database, not in ML training folders.
- Use random internal `dog_id` values in training data, not owner names, phone numbers, email addresses, addresses, or public profile URLs.
- Store consent reference/status separately from the model manifest. Do not include personal contact details in CSV/JSON exported for training.
- Support withdrawal: identify the dog's images and derived embeddings/checkpoints where feasible, and document what can/cannot be removed after aggregated model training. Define this before large-scale collection.
- Restrict raw data access; encrypt storage and backups; avoid uploading private pet images to public notebooks or repositories.
- Review applicable Indian privacy, consumer, animal-welfare, and contractual requirements with the project owner/legal adviser. This handoff is not legal advice.

---

## 8. Proposed dataset structure and metadata

Do not force a new folder structure until Cursor has inspected the current training script. The project status says the current embedding training path expects per-dog folders. The following is a proposed target structure, not a claim about the current implementation.

```text
ml/
├── data/
│   ├── raw/                         # Original archives; immutable; not committed to Git
│   │   ├── cvpr_pet_biometrics/
│   │   ├── nexdata_dog_nose/         # Only after licence and purchase approval
│   │   ├── pawfriend_pilot/
│   │   └── detector_external/
│   ├── manifests/
│   │   ├── dataset_sources.csv
│   │   ├── image_manifest.csv
│   │   ├── consent_manifest.csv      # No owner contact data
│   │   ├── label_audit.csv
│   │   └── checksums.sha256
│   ├── processed/
│   │   ├── nose_crops/
│   │   ├── nose_masks/
│   │   └── detector_yolo/
│   │       ├── images/train/
│   │       ├── images/val/
│   │       ├── images/test/
│   │       ├── labels/train/
│   │       ├── labels/val/
│   │       └── labels/test/
│   ├── identity/
│   │   ├── train/<dog_id>/*.jpg
│   │   ├── val/<dog_id>/*.jpg
│   │   └── test/<dog_id>/*.jpg
│   └── evaluation/
│       ├── gallery/
│       ├── probe/
│       └── open_set_unknown/
├── training/
├── evaluation/
└── reports/
```

### 8.1 Suggested image manifest

One row per image/crop. Use only non-personal identifiers.

| Field | Example | Notes |
|---|---|---|
| `sample_id` | `sample_000001` | Random unique image/sample ID |
| `source_dataset` | `pawfriend_pilot` | Original source |
| `source_record_id` | `record_ABC` | Original dataset record, if permitted |
| `dog_id` | `dog_0001` | Stable pseudonymous dog ID |
| `session_id` | `session_02` | Capture visit/session |
| `image_path` | `raw/dog_0001/session_02/img_01.jpg` | Relative path |
| `crop_path` | `processed/nose_crops/sample_000001.jpg` | Derived nose crop |
| `annotation_path` | `annotations/sample_000001.json` | Box/keypoint/mask annotation |
| `annotation_type` | `segmentation` | `bbox`, `keypoint`, `segmentation`, `none` |
| `image_width` / `image_height` | `1920` / `1080` | Original dimensions |
| `nose_roi_width_px` | `540` | Measure on original crop, not resized tensor |
| `angle` | `frontal` | Controlled vocabulary where possible |
| `lighting` | `outdoor_diffuse` | Controlled vocabulary |
| `device` | `android_model_x` | Avoid unnecessary personal metadata |
| `quality_label` | `accepted` | `accepted`, `retake`, `rejected` |
| `quality_reason` | `sharp_frontal` | Human/review notes |
| `consent_ref` | `consent_0001` | Reference only; no contact data |
| `license_id` | `licence_pawfriend_v1` | Links to licence register |
| `split` | `train` | Must be assigned by group-aware split logic |

### 8.2 Dataset source and licence manifest

For every source, record:

- dataset/source name and version/date;
- official landing page and actual download URL;
- date downloaded and operator;
- checksum for each archive/file;
- stated licence and source of the licence statement;
- whether commercial model training is explicitly permitted;
- attribution/share-alike/non-commercial/redistribution restrictions;
- upstream dataset/image sources;
- whether any identities or labels are missing/ambiguous;
- approval owner and status (`approved`, `research-only`, `blocked`, `pending`).

Do not let an automatic downloader bypass a licence gate. A dataset is `blocked` until the project owner confirms its licence is compatible with the intended product use.

---

## 9. Data quality, labels, and train/validation/test splitting

### 9.1 Required automated checks before training

Cursor should propose or inspect tooling to check:

1. Archive integrity and safe extraction (no path traversal or unexpected executable files).
2. Corrupt/unsupported image files and RGB/greyscale conversion rules.
3. File dimensions and nose ROI dimensions.
4. Exact duplicates by SHA-256 and near-duplicates using perceptual hash/embedding review.
5. Missing IDs, duplicate IDs, and inconsistent dog-to-image mappings.
6. Image counts per dog and per session; flag identities with only one image.
7. Annotation integrity: boxes within image boundaries; non-empty masks; keypoints within image; class index consistency.
8. Label leakage and near-duplicate leakage across splits.
9. Class/identity imbalance and source/domain imbalance.
10. Quality distributions: blur, glare, occlusion, nose width, angle, pigmentation, capture device, lighting.
11. Licence status for each source.
12. A contact-sheet report for human visual QA, with IDs pseudonymised.

### 9.2 Splitting rules — avoid data leakage

Do not use a naïve random image-level split.

For **detector evaluation**, group correlated samples by original capture/video/session and, where possible, by dog. Keep adjacent video frames and near-duplicates in one split. Use a held-out phone/device/session subset to measure field robustness.

For **identity embedding training**, preserve multiple images per dog in training. Validation and test must be defined according to the intended metric:

- **Closed-set gallery/probe re-identification:** the same dog identities intentionally appear in both gallery and probe, but gallery/probe photos must be from different captures/sessions. Do not use the same photo or burst/video neighbours in both. This evaluates retrieval of registered dogs.
- **Verification threshold calibration:** use genuine pairs (same dog, different images/sessions) and impostor pairs (different dogs). Prefer validation identities not used for model fitting to assess threshold generalisation where feasible.
- **Unseen-identity/open-set evaluation:** hold out dog identities entirely from embedding-model training; construct gallery/probe and unknown-dog trials from these held-out identities. This evaluates whether new dogs and unknown dogs are handled safely.
- **Final test:** freeze it. Do not tune architecture, thresholds, preprocessing, or hyperparameters against the final test results.

Cursor must inspect the existing evaluation protocol and make a written split plan before creating new splits. A model may have a valid closed-set rank-1 metric and still perform poorly on open-set unknown dogs; report them separately.

### 9.3 Recommended evaluation metrics

For detector:

- mAP50 and mAP50–95;
- precision, recall, false positives per image;
- missed-nose rate and wrong-region crop rate;
- performance by angle, lighting, pigmentation, device, nose ROI size, and image quality;
- failure examples: keyboard, fabric, fur, screen/photo, mouth, paw, non-dog, blur, partial occlusion.

For embedding/re-ID:

- ROC AUC on a clearly defined pair protocol;
- rank-1, rank-5 and mAP on gallery/probe retrieval;
- genuine acceptance / false acceptance rates at operating thresholds;
- FAR/FRR and EER (where meaningful);
- false-match rate on unknown dogs not in the registry;
- performance by capture session, angle, lighting, phone/device, and image quality;
- calibration of Likely/Possible/No-match bands;
- confidence intervals or repeated seeds where dataset size makes them meaningful.

Always publish the dataset/split description and number of dogs, images, sessions, genuine pairs, impostor pairs, and unknown trials beside the score.

---

## 10. Suggested model-enhancement experiments

These are hypotheses for Cursor to assess against the actual implementation. Do not implement all of them at once.

### 10.1 Improve nose detector (YOLOv8-nano)

Potential improvements:

- Add manually reviewed PawFriend phone images, especially cases where current model misses or crops incorrectly.
- Use external nose keypoints or face boxes only as coarse guidance; convert to tight nose boxes only after human review.
- Add hard-negative images: fabric patterns, keyboard grids, phone screens/printed nose photos, fur, paws, mouths, other animals, and non-nose objects.
- Evaluate whether segmentation masks improve crop boundaries or if a tight bounding box is sufficient for the current embedding input.
- Inspect anchor-free YOLO preprocessing, confidence threshold, image size, padding, NMS, crop expansion, and retry behaviour before retraining.
- Add a visual QA notebook/report with ground-truth box and predicted crop overlays.
- Consider a separate lightweight `dog_nose_validity` classifier only if the existing heuristics and detector still fail on a clearly measured failure class. Compare the extra latency/complexity against improved detector training.

Avoid using random web dog images as detector labels unless the actual nose box is labelled and the source licence permits the intended use.

### 10.2 Improve embedding model (ResNet50 + ArcFace)

Potential improvements to evaluate:

- Fine-tune from the existing checkpoint rather than training from scratch, provided the checkpoint is valid and the data domain is compatible.
- Add real PawFriend samples across separate sessions and capture devices.
- Recheck alignment/crop consistency; nose leather should be consistently represented, not random portions of muzzle/fur.
- Compare current ArcFace objective with a controlled experiment using combined classification + triplet loss or pair-wise circle loss, informed by the 2022 challenge paper.
- Evaluate hard-negative mining for visually similar noses, but make sure hard negatives are correctly labelled.
- Test input sizes based on real nose ROI resolution. Do not upscale low-resolution images and claim more biometric detail.
- Use augmentation carefully. Moderate lighting/colour/blur/rotation/crop perturbations may improve capture robustness, but aggressive geometric distortion, cutmix/mixup, heavy blur, or random crops can destroy identity texture. Every augmentation must be validated against held-out real capture images.
- Compare one change at a time against the current baseline with the same evaluation split and seed protocol.

Do not switch to a larger backbone, ensemble, transformer, or a different loss merely because an academic paper used it. First establish whether our errors come from low-resolution crops, detection, alignment, identity-label noise, insufficient sessions, or embedding capacity.

### 10.3 Quality / anti-junk classifier

Current project already has G0–G3 heuristics. Cursor should:

1. inspect the current gate logic and unit/integration tests;
2. gather a labelled failure set from real scans;
3. quantify false acceptance and false rejection by junk type;
4. decide if the heuristics need better thresholds, a binary classifier, or better detector data;
5. keep the user-facing behaviour honest when the model is uncertain.

A binary `dog nose vs not dog nose` classifier is not a dog identity recogniser. It can only supplement input validation.

### 10.4 Open-set identification and registry matching

NosePrints must handle dogs that are not registered. Cursor should inspect whether current matching logic properly returns no match when an unknown dog is scanned.

- Calibrate thresholds on a separate validation set with both genuine and impostor/unknown comparisons.
- Measure false accept rate at the target operating point; in a lost-dog system a false owner association can be harmful.
- Consider per-dog multiple templates/prototypes only if retrieval and storage evidence supports it.
- Do not expose owner contact details until staff confirmation, as specified by the current product flow.
- Maintain staff confirmation even when similarity scores are high.

---

## 11. Training and evaluation workflow — proposed end-to-end sequence

Cursor must compare this workflow with the current scripts and update the exact commands only after inspecting their argument parsers and expected paths.

### Phase 0 — repository and baseline audit (read-only)

1. Read `MASTER_PLAN.md`, `ACCURACY.md`, `DEPLOY.md`, `G0_G3_AUDIT_FIXES.md`, `docs/dataset-download-guide.md`, `docs/identity-download-guide.md`, and any current ML task files.
2. Inspect model training, evaluation, preprocessing, export, inference and API loading code.
3. Locate all raw/processed datasets and model checkpoints. Record file counts, folder names, label formats, checksums, and disk usage without printing personal data.
4. Reproduce current detector and embedding metrics if possible.
5. Record exact Python/PyTorch/Ultralytics/ONNX versions, CUDA/device availability, GPU VRAM, and inference environment.
6. Produce an audit report with unknowns and blockers. No code/data changes.

### Phase 1 — dataset availability and licence gate

1. Test the CVPR/Kaggle mirror and inspect its dataset card, terms, files, and metadata.
2. Request Nexdata sample/schema/quote/licence; do not purchase until the project owner approves.
3. Inspect secondary detector datasets and verify exact annotation keys and source rights.
4. Create `DATASET_SOURCES.md` and a licence register (`DATA_LICENSES.md`).
5. Set each source to `approved`, `research_only`, `blocked`, or `pending`.
6. Do not run a downloader for a `blocked` or `pending` source.

### Phase 2 — data ingestion and audit

1. Use a reproducible downloader only for approved public sources.
2. Record source URL, version, date, checksum, file size, licence and attribution.
3. Store originals read-only under `ml/data/raw/` and exclude large data from Git.
4. Extract safely; detect corrupt images and duplicates.
5. Build image/identity/session manifests.
6. Audit all labels and counts; generate contact sheets for manual review.
7. Separate valid nose crops, detector full images, and negative/junk samples.
8. Do not combine datasets unless identities/labels are semantically compatible and provenance is retained.

### Phase 3 — capture PawFriend pilot data

1. Confirm consent text and owner opt-in.
2. Create pseudonymous dog IDs and separate capture session IDs.
3. Collect the planned 5–10 images per dog, with at least two sessions where feasible.
4. Record capture/quality metadata and retain originals.
5. Run the existing PWA pipeline on real phones and log detector/quality outcomes.
6. Manually review accepted/rejected crops; annotate detector failures.
7. Aim for 50+ dogs in the first pilot; expand based on measured performance needs.

### Phase 4 — create leakage-safe splits and baseline report

1. Define group-aware detector splits.
2. Define identity-model train/validation/test and gallery/probe/open-set protocols separately.
3. Use separate dog IDs for model-training generalisation test; keep gallery/probe sharing only where retrieval evaluation explicitly requires it.
4. Save split files and freeze final test.
5. Compute baseline detector and embedding results on the exact new evaluation protocol before training.

### Phase 5 — controlled experiments

Recommended sequence:

A. Detector data improvement only.  
B. Detector + crop/alignment improvement if A shows it is needed.  
C. Embedding fine-tune on approved identity-labelled nose prints.  
D. Compare objective/augmentation/hard-negative strategy one variable at a time.  
E. Test optional quality classifier only if failure analysis justifies it.  
F. Run open-set calibration and multi-session field evaluation.

Track configuration, seed, commit, source-data manifest version, checkpoint, metrics and notes for every run.

### Phase 6 — export and safe deployment

1. Select the model only if it beats the baseline on pre-defined metrics and does not cause unacceptable false-accept/false-reject trade-offs.
2. Re-run the exact ONNX preprocessing/inference parity test.
3. Version the model, training data manifest, thresholds and preprocessing config together.
4. Keep old ONNX files/checkpoints and a rollback plan.
5. Recalibrate `MATCH_THRESHOLD` and `MATCH_THRESHOLD_LOW` from the new validation ROC; do not reuse 0.56/0.51 automatically.
6. Run API health checks, known-dog match, unknown-dog no-match, and junk-photo reject tests.
7. Run real-phone HTTPS acceptance tests with staff confirmation.
8. Do not deploy until the project owner explicitly approves.

---

## 12. Current commands mentioned in the project status — verify before use

The project status snapshot references the following PowerShell commands. Cursor must inspect the actual scripts and `--help` output before executing, because arguments and expected folder layout may have changed.

### Detector training (as documented)

```powershell
cd D:\NosePrints-Pawfriend\ml
.\.venv\Scripts\activate
cd training
python train_detector.py --epochs 40 --batch 8 --imgsz 640 --device 0
```

### Embedding training (as documented)

```powershell
cd D:\NosePrints-Pawfriend\ml
.\.venv\Scripts\python.exe training\train_embedding.py --data_dir data\identity --epochs 50 --batch_size 16 --num_workers 0 --checkpoint_dir checkpoints\embedding
```

The project status says the expected identity folder shape is:

```text
ml/data/identity/train/<dog_id>/*.jpg
ml/data/identity/val/<dog_id>/*.jpg
```

After training, the documented path is to run evaluation/ROC, export ONNX, copy to `backend/models/`, and restart the API. **Do not copy/overwrite model files until Cursor verifies the current export process, API model-loading path, and rollback strategy.**

---

## 13. Questions Cursor must answer before implementation

Cursor should answer all questions with repository evidence. If evidence is missing, mark the answer as unknown and ask me for the specific file, access, or decision needed.

### A. What do we already have?

1. Which exact CVPR 2022/Kaggle dataset or mirror was used for the existing embedding model?
2. Where is the original archive and where are processed images/crops stored?
3. How many unique dog IDs and images actually exist locally?
4. Do we have a metadata file mapping every image to a dog ID?
5. Which splits and protocols were used for the reported 78.6% rank-1 and 0.80 AUC?
6. Can those metrics be reproduced from the current commit and checkpoints?
7. Does the existing dataset contain raw/full dog photographs, nose crops, nose boxes, masks, or only crops?
8. What is the current training image-size distribution and actual pixel width of nose regions?
9. How many real PawFriend registrations/scans currently exist, and are they usable with consent for training?
10. What are the current GPU model/VRAM, free disk space, Python/CUDA versions, and expected training time?

### B. Which research datasets should we use?

1. Is the CVPR Kaggle mirror downloadable and sufficiently complete? Is there a valid dataset licence for our intended use?
2. Is Nexdata's 64,378-image set worth buying based on sample inspection, stable identity labels, images per dog, separate sessions, segmentation schema, image resolution, price, and commercial rights?
3. Which secondary detector dataset has the cleanest compatible annotations and rights?
4. Can StanfordExtra or Animal-Pose nose keypoints generate reliable nose boxes? What conversion and manual QA are required?
5. Are DogFLW, Zenodo pet-face, Oxford-IIIT Pet, Multi-pose Dog, PetFace, and images.cv appropriate for any exact task? Which must be excluded due to non-commercial/unclear rights?
6. Are we duplicating any dataset already present?
7. Do we need an external commercial dataset at all, or will a pilot + existing challenge data be a better first investment?

### C. What will improve accuracy/robustness?

1. Are errors primarily caused by missed nose detection, crop alignment, image resolution, bad quality, label noise, or embedding limitations?
2. Should we keep YOLOv8n and ResNet50+ArcFace, or run a controlled comparison with another detector/backbone/loss?
3. Should nose segmentation, keypoint alignment, a quality classifier, or better capture UX be prioritised?
4. Which augmentation strategies preserve biometric nose texture?
5. Do we need hard-negative mining? How will negatives be selected and labels verified?
6. How should we evaluate open-set unknown dogs and prevent false owner association?
7. What measurable acceptance criteria should a new model beat before we deploy it?
8. Which changes have the highest expected value relative to engineering time, compute, and cost?

### D. What exactly do you need from me?

Produce a checklist with each item marked `required now`, `required later`, or `not needed`, and explain why. Potential items include:

- Kaggle access or a manually downloaded archive if automated access is blocked;
- dataset licence/terms approval;
- Nexdata sample, quotation, or purchase approval;
- PawFriend's approval for a real-dog pilot and owner consent wording;
- sample phone images with consent;
- current project root path and confirmation of the active branch;
- GPU model/VRAM, storage availability, and whether cloud GPU is permitted;
- approval to install any package or modify Python environments;
- approval to annotate images using CVAT/Label Studio/Roboflow or another tool;
- decisions about commercial vs academic-only data;
- explicit approval before any training run, ONNX replacement, threshold change, DB cleanup, or deployment.

Do not ask me for passwords, Kaggle API tokens, cloud secrets, database credentials, or owner contact data in chat. If credentials are required, explain the secure local configuration method and let me handle them.

---

## 14. Required format for Cursor's first report

Cursor's first response should be a decision report with these sections:

1. **Repository audit:** exact paths, actual scripts, actual model artifacts, current data folders, and test/evaluation evidence.
2. **Current baseline verification:** reproducible metrics or reasons they cannot be reproduced.
3. **Existing dataset inventory:** source, image count, identity count, annotation types, splits, licence status, disk usage, duplicates, and data-quality issues.
4. **Dataset link review:** each link marked `reachable`, `downloadable`, `requires account/form`, `paid`, `unavailable`, `licence unclear`, or `not suitable`; distinguish landing-page reachability from actual archive validation.
5. **Dataset suitability matrix:** detector, crop/segmentation, identity embedding, general Re-ID, and licence suitability.
6. **Recommended data acquisition order:** ranked source choices and reasons; explicitly say what not to download.
7. **Model improvement hypotheses:** expected mechanism, measurable metric, potential risks, and cost/complexity.
8. **Proposed experiments:** baseline, one-variable-at-a-time experiments, dataset splits, metrics, and model selection gates.
9. **Storage/compute estimate:** archive size, extracted size, processed size, GPU requirements, and whether local hardware is sufficient. State assumptions.
10. **Security/licensing/privacy risks:** blocked data sources, consent needs, personal data handling, and model/data retention.
11. **What you need from me:** specific inputs and approvals, prioritised.
12. **Recommended next step:** exactly one small, reversible step to begin with.

Every claim about our code must cite the file path and relevant function/class/config. Every external dataset claim must link to the official source or relevant dataset card. Separate verified facts from inference.

---

## 15. Guardrails — actions Cursor must not take without approval

- Do not download paid/licence-restricted datasets or accept paid vendor terms.
- Do not use non-commercial datasets in a commercial training/deployment path without permission.
- Do not scrape Google Images, Instagram, websites, or private pet-owner accounts for training images.
- Do not use generated/synthetic dog noses as genuine biometric identity examples.
- Do not mix identities across datasets unless there is a verified mapping; do not invent dog IDs.
- Do not silently relabel images or use weak pseudo-labels as ground truth.
- Do not commit large datasets, owner data, credentials, or consent forms to Git.
- Do not delete, wipe, overwrite, or migrate the production registry/database.
- Do not overwrite the existing ONNX models or checkpoints; preserve backups and hashes.
- Do not alter live match thresholds without held-out calibration and explicit approval.
- Do not remove staff confirmation or expose owner contact before staff approval.
- Do not claim an improvement from training loss, validation loss alone, or a metric measured on contaminated/leaked data.
- Do not run long training or cloud jobs until hardware/cost are stated and approved.
- Do not modify production code or deployment configuration as part of the initial audit.

---

## 16. Proposed acceptance criteria for a future improvement

Cursor should propose exact numerical targets only after it sees the baseline and dataset. The following are minimum process criteria, not promised model scores:

- Reproducible baseline metrics from versioned splits and code.
- No image/near-duplicate or session leakage across evaluation partitions.
- Written provenance and compatible licence for every training image source.
- At least one held-out real-phone dataset from PawFriend.
- Explicit reporting of unique dogs, images per dog, sessions per dog, image quality, and nose-region pixel size.
- Detector evaluation includes real phone failure categories, not only mAP.
- Embedding evaluation includes both registered-dog retrieval and unknown-dog/open-set rejection.
- Similarity thresholds recalibrated only from an appropriate held-out validation set.
- ONNX inference parity with the trained model within defined numerical tolerance.
- No regression in API latency, memory, or capture acceptance rate beyond an agreed tolerance.
- Staff confirmation remains mandatory for owner contact.
- Rollback to the previous model/config is tested.

A model should not be selected solely because rank-1 or AUC improved on one benchmark. Evaluate false matches, unknown-dog behaviour, capture failure rates, and real-phone performance together.

---

## 17. Final recommendation from this research

The most sensible path is **audit first, then acquire only what fills a proven gap**.

1. Reproduce and understand the existing CVPR-based embedding baseline before acquiring another copy.
2. Begin a consented PawFriend pilot with 50+ real dogs, multiple captures per dog and more than one session where feasible.
3. Obtain a Nexdata sample and full licence/schema quote. Buy only if dog identity labels, session diversity, nose resolution, segmentation data, and commercial training rights are confirmed in writing.
4. Improve the YOLO detector using real phone failures and only those external face/keypoint datasets whose image rights and labels are suitable.
5. Fine-tune the existing ArcFace model only after identity/session manifests and leakage-safe evaluation splits are ready.
6. Re-calibrate matching thresholds and preserve staff confirmation.
7. Keep all external dataset sources, licences, manifests, checksums, training configurations, model versions, and evaluation reports documented.

**The project's likely bottleneck is data quality and real-world coverage, not automatically the choice of neural-network architecture.** Cursor's job is to prove or disprove that hypothesis with the actual repository, capture samples, error analysis, and reproducible experiments.

---

## 18. External references and source links

The dataset specifications and research notes in this document were checked against the following source pages on 9 November 2026. Dataset access and terms can change; recheck before download or use.

### Dataset pages / repositories

- [CVPR Pet Biometric Challenge Kaggle page](https://www.kaggle.com/datasets/zekunn/pet-biometric-challenge)
- [Pet-ReID-IMAG — CVPR 2022 top-three solution code](https://github.com/muzishen/Pet-ReID-IMAG)
- [dashengge/pet-biometrics](https://github.com/dashengge/pet-biometrics)
- [DogNosePrintIdentification](https://github.com/liuhaoyutz/DogNosePrintIdentification)
- [Nexdata Dog Nose Print Dataset — 64,378 images / 1,073 dogs](https://www.nexdata.ai/datasets/computervision/1051)
- [StanfordExtra](https://github.com/benjiebob/StanfordExtra)
- [Stanford Dogs image source](http://vision.stanford.edu/aditya86/ImageNetDogs/)
- [Animal-Pose official site](https://sites.google.com/view/animal-pose/)
- [Animal-Pose GitHub](https://github.com/noahcao/animal-pose-dataset)
- [Animal-Pose keypoint Google Drive](https://drive.google.com/drive/folders/1xxm6ZjfsDSmv6C9JvbgiGrmHktrUjV5x?usp=sharing)
- [DogFLW](https://github.com/martvelge/DogFLW)
- [Pet face detection dataset-1 on Zenodo](https://zenodo.org/records/7604865)
- [Oxford-IIIT Pet official page](https://www.robots.ox.ac.uk/~vgg/data/pets/)
- [Oxford-IIIT Pet Zenodo copy](https://zenodo.org/records/8067751)
- [Multi-pose Dog dataset on Mendeley Data](https://data.mendeley.com/datasets/v5j6m8dzhv/1)
- [PetFace project](https://github.com/mapooon/PetFace)
- [PetFace ECCV 2024 paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/2660_ECCV_2024_paper.php)
- [images.cv Dog Nose classification dataset](https://images.cv/dataset/dog-nose-image-classification-dataset)
- [images.cv FAQ/licensing notes](https://images.cv/faq)

### Academic papers

- [Study on the Viability of Canine Nose Pattern as a Unique Biometric Marker (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8697952/)
- [A Competitive Method for Dog Nose-print Re-identification (2022)](https://arxiv.org/abs/2205.15934)
- [PetFace: A Large-Scale Dataset and Benchmark for Animal Identification (ECCV 2024)](https://arxiv.org/abs/2407.13555)
- [Advancing Pet Biometric Identification: A State-of-the-Art Unified Framework for Dogs and Cats (IEEE Access 2024)](https://doi.org/10.1109/ACCESS.2024.3516130)

---

**End of handoff.** Cursor should now begin with the read-only audit in Section 1 and return the report in Section 14. No implementation should begin until the project owner has reviewed Cursor's findings and approved the proposed next step.

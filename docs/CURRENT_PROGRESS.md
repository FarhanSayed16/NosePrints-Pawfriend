# Current ML progress — live status

**Updated:** 9 November 2026 (evening)

## Verdict

**Not stuck.** Detector train looked frozen in the Cursor terminal (1MB progress-bar spam) but GPU work continued. We **stopped** remaining YOLO epochs after locking the best checkpoint, exported a candidate ONNX, and **started embedding continue-train**.

| Stage | Status | Result |
|-------|--------|--------|
| Phase 0 baseline freeze | Done | Hashes + inventory + licences |
| Phase 1 detector data | Done | `merged_v1` (~6133 imgs) |
| Phase 2 YOLO retrain | Done | Best **mAP50 = 0.54057** @ epoch 33 (matches prior ~0.54) |
| Phase 3 ArcFace continue-train | **Running** | From `best_model.baseline.pt`, 30 epochs, LR `1e-4` |
| Phase 4 promote / thresholds | Pending | Only if metrics beat baseline |
| Phase 5 changelog | Pending | |

## Locked artifacts (safe to resume anytime)

| Path | Why it matters |
|------|----------------|
| `ml/checkpoints/detector_merged_v1/best_epoch33_map054.pt` | Best YOLO weights |
| `ml/checkpoints/detector_merged_v1/results.csv` | Full epoch history |
| `backend/models/nose_detector.candidate.onnx` | Exported candidate (~12.3 MB) |
| `backend/models/nose_detector.prev.onnx` | Production rollback |
| `ml/checkpoints/embedding/best_model.baseline.pt` | Embedding baseline (frozen) |
| `backend/models/embedding_model.prev.onnx` | Embedding ONNX rollback |
| `ml/eval_results/detector/merged_v1_train_summary.md` | Detector decision record |

## Detector decision

Candidate **eligible to promote** (mAP50 matches prior). Promotion deferred to Phase 4 with embedding so we ship one coherent model set + docs.

## Embedding run (Phase 3) — LIVE

```text
PID:         17688 (worker also ~34588)
started:     2026-11-09 23:30
device:      CUDA + AMP
data:        13956 train / 6044 val images, 6000 dogs
resume:      best_model.baseline.pt (was epoch 47, val_loss 6.78)
out:         ml/checkpoints/embedding_continued_v1/
epochs:      30
batch:       16 (~872 steps/epoch)
lr:          1e-4 (fine-tune)
first batch: Epoch 1 / Batch 100 — loss ~23 (ArcFace head re-init; expected)
log:         ml/runs/embedding/continued_v1_20261109_233026.err.log
pid file:    ml/runs/embedding/continued_v1.pid
```

**ETA (rough):** overnight-class on RTX 4050 (~30–60+ min/epoch depending on I/O). Do not judge from Cursor terminal freeze — watch the `.err.log` + `nvidia-smi`.

**Next after train finishes:** `evaluate.py` + open-set → compare AUC / rank-1 / thresholds vs baseline → export candidate ONNX only if better → promote detector+embedding winners together → update `ACCURACY.md` / `PROJECT_STATUS.md`.

## How to check without guessing

```powershell
nvidia-smi
Get-Content D:\NosePrints-Pawfriend\ml\runs\embedding\continued_v1_20261109_233026.err.log -Tail 30
Test-Path D:\NosePrints-Pawfriend\ml\checkpoints\embedding_continued_v1\best_model.pt
```

# ML changelog — Free Public Track (9–10 Nov 2026)

## Detector (merged_v1)
- Trained YOLOv8n on `ml/data/detector/merged_v1`
- Best mAP50 **0.54057** @ epoch 33 (matches prior ~0.54)
- Candidate → production: **True**
- Rollback: `backend/models/nose_detector.prev.onnx`

## Embedding (continue-train)
- Resume from `best_model.baseline.pt`, 30 epochs, LR 1e-4 → `embedding_continued_v1`
- Baseline AUC **0.802713** / Rank-1 **0.785572**
- New AUC **0.800214** / Rank-1 **0.783091**
- Promoted to production: **False**
- Rollback: `backend/models/embedding_model.prev.onnx`
- Eval: `ml/eval_results/embedding/continued_v1/`
- Open-set: `ml/eval_results/embedding/open_set_continued_v1.txt`
- Decision: `ml/eval_results/embedding/threshold_decision_continued_v1.md`

## Autopilot
- Ran unattended via `ml/runs/embedding/phase45_autopilot.ps1`

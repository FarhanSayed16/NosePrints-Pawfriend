# Training live status

> Auto-refreshes ~every 30s. **Keep this tab open** to track progress.  
> Last refresh: **2026-11-09 23.38.38**

## `RUNNING`  `██░░░░░░░░░░░░░░░░░░` 8.6%

| Item | Value |
|------|-------|
| Train PID | `17688` |
| GPU | `1 %, 3362 MiB, 6141 MiB` |
| Best checkpoint | yes — updated 23.36.50 |
| Progress | Epoch **3/30** · Batch **500/872** · **8.6%** · batch loss 18.1918
Last finished epoch — train **19.2204** / val **18.4757** (2 epoch summaries)
ETA ~**1.5 h** (≈ 01.08 local) |

## Latest log

```
2026-11-09 23:35:09,789 | INFO | Epoch [2/30] Batch [400/872] Loss: 19.1846
2026-11-09 23:35:27,286 | INFO | Epoch [2/30] Batch [500/872] Loss: 20.4787
2026-11-09 23:35:43,255 | INFO | Epoch [2/30] Batch [600/872] Loss: 19.9024
2026-11-09 23:35:59,931 | INFO | Epoch [2/30] Batch [700/872] Loss: 17.6439
2026-11-09 23:36:15,185 | INFO | Epoch [2/30] Batch [800/872] Loss: 18.2890
2026-11-09 23:36:49,568 | INFO | Epoch [2/30] Train Loss: 19.2204 | Val Loss: 18.4757 | LR: 0.000010
2026-11-09 23:36:50,111 | INFO | Saved best model to checkpoints\embedding_continued_v1\best_model.pt
2026-11-09 23:37:08,262 | INFO | Epoch [3/30] Batch [100/872] Loss: 16.7121
2026-11-09 23:37:26,759 | INFO | Epoch [3/30] Batch [200/872] Loss: 16.8092
2026-11-09 23:37:43,093 | INFO | Epoch [3/30] Batch [300/872] Loss: 16.0806
2026-11-09 23:38:03,531 | INFO | Epoch [3/30] Batch [400/872] Loss: 15.9813
2026-11-09 23:38:23,617 | INFO | Epoch [3/30] Batch [500/872] Loss: 18.1918
```

## While this runs — you don't need to do GPU work

Parallel safe tasks (no GPU):
1. Open this file + glance every so often — if `STOPPED` unexpectedly, ping the agent.
2. Optional: phone/capture UX smoke on the tunnel when free (doesn't need new models yet).
3. Nothing else required — Phase 4 (eval → promote → docs) starts automatically once training ends if the agent is watching, or on your next message.

Detector candidate is already saved. Do **not** kill PID `17688` unless you intend to abort.

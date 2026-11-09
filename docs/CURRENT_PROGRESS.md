# Current ML progress — post-autopilot

**Updated:** 2026-11-10T00:55:44.4305780+05:30

## Verdict

| Stage | Status |
|-------|--------|
| Phase 0–2 | Done (detector candidate ready; promoted=True) |
| Phase 3 ArcFace continue-train | Done |
| Phase 4 eval/promote | Done — embed promoted=False |
| Phase 5 changelog | Written: `docs/ML_CHANGELOG_2026-11-09.md` |

## Metrics

- Baseline: AUC 0.802713 · Rank-1 0.785572
- Continued: AUC 0.800214 · Rank-1 0.783091
- Details: `ml/eval_results/embedding/threshold_decision_continued_v1.md`

## Next human check (when back)

1. Open `docs/TRAINING_LIVE.md` — should say PHASE 4/5 COMPLETE
2. `curl` /health if API running
3. Optional identify smoke on tunnel
4. If embedding promoted, consider applying new thresholds from decision note

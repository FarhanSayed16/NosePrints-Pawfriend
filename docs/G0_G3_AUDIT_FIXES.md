# G0–G3 Audit — Gaps, Fixes & Improvements

**Date:** 5 September 2026 (updated after remediation pass)  
**Scope:** Garbage-photo / false-match remediation through Phase G3  
**Related:** [`GARBAGE_PHOTO_FALSE_MATCH_PLAN.md`](./GARBAGE_PHOTO_FALSE_MATCH_PLAN.md) · [`ACCURACY.md`](./ACCURACY.md) · [`CAPTURE_UX.md`](./CAPTURE_UX.md)

---

## Status: P0–P2 + actionable P3 implemented in code

| ID | Status |
|----|--------|
| P0.1 found-intake nose gate | **Fixed** — `prepare_nose_scan` before embed; listing kept without print on fail |
| P0.2 gallery purge | **Tooling ready** — Staff → Registry cleanup (+ Load more); **manual purge still required before demo** |
| P0.3 rebuild tunnel | **Ops** — rebuild after this pass |
| P0.4 stale docs | **Fixed** — plan Cause A historical; CAPTURE_UX; sign-off |
| P1.1 identify look gate | **Fixed** — `force_appearance` + soft_warn |
| P1.2 AppearancePhoto stale file | **Fixed** — clear parent on new pick / soft-warn |
| P1.3 Identify floor | **Fixed** — uses `threshold_used` |
| P1.4 top_score on no-match | **Fixed** — API `top_score=0`; audit score in MatchLog only |
| P1.5 DogUpdate Unknown | **Fixed** — blank → Unknown |
| P1.6 G2.1 tests | **Fixed** — `apply_candidate_honesty` unit tests |
| P2.1 pre_cropped + redetect | **Fixed** — fail closed if redetect off |
| P2.2 quality-check | **Fixed** — shared `prepare_nose_scan` |
| P2.3 FoundIntake Unknown | **Fixed** — required + chips |
| P2.4 band copy | **Fixed** — Likely / Possible |
| P2.5 .env.example LOOK_* | **Fixed** |
| P2.6 profile-photo auth | **Fixed** — rate limit + open window hours; staff bypass |
| P2.7 Staff pagination | **Fixed** — Load more |
| P2.8 Register soft-warn UX | **Fixed** — Use anyway only |
| P2.9 HTTP look-check tests | **Fixed** |
| P3.7 zero top_score UI | **Fixed** with P1.4 |
| P3.8 delete match logs | **Fixed** on dog delete |
| P3.9 min 3 nose prints | **Fixed** — Register requires ≥3 successes |
| P3.1–P3.6 ML / liveness | **Deferred (G4)** — not code-closed here |

---

## Still required before senior demo (ops, not code)

1. **Purge** junk dogs via Staff → Registry cleanup.  
2. **Rebuild** frontend (`npm run tunnel`) + hard-refresh phone.  
3. Run acceptance table in the garbage-photo plan §7.  
4. Confirm senior decisions: strict demo Yes/No; DB wipe Yes/No.

---

## G4 deferred

Fine-tune detector/embedder, open-set calibration, hard animal look classifier, liveness, staff nose override — see original plan Phase G4.

---

*Remediation pass applied 5 Sep 2026.*

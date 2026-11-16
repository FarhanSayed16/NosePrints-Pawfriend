# ML pilot program (nationwide accuracy track)

Lab metrics (~AUC 0.80 on public data) are **not** a field guarantee. Nationwide claims require consented real-dog collection and promote-only-if-better evaluation.

## Goals

1. Phone HTTPS acceptance (capture quality on real devices)
2. Consented pilot: **10–20 dogs**, then **~50 dogs**, multi-session where possible
3. Fine-tune embedding + recalibrate thresholds; promote ONNX only if eval wins
4. Keep staff confirmation; never claim 98–99% or “identifies all dogs”

## Capture protocol

- Owner consent recorded in-app (`CONSENT_TEXT_VERSION`)
- 3–5 nose crops per dog, varied angle/lighting
- Optional look photo (soft gate only)
- Tag `region` / `shelter_code` when known (API + registry filter)
- Prefer outdoor + indoor sessions days apart

## Acceptance before claiming field ID

- [ ] HTTPS phone capture checklist passed
- [ ] Gallery purged of junk/test dogs
- [ ] Strict demo threshold understood by staff
- [ ] Open-set / multiprint follow-ups reviewed (see experiment docs)
- [ ] New candidate ONNX evaluated offline; promoted only if better

## Ops links

- Free Public Track + experiment notes under `docs/`
- Staff queue for human-in-the-loop
- `MATCH_STRICT_DEMO` / `MATCH_THRESHOLD_STRICT` for cautious demos

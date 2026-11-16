# Retention & DPDP (India)

NosePrints stores owner contact and biometric nose embeddings for reunion. Treat both as sensitive personal data under the Digital Personal Data Protection Act, 2023.

## Consent

- Registration requires consent; `consent_given_at` and `consent_text_version` are stored on `owners`.
- Current copy version: env `CONSENT_TEXT_VERSION` (default `v1`).
- Staff match review surfaces `consent_text_version` on queue items when available.

## What we store

| Data | Purpose | Notes |
|------|---------|--------|
| Owner name/phone/email/address | Reunion contact | Revealed only after staff confirm |
| Dog profile + look photo | Directory / soft appearance | Not biometric ID |
| Nose crop + 512-d embedding | Matching | Biometric |
| Match logs | Ops audit / accuracy | Query images retained until purge |

## Erasure

- Admin Staff console → **Erasure** tab, or `DELETE /api/v1/owners/{id}`.
- Cascades dogs, nose prints, and best-effort photo deletes from storage.
- Action is written to `audit_logs` as `owner.erase`.
- Dog-only purge: admin **Registry** delete (`dog.delete` audit).

## Retention guidance (ops policy)

| Class | Suggested retention |
|-------|---------------------|
| Active registered dogs | While account active |
| Match query images | Prefer purge after staff decision + 30 days (ops) |
| Audit logs | ≥ 1 year for accountability |
| Backups | Align with Supabase PITR / export schedule |

Exact legal counsel review is still required before nationwide launch claims.

## Staff access

- Owner PII is never returned on public identify responses.
- Confirm/reject requires `staff` or `admin`.
- Erasure and registry delete require `admin`.

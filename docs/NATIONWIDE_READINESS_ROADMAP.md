# Nationwide readiness roadmap

Living checklist for scaling NosePrints / PawFriend beyond a local demo.

**Status:** Implementation landed for Staff UX (P0), RBAC + invite/reset (P1), Staff console redesign (P2), Cloud Run helper (P3), audit/erasure/region/rate-limit/pilot docs (P4). Hosting still requires Farhan’s `gcloud` + billing + object storage credentials.

## Phase status

| Phase | Goal | Done in code |
|-------|------|--------------|
| P0 | Staff UX hardening | Yes — refresh, reviewed toggle, busy/errors, `top_match_dog_id` fix |
| P1 | Roles, invite, password reset | Yes — `viewer`/`staff`/`admin`, invite/reset APIs + UI |
| P2 | Staff ops console redesign | Yes — two-pane queue, registry table, admin/erasure tabs |
| P3 | Cloud hosting | Helper script + checklist; deploy blocked until gcloud/Docker/S3 |
| P4 | Audit, DPDP UX, rate limits, ML pilot | Yes — `audit_logs`, owner erase UI, auth rate limits, region fields, pilot doc |

## Roles

| Role | Queue view | Confirm/reject | Delete dog / erase owner | Invite / roles |
|------|------------|----------------|--------------------------|----------------|
| viewer | Yes | No | No | No |
| staff | Yes | Yes | No | No |
| admin | Yes | Yes | Yes | Yes |

## Key endpoints

- `POST /api/v1/auth/invite` (admin)
- `POST /api/v1/auth/accept-invite`
- `POST /api/v1/auth/request-password-reset`
- `POST /api/v1/auth/reset-password`
- `GET /api/v1/auth/staff`, `PATCH .../role`, `POST .../deactivate`
- `GET /api/v1/auth/audit`
- `DELETE /api/v1/dogs/{id}` — admin
- `DELETE /api/v1/owners/{id}` — admin (DPDP)

## Related docs

- [CLOUD_HOSTING_CHECKLIST.md](./CLOUD_HOSTING_CHECKLIST.md)
- [RETENTION_AND_DPDP.md](./RETENTION_AND_DPDP.md)
- [SUPABASE_BACKUP_RUNBOOK.md](./SUPABASE_BACKUP_RUNBOOK.md)
- [ML_PILOT_PROGRAM.md](./ML_PILOT_PROGRAM.md)
- [DEPLOY.md](./DEPLOY.md) / [PHASE_A_DEPLOYMENT.md](./PHASE_A_DEPLOYMENT.md)

## Success criteria (nationwide)

1. Multi-admin without sharing `.env` passwords
2. Lost password recoverable (SMTP or staging link)
3. Deletes and erasures audited and admin-only
4. Public HTTPS on Cloud Run with durable photos
5. Consented pilot dogs collected before accuracy claims
6. Human-in-the-loop kept — no “identifies all dogs” claims

## Frozen until explicit approval

- Production ONNX promote without eval gates
- Nexdata purchase
- Dropping staff confirmation
- Merging into pawfriend.in monolith

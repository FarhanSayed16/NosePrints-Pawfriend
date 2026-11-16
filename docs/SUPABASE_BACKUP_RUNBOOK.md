# Supabase backup / restore runbook

## Daily / weekly ops

1. Confirm project is not paused (Supabase dashboard).
2. Enable Point-in-Time Recovery on paid plans if available.
3. Weekly: **Database → Backups** (or `pg_dump` via pooler connection on port 5432).

Example logical dump (from a trusted machine):

```bash
pg_dump "$DATABASE_URL_SYNC" -Fc -f noseprints-$(date +%Y%m%d).dump
```

Store dumps encrypted off-laptop (GCS / R2), never in git.

## Restore (high level)

1. Create a new Supabase project or empty database.
2. `pg_restore` into it; then `CREATE EXTENSION IF NOT EXISTS vector`.
3. Run Alembic: `cd backend && alembic upgrade head` (or rely on app `init_db` additive alters for staging).
4. Point Cloud Run `DATABASE_URL` at the restored DB; smoke-test `/health` and staff login.
5. Re-check object storage URLs still resolve (photos are not inside Postgres).

## Staging vs production

- Separate projects; separate JWT secrets.
- After restore drills, rotate any credentials that were exposed in logs.

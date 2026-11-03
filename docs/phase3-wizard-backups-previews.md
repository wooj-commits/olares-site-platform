# Phase 3 — New-site wizard, backups, PR previews

## New-site wizard (console) — shipped

UI **New site** → pick starter → **Generate chart tgz**:

1. Copies embedded `chart/site-template` + `starters/<id>` into Site Console appData
2. Replaces `SITE_*` placeholders
3. Packages `{app}-{ver}.tgz` for Market Upload / Deploy download

APIs: `GET /api/wizard/starters`, `POST /api/wizard/plan`, `POST /api/wizard/generate`, `GET /api/wizard/download/...`

## Backups — shipped (app-level)

**Path:** each site that has Postgres/MinIO exposes `POST /api/admin/backup` (Bearer `BACKUP_TOKEN`).

- Demo: `pg_dump` of `DATABASE_URL` + MinIO object tree → `.tar.gz`
- Site Console: configures `entrance_url` + `backup_token` (stored under appData; never logged), calls the app endpoint, stores archives under `/app/data/backups/`
- Also lists Olares Settings backup plans (`olares-cli settings backup plans list`) for OS-level restic/kopia plans (create those in Settings → Backup SPA)

Restore is still manual (psql + mc/cp) for MVP.

## PR preview deploys — still not automated

Each PR would need a unique chart `metadata.name` / appid, Market install, and Tunnel entrance. Prefer promote `main` only; optional later: shared `preview` app overwritten per PR.

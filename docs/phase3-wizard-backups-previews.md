# Phase 3 — New-site wizard, backups, PR previews

## New-site wizard (console)

API stubs in siteconsole (`/api/wizard/*`): pick starter → generate chart name checklist → link to GitHub Actions publish → Market upload/install instructions. Full auto-clone of starters onto GitHub needs a GitHub App token (optional `GITHUB_TOKEN` already supported for releases).

## Backups

Plan: `pg_dump` of middleware Postgres DB + tar of MinIO `userspace.appData/<app>` into `/app/data/backups/` on siteconsole or a dedicated backup job. Restore is manual Market/SQL for MVP. Not edge S3 Dokploy parity.

## PR preview deploys — feasibility

**Hard / skip automated MVP.** Each PR would need a unique chart `metadata.name` / appid, a Market install of an ephemeral chart, and Tunnel entrance. Olares Market upload + install is slow, allowlist/CLI privileges apply, and cleaning up failed previews risks touching other apps. Prefer: document “promote main only”; optional later: one shared `preview` app overwritten per PR (lossy) or manual chart name `app-pr-N`.

Recommended: **document why not** for full Dokploy-style PR previews; ship wizard + backup dump API first.

# New site checklist (Olares multi-runtime platform)

Host any runtime the way Vercel/Render would: **bring a Dockerfile**, or let CI **auto-build with Nixpacks** (fallback: Cloud Native Buildpacks).

## Stack options

| Path | When |
|------|------|
| Copy a starter from `starters/*` | Fastest — Dockerfile + `/api/health` included |
| Existing app with Dockerfile | Point GH Actions / chart at that context |
| No Dockerfile | CI uses Nixpacks, then Buildpacks |

**End-to-end proof apps in this repo**

- `apps/demo` — Next.js + Better Auth + system Postgres + bundled MinIO
- `apps/fastapi-hello` — FastAPI second-runtime proof (no DB)

## Prerequisites

1. Olares ≥ 1.12.7
2. Do **not** depend on Market MinIO/Postgres apps (Market MinIO mirrors can 404; Postgres is system middleware)
3. GHCR push rights

## 1. Pick a starter (or your app)

```bash
cp -R starters/python-fastapi ~/code/mysite   # or nextjs, go, django, …
cd ~/code/mysite
# edit; keep GET /api/health returning 2xx
```

Ports by starter: see `starters/README.md`.

## 2. Chart from site-template

```bash
cp -R chart/site-template chart/mysite
# Replace SITE_* placeholders
# values.yaml:
#   port: <listen port>
#   healthPath: /api/health
#   postgres.enabled: true|false   # also add/remove middleware.postgres in OlaresManifest
#   storage.enabled: true|false    # bundled MinIO on userspace appData; S3 env injected
#   resources / env as needed
```

AUTH_SECRET (and MinIO password when storage is on) are **auto-generated** (`lookup` + `randAlphaNum`) — no typing at install.

## 3. CI → public GHCR + chart `.tgz`

Workflow `.github/workflows/publish.yml`:

1. For each matrix context: if `Dockerfile` → docker buildx; else Nixpacks; else pack/Buildpacks
2. Push `ghcr.io/<owner>/<image>:<version>` (+ `:latest`), attempt public visibility
3. `helm package` charts → release assets

For a **new single-app repo**, copy the workflow and set matrix to one context `.`.

## 4. Install on Olares

1. Download the chart `.tgz` from the GitHub Release
2. Market → My Olares → **Upload** → Install
3. Optional Settings only: OAuth client IDs/secrets. Auth base URL is derived from the request host (`*.woojinc1205.olares.com`); `BETTER_AUTH_URL` is an optional static fallback only
4. Wait until **running**; entrance is **public** by default

No Market MinIO install required for the demo (storage is in-chart). System Postgres is provisioned from the `middleware.postgres` block alone (no `options.dependencies` middleware entries).

## 5. OAuth (Next.js / Better Auth apps only)

Callbacks:

- `{public_base}/api/auth/callback/google`
- `{public_base}/api/auth/callback/github`

Paste credentials in Settings → Applications → [app]. Leave empty to keep social login disabled.

## 6. Acceptance tests (Next.js demo)

```bash
BASE=https://<entrance-host>   # from Settings / entrances list

curl -fsS "$BASE/api/health" | jq .
# register / login / notes / upload — see prior checklist examples
```

FastAPI hello: `curl -fsS "$BASE/api/health"` → `{"ok":true,"runtime":"fastapi-hello",...}`.

## 7. Non-destructive upgrade

Upload new `.tgz` / upgrade only this app. Do not wipe Postgres DB or `userspace.appData` MinIO data. Re-hit `/api/health`.

## Auto-deploy routine

Trigger: `{ "type": "github", "repo": "wooj-commits/olares-site-platform", "events": ["ci-passed"], "ciBranch": "main" }`  
(Prompt unchanged — upgrade `olaresdemo` after green main.)

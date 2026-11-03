# New site checklist (Olares native platform)

Stack for the demo and recommended default: **Next.js 15 (App Router) single container** with Better Auth, system Postgres middleware, and Market MinIO middleware.

## Prerequisites

1. Olares ≥ 1.12.7 with admin Market access.
2. **MinIO** installed from Market (admin middleware). Do not stop/uninstall other apps.
3. GitHub repo + GHCR push rights (`packages: write`).
4. A 32+ character `AUTH_SECRET` kept only in a secure store (never commit).

## 1. Scaffold from the reusable chart

```bash
cp -R chart/site-template chart/mysite
# Replace SITE_* / OWNER / REPO / OLARES_ID placeholders (see chart/site-template/README.md)
```

Or fork `apps/demo` and point `chart/*/values.yaml` image at your GHCR repo.

## 2. App code expectations

- `GET /api/health` — returns 200 when Postgres is reachable (MinIO status reported in JSON).
- Better Auth at `/api/auth/*` with email/password always on.
- Google / GitHub OAuth only when both `*_CLIENT_ID` and `*_CLIENT_SECRET` are set.
- Session-scoped Postgres CRUD and MinIO keys under `{userId}/…`.

## 3. CI → public GHCR + chart artifact

Push to `main`. Workflow `.github/workflows/publish.yml`:

1. Builds `linux/amd64` image → `ghcr.io/<owner>/<repo>:<version>` + `:latest`.
2. Attempts to set package visibility **public**.
3. `helm package chart/<app>` and uploads the `.tgz` as a release / workflow artifact.

After first publish, confirm the package is public in GitHub Packages (UI) if the API patch is a no-op.

## 4. Install on Olares

1. Market → ensure **MinIO** is installed (middleware).
2. Market → My Olares → **Upload** the chart `.tgz`.
3. Install. When prompted, set:
   - `AUTH_SECRET` — paste from your secure store
   - `BETTER_AUTH_URL` — `https://web.<app>.<olares-id>.olares.com` (no trailing slash)
4. Leave Google/GitHub empty until OAuth apps are ready.
5. Wait until app state is **running**. Entrance is **public** by default in the chart.

Confirm URL (typical pattern):

`https://web.<appid>.<olares-id>.olares.com`

## 5. OAuth (optional, later)

Callback URLs (Better Auth):

- Google: `{BETTER_AUTH_URL}/api/auth/callback/google`
- GitHub: `{BETTER_AUTH_URL}/api/auth/callback/github`

Where credentials go:

1. Create OAuth clients in Google Cloud Console / GitHub Developer Settings with the callbacks above.
2. Paste `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` and `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` into **Settings → Applications → [app] → env**.
3. Restart / wait for applyOnChange so the pod picks them up. Buttons appear only when both id+secret are present.

## 6. Acceptance tests

```bash
BASE=https://web.<appid>.<olares-id>.olares.com

# Health
curl -fsS "$BASE/api/health" | jq .

# Register + login (cookie jar)
curl -fsS -c /tmp/od.jar -H 'content-type: application/json' \
  -d '{"email":"demo@example.com","password":"demopass1","name":"Demo"}' \
  "$BASE/api/auth/sign-up/email"
curl -fsS -c /tmp/od.jar -b /tmp/od.jar -H 'content-type: application/json' \
  -d '{"email":"demo@example.com","password":"demopass1"}' \
  "$BASE/api/auth/sign-in/email"

# Notes CRUD
curl -fsS -b /tmp/od.jar -H 'content-type: application/json' \
  -d '{"title":"persist","body":"after restart"}' "$BASE/api/notes"
curl -fsS -b /tmp/od.jar "$BASE/api/notes" | jq .

# Upload
echo hello > /tmp/hello.txt
curl -fsS -b /tmp/od.jar -F file=@/tmp/hello.txt "$BASE/api/files" | jq .

# Data survives restart: Settings → stop/start app (or market resume), then re-list notes/files.
```

## 7. Non-destructive upgrade (auto-deploy target)

When CI on `main` is green and a new image+chart are published:

1. Do **not** uninstall other apps; do **not** delete the Postgres DB or MinIO bucket.
2. Upload the new chart `.tgz` (or Market upgrade if listed).
3. Confirm image tag in values matches the green build.
4. Upgrade / resume only this app; wait for `running`.
5. Re-hit `/api/health` and spot-check notes + files.

## Auto-deploy routine (create separately)

See repo root `README.md` for the exact routine prompt + GitHub `ci-passed` / `main` trigger shape.

# site-template

Language-agnostic Olares chart for any container image (Dockerfile, Nixpacks, or Cloud Native Buildpacks).

## Placeholders

| Token | Example |
|-------|---------|
| `SITE_NAME` | `mysite` |
| `SITE_TITLE` | `My Site` |
| `SITE_DESCRIPTION` | short blurb |
| `SITE_DEVELOPER` / `OWNER` / `REPO` / `SITE_IMAGE` | coords |
| Entrance `port` in OlaresManifest | match `values.port` |

## values.yaml knobs

- `port`, `healthPath` — probe + Service
- `resources`, `env` — CPU/mem + extra env
- `postgres.enabled` — system middleware (also edit/remove `middleware:` in OlaresManifest)
- `storage.enabled` — bundled MinIO on `userspace.appData` (S3 env injected; swap to shared MinIO later by pointing `storage.endpoint`)

AUTH_SECRET (and MinIO password when storage is on) are generated once via `lookup` + `randAlphaNum`.

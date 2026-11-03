# olares-site-platform

Multi-runtime native Olares hosting (Vercel/Render-class): **any Dockerfile**, or **Nixpacks / Cloud Native Buildpacks** when none exists.

| Piece | Location |
|-------|----------|
| Next.js e2e demo (auth + Postgres + MinIO) | `apps/demo` |
| FastAPI second-runtime proof | `apps/fastapi-hello` |
| Runtime starters | `starters/*` |
| Installable charts | `chart/olaresdemo`, `chart/fastapihello` |
| Copy-paste chart | `chart/site-template` (port, healthPath, env, resources, optional postgres/storage) |
| Checklist | `docs/new-site-checklist.md` |

## Images (public GHCR)

- `ghcr.io/wooj-commits/olares-site-platform` — Next.js demo
- `ghcr.io/wooj-commits/olares-site-platform-fastapi` — FastAPI hello

## Design notes (0.1.1+)

- **System Postgres** via `middleware.postgres` only — no Market postgres/minio `options.dependencies`
- **Bundled MinIO** (`docker.io/beclab/minio-minio`) on `userspace.appData` — Market MinIO mirrors can 404
- **AUTH_SECRET** auto-generated (Helm `lookup` + `randAlphaNum`), persists across upgrades

## OAuth callbacks (demo)

- `https://<entrance>/api/auth/callback/google`
- `https://<entrance>/api/auth/callback/github`

## Auto-deploy routine (create in Grok Bot)

**Trigger:**
```json
{"type":"github","repo":"wooj-commits/olares-site-platform","events":["ci-passed"],"ciBranch":"main"}
```

**Prompt:**
```
When CI passes on main for wooj-commits/olares-site-platform, non-destructively upgrade the Olares demo app olaresdemo on woojinc1205: download the latest chart .tgz release asset (or workflow artifact), upload/upgrade via Market or olares-cli without uninstalling other apps or wiping Postgres/MinIO data, wait until the app is running, then hit the demo entrance /api/health and report status. If olares-cli needs profile login or Market auth, pause and ask Woojin in this chat. Never print or commit secrets. Deliver the result to the user in this chat; if nothing changed beyond a green build already deployed, say so briefly.
```

## License

Apache-2.0

## Site Console

Dokploy-like private admin UI for this Olares: list/stop/resume sites, deploy from GitHub release charts, edit env vars, domain wizard (third-level + guided custom DNS), redirects, logs.

- App: `apps/siteconsole` · Chart: `chart/siteconsole`
- Docs: [`docs/site-console.md`](docs/site-console.md) · Allowlist: [`docs/site-console-admin-steps.md`](docs/site-console-admin-steps.md)
- Image: `ghcr.io/wooj-commits/olares-site-console`


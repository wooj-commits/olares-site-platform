# Site Console (Dokploy-like manager on Olares)

Private, admin-only Olares app (`siteconsole`) that manages your sites through `olares-cli` with `permission.loginOlaresCLI: true` — same pattern as Mode Switch.

## What it does (Phase 1)

| Feature | How |
|---|---|
| Site list + status | `olares-cli market list --mine` / `market status` |
| Stop / resume | `market stop|resume --watch` (refuses to stop itself) |
| Deploy / rollback | Download chart `.tgz` from GitHub Releases → `market upload` → `upgrade|install -s upload --watch` |
| Env editor | `settings apps env get|set` (editable vars only) |
| Memorable domain | `settings apps domain set --third-level` → `*.woojinc1205.olares.com` |
| Custom domain | Cert/key upload + CNAME cheat-sheet (Squarespace / Google paste) + `domain finish` + poll |
| Redirects | Rule table → `REDIRECT_RULES_JSON` env on the site app |
| Pod logs | `cluster pod list` + `cluster pod logs` |
| Deploy history | Stored on appData; optional webhook |

## Allowlist (required once)

ConfigMap `login-olares-cli-allow-list` in namespace **`os-framework`** must include `siteconsole` **without removing** existing entries:

```yaml
LOGIN_OLARES_CLI_ALLOW_LIST: "lares,modeswitch,siteconsole"
```

Then restart (both):

1. StatefulSet / workload **`app-service`** in `os-framework`
2. Deployment **`market-deployment`** in `os-framework` (or the Market API deployment name shown in Control Hub)

UI path: Control Hub → Browse → `os-framework` → ConfigMaps → `login-olares-cli-allow-list` → edit → Confirm → restart the two workloads above.

See also `docs/site-console-admin-steps.md`.

## Install

1. Complete the allowlist + restarts.
2. Download `siteconsole-0.1.0.tgz` from the GitHub Release (or build with `helm package chart/siteconsole`).
3. Market → My Olares → **Upload** → Install.
4. Open **Site Console** from the Desktop (private entrance — Olares login; admin only).

Image: `ghcr.io/wooj-commits/olares-site-console:0.1.0`

## Phases 2–3 (roadmap in-repo)

- **Phase 2:** Prometheus + Grafana from Market; `/metrics` on site-template/starters; front-end analytics beacon; deploy notifications (webhook already wired).
- **Phase 3:** New-site wizard from `starters/*`; pg_dump + MinIO backups; PR preview deploys (document if Tunnel/chart limits block it).

## Out of scope

- Installing Dokploy / Coolify / CapRover on Olares
- Automatic Squarespace DNS writes (no public end-user API)
- Guaranteeing every custom Tunnel domain

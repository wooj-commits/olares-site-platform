# Dokploy → Olares Site Console: feasibility (research only)

Date: 2026-11-03 (America/New_York).

**BUILD STATUS:** Phase 1 Site Console implemented in-repo (`apps/siteconsole`, `chart/siteconsole`). Woojin approved all phases.

## Bottom line

Do **not** install Dokploy (Docker/Swarm/Traefik). Build a native Olares **Site Console** chart that wraps `olares-cli` (same pattern as `modeswitch`: `permission.loginOlaresCLI: true` + ConfigMap `os-framework/login-olares-cli-allow-list`) and GitHub/GHCR. That can cover most of what Woojin asked for (list apps, deploy/redeploy, env vars, guided domains, logs, basic metrics, app-level redirects). Full Dokploy parity is not possible on Olares Tunnel + Kubernetes.

## Dokploy feature inventory → Olares mapping

| Dokploy feature | Olares surface | Feasibility | Notes |
|---|---|---|---|
| App list / status | `olares-cli market list --mine`, `market status`, Settings apps list | **Feasible** | Proven by modeswitch |
| Deploy / stop / resume / uninstall | `market upload` + `market upgrade -s upload`, `market stop/resume`, settings apps suspend/resume | **Feasible** | Needs allowlist + one-time profile login (or standing CLI loginOlaresCLI) |
| Redeploy from GitHub | Existing GH Actions → GHCR + chart `.tgz` release; console triggers upgrade of uploaded chart | **Feasible** | Build stays in GitHub; console only applies chart |
| Rollback | Re-upgrade older release chart / image tag from GH releases | **Partial** | Not container-snapshot rollback; upload source allows same-version re-apply |
| Build (Docker/Nixpacks/Buildpacks) | Already in `olares-site-platform` CI | **Feasible (off-box)** | Keep builds on GitHub, not on Olares |
| Env vars UI | `olares-cli settings apps env get/set` → `PUT /api/env/apps/{app}/env` | **Feasible** | Only vars declared editable in OlaresManifest; cannot invent undeclared keys; Apply may restart app |
| Domains: memorable route ID | `settings apps domain set --third-level` | **Feasible** | Instant; no DNS; e.g. `demo.woojinc1205.olares.com` |
| Domains: custom FQDN | `domain set --third-party` + cert/key PEM + CNAME + `domain finish` | **Partial** | Requires public entrance + RSA cert/key. `collaborate.thinkermaker.studio` worked; `vault.woojincho.com` never routed via Tunnel — treat Tunnel custom domains as unreliable and always verify |
| DNS record automation | Registrar APIs | **Not feasible (current DNS)** | Squarespace has no public end-user DNS CRUD API (reseller Domains Management ≠ zone API). Guided copy-paste only. Optional later: move zone to Cloudflare/Cloud DNS for API |
| Redirects (Traefik regex) | No Traefik control on Olares | **Partial via app** | Redirect rule table in console → write into site chart/app middleware, or tiny dedicated redirector app. Not edge Traefik rules |
| Real-time logs | `olares-cli cluster pod logs` / Control Hub | **Feasible** | Via loginOlaresCLI cluster APIs; stream in console UI |
| CPU/mem/disk/net monitoring | Control Hub + optional Prometheus/Grafana Market apps | **Partial → Feasible** | Built-in Dashboard graphs exist; request-level RPS/latency needs Prometheus + app `/metrics` + optional frontend analytics |
| Databases (PG/MySQL/Mongo/Redis provision) | `middleware.postgres` in chart; bundled MinIO | **Partial** | Stick to system Postgres + in-chart MinIO. Full multi-engine DB PaaS = out of scope |
| DB/volume backups | Manual pg_dump to MinIO / PVC snapshots | **Partial (later)** | No Dokploy S3 backup UX yet |
| Docker Compose / Swarm / multi-node | N/A | **Not possible** | Conflicts with Olares K8s model |
| Traefik file config / ports publish | N/A | **Not possible** | Entrances replace Traefik |
| Templates / one-click OSS | Market charts + `starters/*` | **Partial** | Console can clone site-template + starters; not Dokploy template marketplace |
| Webhooks (Git push deploy) | GitHub Actions + optional Grok routine; console webhook endpoint | **Feasible** | Already partially wired for olaresdemo |
| Notifications (Slack/Discord/email) | Console outbound webhooks / email | **Feasible (later)** | Easy after deploy pipeline exists |
| Multi-user / roles | Olares org users + private entrance + `onlyAdmin` | **Partial** | Rely on Olares auth; no Dokploy enterprise RBAC clone in MVP |
| Preview deployments (PR) | Extra chart installs per PR | **Later / hard** | Possible with ephemeral charts; skip MVP |
| Terminal into container | Control Hub / kubectl exec | **Later** | Needs careful privilege; skip MVP |
| Multi-server remote | N/A | **Not applicable** | Single Olares |

## Permissions (honest)

A third-party Market app **can** manage other apps **if and only if**:

1. `OlaresManifest.permission.loginOlaresCLI: true`
2. Admin adds the app name to ConfigMap `login-olares-cli-allow-list` in `os-framework` (keep `lares`), then restarts `app-service`
3. Preferably `onlyAdmin: true` + private entrance

This is the proven modeswitch path. Raw kube ServiceAccount cluster-admin for arbitrary apps is **not** the sanctioned model (modeswitch sets `automountServiceAccountToken: false` and uses CLI credentials instead). Without the allowlist, the console cannot stop/upgrade/env/domain other apps.

## DNS & redirects plan

| Domain | Provider | Automation |
|---|---|---|
| `woojincho.com` | Squarespace | Guided TXT/CNAME/NS only. No reliable public DNS API. |
| `thinkermaker.studio` | Historically Google Domains; journal shows Squarespace DNS used for Collab Draw | Same: guided records. If NS moved to Cloudflare/Cloud DNS later → API automation becomes feasible. |

**Recommended console DNS UX**

1. User picks entrance → console sets third-level (instant) and/or third-party domain via CLI.
2. Console shows exact records to paste (CNAME target from `domain get`, or Space host-domain TXT+NS if using Olares Space subdomain delegation).
3. User pastes at Squarespace; console polls `domain get` / `domain finish` and shows status.
4. **Do not promise** vault-style Tunnel custom domains always work; keep `*.woojinc1205.olares.com` as the guaranteed URL.
5. **Redirects:** store rules in console DB (Postgres middleware) and either (a) push as env/`REDIRECT_RULES_JSON` into the site app, or (b) deploy a small `redirector` chart that owns apex/www → target. Prefer (a) for per-site path redirects.

## Recommended MVP (phased)

### Phase 0 — Privileges & skeleton (~0.5–1 day)
- Chart `siteconsole` with `loginOlaresCLI`, private + onlyAdmin entrance, Better Auth or Olares private auth.
- Document allowlist steps (copy modeswitch ADMIN-UI-STEPS).
- Wire CLI: `market list --mine`, `status`.

### Phase 1 — Manage sites Woojin asked for (~3–5 days) **← ship this first**
- Site list (platform charts tagged / name prefix / registry of managed apps).
- Env editor (get/set declared editable vars) with restart awareness.
- Deploy / redeploy: pick GH release chart → `market upload` + `upgrade -s upload --watch`.
- Rollback: pick older release version and upgrade.
- Domain panel: third-level set; third-party wizard with cert upload + CNAME cheat-sheet + finish/poll.
- Redirect rules table (JSON → site env or redirector).
- Pod logs viewer (tail/follow).

### Phase 2 — Metrics & notifications (~2–4 days)
- Embed/link Control Hub-style CPU/mem; install Prometheus+Grafana if wanted.
- Add `/metrics` to site-template; optional lightweight page-view beacon.
- Deploy success/fail notifications (email/Slack webhook).

### Phase 3 — Nice-to-haves (later)
- New-site wizard from starters; GitHub App connect; PR previews; pg_dump backups to MinIO; multi-user roles beyond Olares admin.

## Out of scope / refuse
- Installing Dokploy, Coolify, CapRover, or any Docker-Swarm control plane on this Olares.
- Claiming Squarespace DNS auto-write.
- Guaranteeing every custom domain via Olares Tunnel (known miss: vault.woojincho.com).

## Effort summary
| Phase | Rough effort | Delivers |
|---|---|---|
| 0 | 0.5–1 day | Privileged console shell |
| 1 | 3–5 days | Full manage: list, deploy, rollback, env, domains guide, redirects, logs |
| 2 | 2–4 days | Metrics + alerts |
| 3 | open | Templates, previews, backups |

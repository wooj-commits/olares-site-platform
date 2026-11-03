# Install handoff (executor blocked on olares-cli profile)

## Ready artifacts
- Repo: https://github.com/wooj-commits/olares-site-platform
- Image (public): `ghcr.io/wooj-commits/olares-site-platform:0.1.0` (+ `:latest`)
- Chart: https://github.com/wooj-commits/olares-site-platform/releases/tag/v0.1.0 → `olaresdemo-0.1.0.tgz`
- Local chart copy: `/workspace/olares-site-platform/dist/olaresdemo-0.1.0.tgz`
- AUTH_SECRET: `/workspace/secrets/olares-demo-auth-secret` (chmod 600; do not print)

## Parent must finish (browser or olares-cli)
1. `olares-cli profile login --olares-id woojinc1205` (password via Secure Form / Vault; never argv)
2. Market: install **MinIO** middleware if absent — do not stop/uninstall other apps
3. Market → upload `olaresdemo-0.1.0.tgz` → install **olaresdemo**
4. At install / Settings set:
   - `AUTH_SECRET` = contents of the secret file
   - `BETTER_AUTH_URL` = `https://web.olaresdemo.woojinc1205.olares.com` (confirm actual entrance URL after install via `settings apps entrances list olaresdemo`)
5. Confirm entrance `web` is **public**
6. Acceptance tests from docs/new-site-checklist.md

## Expected demo URL
https://web.olaresdemo.woojinc1205.olares.com

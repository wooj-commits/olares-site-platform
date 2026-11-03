# Install Phase 1 now (Market UI — no olares-cli profile)

Charts ready under `/workspace/olares-site-platform/dist/` after `gh release download`,
or from https://github.com/wooj-commits/olares-site-platform/releases/tag/v0.1.5
(and the next v0.1.6 release once CI finishes for metrics bump).

## A. Allowlist (required for Site Console CLI)

Control Hub → Browse → `os-framework` → ConfigMaps → `login-olares-cli-allow-list`:

```yaml
LOGIN_OLARES_CLI_ALLOW_LIST: "lares,modeswitch,siteconsole"
```

Then restart **`app-service`** and **`market-deployment`** in `os-framework`. Do not remove `lares` or `modeswitch`.

## B. Market Upload / Install / Update

1. Desktop → Market → My Olares → Upload custom app package.
2. Upload **`siteconsole-0.1.0.tgz`** (or `0.1.1` after next release) → **Install** (private, admin-only).
3. Upload **`olaresdemo-0.1.5.tgz`** (or `0.1.6`) → choose **Update** on the already-installed Olares Demo (do not uninstall).
4. Wait until both show Running.

## C. Verify

```bash
# demo (replace host if entrance changed)
curl -sk --resolve 1c5eaad0.woojinc1205.olares.com:443:100.49.108.29 \
  https://1c5eaad0.woojinc1205.olares.com/api/health

# siteconsole: open private Desktop icon "Site Console" (Olares login)
# or curl its entrance host /healthz once known
```

## D. Optional headless (Woojin)

```bash
olares-cli profile login --olares-id woojinc1205
# password + TOTP if 2FA; never paste secrets into chat
```

After login, future auto-deploys and agent upgrades work without Market UI.

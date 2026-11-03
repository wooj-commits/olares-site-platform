# Site Console — Admin UI steps (allowlist)

Do this **once** before or right after installing `siteconsole`. The env **replaces** the default list; it does not merge — keep every app that already needs CLI login.

## 1. Update LOGIN_OLARES_CLI_ALLOW_LIST

1. Open **Control Hub** on the Olares Desktop.
2. Left nav → **Browse**.
3. Expand namespace **`os-framework`**.
4. **ConfigMaps** → **`login-olares-cli-allow-list`**.
5. Click **edit** (edit_square).
6. Under `data`, set **exactly** (append `siteconsole`, keep `lares` and `modeswitch`):

```yaml
LOGIN_OLARES_CLI_ALLOW_LIST: "lares,modeswitch,siteconsole"
```

7. **Confirm**.

## 2. Restart so the allowlist is loaded

Still under **`os-framework`**:

1. Find **`app-service`** (StatefulSet or Workload) → **Restart** (confirm the name).
2. Find **`market-deployment`** (Deployment) → **Restart**.
3. Wait until both are healthy/green.

Without these restarts, `siteconsole` will install but `olares-cli` calls from the pod will be denied.

## 3. Install / open Site Console

Market → Upload `siteconsole-*.tgz` → Install → open the private **Site Console** entrance.

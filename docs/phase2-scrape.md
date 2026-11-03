# Phase 2 — Scraping site `/metrics` on Olares

## Sanctioned path (no NetworkPolicy edits)

KubeSphere’s `prometheus-k8s` (namespace `kubesphere-monitoring-system`) discovers targets via **ServiceMonitor** objects labeled:

```yaml
metadata:
  labels:
    app.kubernetes.io/vendor: kubesphere
```

Each site chart ships:

1. **Service** annotations `prometheus.io/scrape|port|path` (annotation SD fallback)
2. **ServiceMonitor** in the app namespace selecting `app: <name>`, endpoint port `http`, path `/metrics`

Grafana datasource remains the Prometheus API entrance (`https://4ae9f19e1.<id>.olares.com`).

## Metric names (site apps)

| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | counter | `method`, `path`, `status` |
| `http_errors_total` | counter | `method`, `path` |
| `http_request_duration_seconds_sum` / `_count` | counter | `method`, `path` |

Kubernetes apiserver also exposes `http_request_duration_seconds_*`. Dashboard panels **must** filter `service=~"olaresdemo\|fastapihello\|siteconsole"` (or the ServiceMonitor job name) so Latency is not a false positive from the control plane.

## After Market Update

1. Update olaresdemo / fastapihello / siteconsole charts
2. In Prometheus UI (or Grafana Explore): `http_requests_total{service="olaresdemo"}`
3. Re-import `docs/grafana/olares-sites-dashboard.json`
4. If targets stay empty after ~2m, report — do **not** open NetworkPolicies without review (operator scrape may need a Control Hub exception)

## Demo paths

- Prometheus path: **`/metrics`** (also available as `/api/metrics`)

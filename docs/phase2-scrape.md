# Phase 2 — Site metrics on Olares

## Diagnosis (2026-11-03, woojinc1205)

- App `/metrics` works (public demo/fastapihello return Prometheus text).
- Grafana → Prometheus API entrance works in-browser, but from the box the API is Authelia-gated (302); no kubectl on the box.
- After installing ServiceMonitors (`app.kubernetes.io/vendor: kubesphere` + `prometheus.io/*` annotations), Explore still had **no** `http_requests_total` series.
- Conclusion: **prometheus-k8s is not scraping user app namespaces** (ServiceMonitors stripped and/or namespace selector / NetworkPolicy). **Do not change NetworkPolicies** without an explicit review.

## Fallback (shipped): Site Console poller

Site Console (`0.1.6+`) polls each site’s `/metrics` every ~20s:

1. Default public URLs for `olaresdemo` / `fastapihello`, plus `http://127.0.0.1:8080/metrics` for itself
2. Refreshes entrance URLs via `olares-cli settings apps entrances list` every 5m
3. Stores samples in SQLite under appData (`metrics.sqlite`)
4. **Metrics** tab: request rate, latency, error rate charts
5. Combined exposition: `GET /federate` (and `/api/metrics/federate`)

Optional: `PUT /api/metrics/targets` with `{ "targets":[{"app":"…","url":"https://…/metrics"}], "interval_s":20 }`.

Charts shipped earlier still work **if** cluster scrape is fixed later; until then use the console Metrics tab.

# Phase 2 — Metrics & notifications (after Site Console Phase 1 is live)

## Backend `/metrics`

Add Prometheus text exposition to site-template apps:

- Counters: `http_requests_total{method,path,status}`
- Histogram: `http_request_duration_seconds`
- Counter: `http_errors_total`

Wire into Next.js demo (instrumentation) and FastAPI starters. Site Console can link Grafana or embed panels.

## Install on Olares (approved)

1. Market → install **Prometheus** (if available) and **Grafana**.
2. Scrape site pods on `/metrics` (or pushgateway if scrape networking is limited).
3. Import dashboard JSON under `docs/grafana/` (added in Phase 2 implementation).

## Front-end analytics

Self-hosted page views / web vitals / JS errors via a light collector endpoint on Site Console (`POST /api/analytics/collect`) or a custom Umami chart — prefer console collector first to avoid another Market dependency.

## Notifications

`NOTIFY_WEBHOOK_URL` already on siteconsole; Phase 2 adds email option and richer deploy history UI.

## Scrape (implemented)

See `docs/phase2-scrape.md`. Charts ship ServiceMonitor (`app.kubernetes.io/vendor: kubesphere`) + `prometheus.io/*` annotations. Dashboard filters by `service`.


## Fallback when cluster scrape fails

Site Console polls `/metrics` into SQLite and charts in the **Metrics** tab (`/federate` for combined text). See `docs/phase2-scrape.md`.

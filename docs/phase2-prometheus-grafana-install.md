# Phase 2 — Prometheus + Grafana on Olares (browser)

Woojin approved Market installs. This executor cannot drive Control Hub/Market UI.

## Browser steps (parent / Woojin)

1. Desktop → **Market** → search **Prometheus**. If listed, Install (CPU). Note entrance URL.
2. Market → search **Grafana**. Install. Open and set admin password on first login (use vault; never paste in chat).
3. In Grafana → Connections → Data sources → Prometheus → URL = in-cluster Prometheus service (from Control Hub / app docs; often `http://prometheus:9090` or the Market chart’s service DNS).
4. Dashboards → Import → upload `docs/grafana/olares-sites-dashboard.json`.
5. Scrape config: add jobs for site pods’ `/metrics` (olaresdemo, fastapihello, siteconsole). If Market Prometheus has no scrape UI, document targets in `prometheus.yml` via Control Hub ConfigMap edit, or use a pushgateway later.

If Market has no Prometheus/Grafana charts, fall back to custom charts in a follow-up (out of this increment) or Control Hub built-in CPU/mem only.

## App side (already in repo)

- siteconsole, fastapi-hello, demo expose `/metrics` (Prometheus text).
- Site Console: `POST /api/analytics/collect`, `GET /api/analytics/summary` for front-end beacons.

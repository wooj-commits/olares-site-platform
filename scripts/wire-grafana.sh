#!/usr/bin/env bash
# Wire Prometheus datasource + import olares-sites dashboard into Grafana.
# Requires: GF_USERNAME/GF_PASSWORD in env (from secrets file) AND either
#   - GRAFANA_HOST reachable without Authelia, OR
#   - COOKIE jar from an Olares Authelia session (COOKIE_JAR path).
# Usage:
#   set -a; source /workspace/secrets/grafana-admin; set +a
#   GRAFANA_HOST=d9c0e52d.woojinc1205.olares.com \
#   PROM_URL=http://prometheus:9090 \
#   COOKIE_JAR=/path/to/cookies.txt \
#   ./scripts/wire-grafana.sh
set -euo pipefail
: "${GF_USERNAME:?}" "${GF_PASSWORD:?}"
GRAFANA_HOST=${GRAFANA_HOST:-d9c0e52d.woojinc1205.olares.com}
PROM_URL=${PROM_URL:-http://prometheus:9090}
RESOLVE=${RESOLVE:-${GRAFANA_HOST}:443:100.49.108.29}
DASH=$(dirname "$0")/../docs/grafana/olares-sites-dashboard.json
CURL=(curl -sk --resolve "$RESOLVE")
if [[ -n "${COOKIE_JAR:-}" ]]; then
  CURL+=(-b "$COOKIE_JAR" -c "$COOKIE_JAR")
fi
CURL+=(-u "${GF_USERNAME}:${GF_PASSWORD}")

code=$("${CURL[@]}" -o /tmp/gf-h.json -w '%{http_code}' "https://${GRAFANA_HOST}/api/health" || true)
echo "grafana /api/health -> $code"
if [[ "$code" != "200" ]]; then
  echo "Blocked (likely Olares Authelia). Open Grafana in a logged-in browser, export cookies to COOKIE_JAR, retry."
  exit 2
fi

# Upsert Prometheus datasource
"${CURL[@]}" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Prometheus\",\"type\":\"prometheus\",\"url\":\"${PROM_URL}\",\"access\":\"proxy\",\"isDefault\":true}" \
  "https://${GRAFANA_HOST}/api/datasources" -o /tmp/gf-ds.json -w 'datasource:%{http_code}\n' || true

# Import dashboard
payload=$(python3 - <<PY
import json
from pathlib import Path
dash=json.loads(Path("$DASH").read_text())
print(json.dumps({"dashboard": dash, "overwrite": True, "folderId": 0}))
PY
)
"${CURL[@]}" -H 'Content-Type: application/json' -d "$payload" \
  "https://${GRAFANA_HOST}/api/dashboards/db" -o /tmp/gf-dash.json -w 'dashboard:%{http_code}\n'
echo done

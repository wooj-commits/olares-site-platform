#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/apps/siteconsole/wizard-assets"
rm -rf "$DEST"
mkdir -p "$DEST/chart" "$DEST/starters"
cp -a "$ROOT/chart/site-template" "$DEST/chart/site-template"
cp -a "$ROOT/starters/." "$DEST/starters/"
echo "Prepared $DEST"

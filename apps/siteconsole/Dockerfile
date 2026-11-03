FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SITECONSOLE_DATA_DIR=/app/data \
    PORT=8080 \
    OLARES_CLI=/usr/local/bin/olares-cli \
    WIZARD_ASSETS=/srv/wizard-assets

WORKDIR /srv

# Install olares-cli from npm (loginOlaresCLI mounts credentials at runtime).
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg tar \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @olares/cli@1.12.7-cli.10 \
 && OCLI="$(find /usr -name olares-cli -type f 2>/dev/null | head -1)" \
 && test -n "$OCLI" \
 && ln -sf "$OCLI" /usr/local/bin/olares-cli \
 && olares-cli version \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY server.py fastapi_metrics.py metrics_poller.py ./
COPY static ./static/

# Wizard assets: site-template + starters (copied from repo root in build context)
# Build context for siteconsole is apps/siteconsole — CI also needs parent assets.
# We expect a wizard-assets/ directory next to the Dockerfile (prepared by CI or local prep).
COPY wizard-assets /srv/wizard-assets

RUN useradd --uid 1000 --create-home app \
 && mkdir -p /app/data \
 && chown -R app:app /app/data /srv

USER app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["python", "server.py"]

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from fastapi_metrics import MetricsMiddleware, metrics_response

app = FastAPI(title="olares-fastapi-hello")
app.add_middleware(MetricsMiddleware)

@app.get("/api/health")
def health():
    return {"ok": True, "runtime": "fastapi-hello", "service": "olares-fastapi-hello"}

@app.get("/metrics")
def metrics():
    return metrics_response()

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><body style="font-family:system-ui;padding:2rem">
    <h1>Olares FastAPI hello</h1>
    <p>Second-runtime proof for olares-site-platform.</p>
    <p>Health: <code>/api/health</code> · Metrics: <code>/metrics</code></p>
    </body></html>"""

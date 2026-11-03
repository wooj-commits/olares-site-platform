from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="olares-fastapi-starter")

@app.get("/api/health")
def health():
    return {"ok": True, "runtime": "python-fastapi"}

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>Olares FastAPI starter</h1><p>/api/health</p>"

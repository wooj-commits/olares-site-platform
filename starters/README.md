# Runtime starters

Each folder is a minimal app + Dockerfile + `/api/health` for the Olares site platform.

| Starter | Port | Health | Notes |
|---------|------|--------|-------|
| `static-vite` | 8080 | `/api/health` | nginx; disable postgres/storage in chart |
| `nextjs` | 3000 | `/api/health` | See also `apps/demo` for full auth/DB/S3 |
| `node-express` | 3000 | `/api/health` | |
| `python-fastapi` | 8000 | `/api/health` | See `apps/fastapi-hello` |
| `django` | 8000 | `/api/health` | SQLite in image; wire Postgres via chart |
| `go` | 8080 | `/api/health` | distroless |
| `swift-vapor` | 8080 | `/api/health` | |

Copy a starter into a new repo (or path), set chart `port` / `healthPath`, push — CI builds via Dockerfile, or Nixpacks/CNB if no Dockerfile.

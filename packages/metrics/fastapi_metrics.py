"""Minimal Prometheus metrics for FastAPI apps (no prometheus_client dep)."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

_req_count: dict[tuple[str, str, str], int] = defaultdict(int)
_err_count: dict[tuple[str, str], int] = defaultdict(int)
_latency_sum: dict[tuple[str, str], float] = defaultdict(float)
_latency_count: dict[tuple[str, str], int] = defaultdict(int)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/metrics", "/healthz", "/api/health"):
            return await call_next(request)
        start = time.perf_counter()
        status = "500"
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        except Exception:
            _err_count[(request.method, request.url.path)] += 1
            raise
        finally:
            elapsed = time.perf_counter() - start
            key = (request.method, request.url.path, status)
            _req_count[key] += 1
            lk = (request.method, request.url.path)
            _latency_sum[lk] += elapsed
            _latency_count[lk] += 1
            if status.startswith("5"):
                _err_count[lk] += 1


def metrics_body() -> str:
    lines = [
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter",
    ]
    for (method, path, status), n in sorted(_req_count.items()):
        lines.append(
            f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {n}'
        )
    lines += [
        "# HELP http_errors_total Total HTTP 5xx / unhandled errors",
        "# TYPE http_errors_total counter",
    ]
    for (method, path), n in sorted(_err_count.items()):
        lines.append(f'http_errors_total{{method="{method}",path="{path}"}} {n}')
    lines += [
        "# HELP http_request_duration_seconds_sum Request latency sum",
        "# TYPE http_request_duration_seconds_sum counter",
        "# HELP http_request_duration_seconds_count Request latency count",
        "# TYPE http_request_duration_seconds_count counter",
    ]
    for (method, path), s in sorted(_latency_sum.items()):
        c = _latency_count[(method, path)]
        lines.append(
            f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {s:.6f}'
        )
        lines.append(
            f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {c}'
        )
    return "\n".join(lines) + "\n"


def metrics_response() -> PlainTextResponse:
    return PlainTextResponse(metrics_body(), media_type="text/plain; version=0.0.4")

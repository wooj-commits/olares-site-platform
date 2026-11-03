"""Poll site /metrics endpoints and store samples in SQLite (appData).

Olares prometheus-k8s often cannot scrape user app namespaces (ServiceMonitor
selector / NetworkPolicy). Site Console polls public or configured URLs instead.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("siteconsole.metrics")

SAMPLE_RE = re.compile(
    r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)'
)
LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:\\.|[^"\\])*)"')

KEEP_METRICS = {
    "http_requests_total",
    "http_errors_total",
    "http_request_duration_seconds_sum",
    "http_request_duration_seconds_count",
}


def parse_prom_text(body: str) -> list[tuple[str, dict[str, str], float]]:
    out: list[tuple[str, dict[str, str], float]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = SAMPLE_RE.match(line)
        if not m:
            continue
        name, labels_raw, val_s = m.group(1), m.group(2), m.group(3)
        if name not in KEEP_METRICS:
            continue
        labels: dict[str, str] = {}
        if labels_raw:
            for lm in LABEL_RE.finditer(labels_raw):
                labels[lm.group(1)] = lm.group(2).replace('\\"', '"').replace("\\\\", "\\")
        try:
            val = float(val_s)
        except ValueError:
            continue
        out.append((name, labels, val))
    return out


class MetricsStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.db_path), timeout=30)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS samples (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts REAL NOT NULL,
                  app TEXT NOT NULL,
                  metric TEXT NOT NULL,
                  labels TEXT NOT NULL,
                  value REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_samples_app_metric_ts
                  ON samples(app, metric, ts);
                CREATE TABLE IF NOT EXISTS scrape_status (
                  app TEXT PRIMARY KEY,
                  url TEXT,
                  ok INTEGER,
                  http_status INTEGER,
                  error TEXT,
                  last_ts REAL,
                  series INTEGER
                );
                """
            )

    def insert_batch(self, app: str, ts: float, rows: list[tuple[str, dict[str, str], float]]) -> int:
        with self._conn() as c:
            c.executemany(
                "INSERT INTO samples(ts, app, metric, labels, value) VALUES (?,?,?,?,?)",
                [(ts, app, m, json.dumps(labels, sort_keys=True), v) for m, labels, v in rows],
            )
        return len(rows)

    def set_status(self, app: str, url: str, ok: bool, http_status: int | None, error: str, series: int) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO scrape_status(app, url, ok, http_status, error, last_ts, series)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(app) DO UPDATE SET
                  url=excluded.url, ok=excluded.ok, http_status=excluded.http_status,
                  error=excluded.error, last_ts=excluded.last_ts, series=excluded.series
                """,
                (app, url, 1 if ok else 0, http_status, error[:500], time.time(), series),
            )

    def prune(self, keep_seconds: float = 86400.0) -> int:
        cutoff = time.time() - keep_seconds
        with self._conn() as c:
            cur = c.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
            return cur.rowcount or 0

    def statuses(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT app, url, ok, http_status, error, last_ts, series FROM scrape_status ORDER BY app"
            ).fetchall()
        return [
            {
                "app": r[0],
                "url": r[1],
                "ok": bool(r[2]),
                "http_status": r[3],
                "error": r[4] or "",
                "last_ts": r[5],
                "series": r[6],
            }
            for r in rows
        ]

    def series(
        self,
        app: str | None,
        metric: str,
        since: float,
        label_filter: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        q = "SELECT ts, app, labels, value FROM samples WHERE metric=? AND ts>=?"
        args: list[Any] = [metric, since]
        if app:
            q += " AND app=?"
            args.append(app)
        q += " ORDER BY ts ASC"
        with self._conn() as c:
            rows = c.execute(q, args).fetchall()
        out = []
        for ts, a, labels_s, value in rows:
            labels = json.loads(labels_s)
            if label_filter:
                if any(labels.get(k) != v for k, v in label_filter.items()):
                    continue
            out.append({"ts": ts, "app": a, "labels": labels, "value": value})
        return out

    def latest_counters(self, app: str | None = None) -> list[dict[str, Any]]:
        """Latest sample per (app, metric, labels)."""
        since = time.time() - 3600
        q = """
        SELECT s.ts, s.app, s.metric, s.labels, s.value FROM samples s
        INNER JOIN (
          SELECT app, metric, labels, MAX(ts) AS mts FROM samples WHERE ts>=?
        """
        args: list[Any] = [since]
        if app:
            q += " AND app=?"
            args.append(app)
        q += """
          GROUP BY app, metric, labels
        ) t ON s.app=t.app AND s.metric=t.metric AND s.labels=t.labels AND s.ts=t.mts
        """
        with self._conn() as c:
            rows = c.execute(q, args).fetchall()
        return [
            {"ts": r[0], "app": r[1], "metric": r[2], "labels": json.loads(r[3]), "value": r[4]}
            for r in rows
        ]

    def rate_points(
        self, app: str, metric: str, window_s: float = 3600.0, step_s: float = 60.0
    ) -> list[dict[str, Any]]:
        """Approximate per-path request rate from counter samples."""
        since = time.time() - window_s
        rows = self.series(app, metric, since)
        # group by labels json
        by_key: dict[str, list[tuple[float, float]]] = {}
        for r in rows:
            key = json.dumps(r["labels"], sort_keys=True)
            by_key.setdefault(key, []).append((r["ts"], r["value"]))
        # emit mid-interval rates
        out: list[dict[str, Any]] = []
        for key, pts in by_key.items():
            pts.sort()
            labels = json.loads(key)
            for i in range(1, len(pts)):
                t0, v0 = pts[i - 1]
                t1, v1 = pts[i]
                dt = t1 - t0
                if dt <= 0:
                    continue
                dv = v1 - v0
                if dv < 0:
                    continue  # counter reset
                out.append(
                    {
                        "ts": t1,
                        "app": app,
                        "labels": labels,
                        "rate": dv / dt,
                    }
                )
        out.sort(key=lambda x: x["ts"])
        return out

    def federate_text(self) -> str:
        """Prometheus text exposition of latest scraped samples (plus scrape_ok)."""
        lines = [
            "# HELP siteconsole_scrape_ok 1 if last scrape succeeded",
            "# TYPE siteconsole_scrape_ok gauge",
        ]
        for st in self.statuses():
            lines.append(
                f'siteconsole_scrape_ok{{app="{st["app"]}"}} {1 if st["ok"] else 0}'
            )
        lines += [
            "# HELP http_requests_total Total HTTP requests (scraped by siteconsole)",
            "# TYPE http_requests_total counter",
        ]
        # Only emit http_* from latest
        for row in self.latest_counters():
            if row["metric"] not in KEEP_METRICS:
                continue
            labels = {"app": row["app"], **row["labels"]}
            lab = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            lines.append(f'{row["metric"]}{{{lab}}} {row["value"]}')
        return "\n".join(lines) + "\n"


def default_targets(olares_id: str) -> list[dict[str, str]]:
    """Built-in public targets known for this platform (overridable via config)."""
    return [
        {
            "app": "olaresdemo",
            "url": f"https://1c5eaad0.{olares_id}.olares.com/metrics",
        },
        {
            "app": "fastapihello",
            "url": f"https://3fd9011b.{olares_id}.olares.com/metrics",
        },
        {
            "app": "siteconsole",
            "url": "http://127.0.0.1:8080/metrics",
        },
    ]


def merge_targets(
    olares_id: str,
    cfg: dict[str, Any],
    backup_cfg: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Config shape: { "targets": [ {"app","url","token"?} ], "interval_s": 20 }."""
    by_app: dict[str, dict[str, str]] = {t["app"]: dict(t) for t in default_targets(olares_id)}
    for t in cfg.get("targets") or []:
        if isinstance(t, dict) and t.get("app") and t.get("url"):
            by_app[str(t["app"])] = {
                "app": str(t["app"]),
                "url": str(t["url"]).rstrip("/"),
                **({"token": str(t["token"])} if t.get("token") else {}),
            }
    # Reuse backup entrance URLs when metrics URL not set
    for name, conf in ((backup_cfg or {}).get("apps") or {}).items():
        if name in by_app:
            continue
        entrance = (conf or {}).get("entrance_url") or ""
        if entrance:
            u = entrance.rstrip("/")
            if not u.endswith("/metrics"):
                u = u + "/metrics"
            by_app[name] = {"app": name, "url": u}
    return list(by_app.values())


async def scrape_one(client: httpx.AsyncClient, target: dict[str, str], store: MetricsStore) -> None:
    app = target["app"]
    url = target["url"]
    headers = {}
    if target.get("token"):
        headers["Authorization"] = f"Bearer {target['token']}"
    try:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            store.set_status(app, url, False, r.status_code, f"HTTP {r.status_code}", 0)
            return
        # Authelia HTML/login redirects sometimes still 200 with HTML
        ctype = (r.headers.get("content-type") or "").lower()
        body = r.text
        if "text/html" in ctype and "http_requests_total" not in body:
            store.set_status(app, url, False, r.status_code, "got HTML (auth wall?)", 0)
            return
        rows = parse_prom_text(body)
        ts = time.time()
        n = store.insert_batch(app, ts, rows)
        store.set_status(app, url, True, r.status_code, "", n)
    except Exception as e:
        store.set_status(app, url, False, None, str(e), 0)
        logger.warning("scrape %s failed: %s", app, e)


async def poll_loop(
    store: MetricsStore,
    get_targets,
    interval_s: float = 20.0,
    stop_event: asyncio.Event | None = None,
) -> None:
    stop = stop_event or asyncio.Event()
    prune_every = 0
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        while not stop.is_set():
            targets = get_targets()
            await asyncio.gather(*(scrape_one(client, t, store) for t in targets))
            prune_every += 1
            if prune_every >= 30:
                pruned = store.prune(86400.0)
                if pruned:
                    logger.info("pruned %s old metric samples", pruned)
                prune_every = 0
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval_s)
            except asyncio.TimeoutError:
                pass

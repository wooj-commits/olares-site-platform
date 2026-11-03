"""Olares Site Console — manage sites via olares-cli (loginOlaresCLI)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fastapi_metrics import MetricsMiddleware, metrics_response

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("siteconsole")

OLARES_CLI = os.environ.get("OLARES_CLI", "olares-cli")
DATA_DIR = Path(os.environ.get("SITECONSOLE_DATA_DIR", "/app/data"))
HISTORY_FILE = DATA_DIR / "deploy-history.json"
REDIRECTS_FILE = DATA_DIR / "redirects.json"
REGISTRY_FILE = DATA_DIR / "managed-apps.json"
NOTIF_FILE = DATA_DIR / "notifications.json"

GH_OWNER = os.environ.get("GH_OWNER", "wooj-commits").strip()
GH_REPO = os.environ.get("GH_REPO", "olares-site-platform").strip()
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()  # optional; never log
MANAGED_FILTER = os.environ.get("MANAGED_APPS", "").strip()  # comma names; empty = all
WATCH_TIMEOUT = os.environ.get("WATCH_TIMEOUT", "20m").strip()
OLARES_ID = os.environ.get("OLARES_ID", "woojinc1205").strip()
WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL", "").strip()

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Olares Site Console", version="0.1.3")
app.add_middleware(MetricsMiddleware)
_lock = asyncio.Lock()
_busy = False
_busy_msg = ""
_last_error = ""
_last_log: list[str] = []


# ---------- helpers ----------

def _load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def _save_json(path: Path, data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _append_history(entry: dict[str, Any]) -> None:
    hist = _load_json(HISTORY_FILE, [])
    if not isinstance(hist, list):
        hist = []
    entry.setdefault("at", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    hist.insert(0, entry)
    _save_json(HISTORY_FILE, hist[:200])


def _managed_set() -> set[str] | None:
    if not MANAGED_FILTER:
        # optional registry file
        reg = _load_json(REGISTRY_FILE, None)
        if isinstance(reg, list) and reg:
            return {str(x).strip() for x in reg if str(x).strip()}
        return None
    return {p.strip() for p in MANAGED_FILTER.split(",") if p.strip()}


async def run_cli(*args: str, timeout: float = 1200.0) -> tuple[int, str, str]:
    cmd = [OLARES_CLI, *args]
    logger.info("cli: %s", " ".join(cmd))
    _last_log.append("$ " + " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ},
    )
    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        msg = f"timeout after {timeout}s: {' '.join(cmd)}"
        _last_log.append(msg)
        return 124, "", msg
    out = (out_b or b"").decode(errors="replace")
    err = (err_b or b"").decode(errors="replace")
    if out.strip():
        _last_log.append(out.strip()[:4000])
    if err.strip():
        _last_log.append(err.strip()[:2000])
    del _last_log[:-60]
    return proc.returncode or 0, out, err


async def cli_json(*args: str, timeout: float = 180.0) -> Any:
    code, out, err = await run_cli(*args, "-o", "json", timeout=timeout)
    if code != 0:
        raise RuntimeError(
            f"olares-cli {' '.join(args)} failed ({code}): {(err or out)[:800]}"
        )
    text = out.strip() or "null"
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise RuntimeError(f"non-JSON from olares-cli {' '.join(args)}: {text[:400]}")


def _is_running(state: str) -> bool:
    s = (state or "").lower()
    return s in ("running", "resumed") or s.endswith("running")


def _is_stopped(state: str) -> bool:
    s = (state or "").lower()
    return s in ("stopped", "suspended", "stop") or "stopp" in s or "suspend" in s


def _normalize_app_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"name": str(row), "state": "unknown"}
    name = (
        row.get("name")
        or row.get("appName")
        or row.get("rawName")
        or row.get("id")
        or "unknown"
    )
    state = (
        row.get("state")
        or row.get("status")
        or row.get("finalState")
        or (row.get("data") or {}).get("state")
        or "unknown"
    )
    title = row.get("title") or row.get("displayName") or name
    version = row.get("version") or row.get("currentVersion") or row.get("appVersion")
    source = row.get("source") or (row.get("data") or {}).get("source")
    entrances = row.get("entrances") or row.get("entrance") or []
    return {
        "name": str(name),
        "title": str(title),
        "state": str(state),
        "version": version,
        "source": source,
        "entrances": entrances,
        "raw": {k: row.get(k) for k in ("namespace", "icon", "category", "createTime") if k in row},
    }


async def list_apps() -> list[dict[str, Any]]:
    data = await cli_json("market", "list", "--mine")
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("items") or data.get("data") or data.get("apps") or []
        if not isinstance(rows, list):
            rows = [data]
    else:
        rows = []
    apps = [_normalize_app_row(r) for r in rows]
    filt = _managed_set()
    if filt is not None:
        apps = [a for a in apps if a["name"] in filt]
    return apps


async def app_status(name: str) -> dict[str, Any]:
    try:
        data = await cli_json("market", "status", name)
        return _normalize_app_row(data if not isinstance(data, list) else (data[0] if data else {}))
    except Exception as e:
        return {"name": name, "state": "unknown", "error": str(e)[:400]}


async def notify(event: str, payload: dict[str, Any]) -> None:
    entry = {"event": event, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **payload}
    notes = _load_json(NOTIF_FILE, [])
    if not isinstance(notes, list):
        notes = []
    notes.insert(0, entry)
    _save_json(NOTIF_FILE, notes[:100])
    if not WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(WEBHOOK_URL, json=entry)
    except Exception as e:
        logger.warning("webhook notify failed: %s", e)


# ---------- models ----------

class EnvSetBody(BaseModel):
    vars: dict[str, str] = Field(default_factory=dict)


class ThirdLevelBody(BaseModel):
    third_level: str = Field(..., min_length=1)


class ThirdPartyBody(BaseModel):
    third_party: str = Field(..., min_length=1)
    # cert/key provided as PEM text (never logged)


class DeployBody(BaseModel):
    app: str = Field(..., min_length=1)
    tag: str = Field(..., min_length=1)  # release tag e.g. v0.1.4
    asset: str | None = None  # chart tgz filename; auto-pick if omitted
    action: str = Field(default="upgrade", pattern="^(upgrade|install)$")


class RedirectRule(BaseModel):
    from_path: str = Field(..., min_length=1)
    to_url: str = Field(..., min_length=1)
    status: int = Field(default=302)


class RedirectsBody(BaseModel):
    rules: list[RedirectRule] = Field(default_factory=list)
    apply: bool = True  # also push REDIRECT_RULES_JSON env to the app


class RegistryBody(BaseModel):
    apps: list[str] = Field(default_factory=list)


# ---------- routes ----------

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "siteconsole"}


@app.get("/metrics")
async def metrics():
    return metrics_response()


@app.get("/api/health")
async def api_health():
    return {"ok": True, "runtime": "siteconsole", "version": "0.1.3"}


@app.get("/api/config")
async def api_config():
    return {
        "gh_owner": GH_OWNER,
        "gh_repo": GH_REPO,
        "olares_id": OLARES_ID,
        "managed_filter": sorted(_managed_set() or []),
        "managed_filter_active": _managed_set() is not None,
        "watch_timeout": WATCH_TIMEOUT,
        "webhook_configured": bool(WEBHOOK_URL),
        "github_token_configured": bool(GH_TOKEN),
        "busy": _busy,
        "busy_msg": _busy_msg,
    }


@app.get("/api/status")
async def api_status():
    return {
        "busy": _busy,
        "busy_msg": _busy_msg,
        "last_error": _last_error,
        "recent_log": _last_log[-20:],
    }


@app.get("/api/apps")
async def api_apps():
    try:
        apps = await list_apps()
        return {"ok": True, "apps": apps}
    except Exception as e:
        logger.exception("list apps")
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)[:800]})


@app.get("/api/apps/{name}")
async def api_app(name: str):
    st = await app_status(name)
    return {"ok": True, "app": st}


@app.post("/api/apps/{name}/stop")
async def api_stop(name: str):
    global _last_error
    if name == "siteconsole":
        raise HTTPException(400, "Refusing to stop siteconsole itself")
    code, out, err = await run_cli(
        "market", "stop", name, "--watch", f"--watch-timeout={WATCH_TIMEOUT}"
    )
    if code != 0:
        st = await app_status(name)
        if _is_stopped(st.get("state", "")):
            return {"ok": True, "app": st, "note": "already stopped"}
        _last_error = (err or out)[:800]
        return JSONResponse(status_code=500, content={"ok": False, "error": _last_error})
    return {"ok": True, "app": await app_status(name)}


@app.post("/api/apps/{name}/resume")
async def api_resume(name: str):
    global _last_error
    code, out, err = await run_cli(
        "market", "resume", name, "--watch", f"--watch-timeout={WATCH_TIMEOUT}"
    )
    if code != 0:
        st = await app_status(name)
        if _is_running(st.get("state", "")):
            return {"ok": True, "app": st, "note": "already running"}
        _last_error = (err or out)[:800]
        return JSONResponse(status_code=500, content={"ok": False, "error": _last_error})
    return {"ok": True, "app": await app_status(name)}


@app.get("/api/apps/{name}/env")
async def api_env_get(name: str):
    try:
        data = await cli_json("settings", "apps", "env", "get", name)
        return {"ok": True, "env": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)[:800]})


@app.put("/api/apps/{name}/env")
async def api_env_set(name: str, body: EnvSetBody):
    if not body.vars:
        raise HTTPException(400, "vars required")
    args = ["settings", "apps", "env", "set", name]
    for k, v in body.vars.items():
        args += ["--var", f"{k}={v}"]
    code, out, err = await run_cli(*args, timeout=180.0)
    if code != 0:
        return JSONResponse(
            status_code=500, content={"ok": False, "error": (err or out)[:800]}
        )
    # re-fetch (values may mask secrets)
    try:
        data = await cli_json("settings", "apps", "env", "get", name)
    except Exception:
        data = None
    return {"ok": True, "env": data, "updated": list(body.vars.keys())}


@app.get("/api/apps/{name}/entrances")
async def api_entrances(name: str):
    try:
        data = await cli_json("settings", "apps", "entrances", "list", name)
        return {"ok": True, "entrances": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)[:800]})


@app.get("/api/apps/{name}/domains")
async def api_domains(name: str):
    try:
        data = await cli_json("settings", "apps", "domain", "list", name)
        return {"ok": True, "domains": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)[:800]})


@app.get("/api/apps/{name}/domains/{entrance}")
async def api_domain_get(name: str, entrance: str):
    try:
        data = await cli_json("settings", "apps", "domain", "get", name, entrance)
        # never return raw cert/key PEMs to the UI by default
        if isinstance(data, dict):
            safe = {**data}
            if safe.get("cert"):
                safe["cert"] = "(set)"
            if safe.get("key"):
                safe["key"] = "(set)"
            return {"ok": True, "domain": safe}
        return {"ok": True, "domain": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)[:800]})


@app.post("/api/apps/{name}/domains/{entrance}/third-level")
async def api_domain_third_level(name: str, entrance: str, body: ThirdLevelBody):
    code, out, err = await run_cli(
        "settings",
        "apps",
        "domain",
        "set",
        name,
        entrance,
        "--third-level",
        body.third_level.strip(),
        timeout=120.0,
    )
    if code != 0:
        return JSONResponse(
            status_code=500, content={"ok": False, "error": (err or out)[:800]}
        )
    return {"ok": True, "message": out.strip(), "hint": f"Live at https://{body.third_level.strip()}.{OLARES_ID}.olares.com (instant; no DNS)."}


@app.post("/api/apps/{name}/domains/{entrance}/third-party")
async def api_domain_third_party(
    name: str,
    entrance: str,
    third_party: str = Form(...),
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
):
    """Custom domain with cert/key PEMs (multipart)."""
    tmp = Path(tempfile.mkdtemp(prefix="sc-domain-"))
    try:
        cert_path = tmp / "fullchain.pem"
        key_path = tmp / "privkey.pem"
        cert_path.write_bytes(await cert_file.read())
        key_path.write_bytes(await key_file.read())
        code, out, err = await run_cli(
            "settings",
            "apps",
            "domain",
            "set",
            name,
            entrance,
            "--third-party",
            third_party.strip(),
            "--cert-file",
            str(cert_path),
            "--key-file",
            str(key_path),
            timeout=180.0,
        )
        if code != 0:
            return JSONResponse(
                status_code=500, content={"ok": False, "error": (err or out)[:800]}
            )
        # fetch cname target for DNS instructions
        setup = None
        try:
            setup = await cli_json("settings", "apps", "domain", "get", name, entrance)
        except Exception:
            pass
        cname_target = (setup or {}).get("cname_target") if isinstance(setup, dict) else None
        instructions = _dns_instructions(third_party.strip(), cname_target)
        return {
            "ok": True,
            "message": out.strip(),
            "cname_target": cname_target,
            "dns_instructions": instructions,
            "next": "Paste DNS records at Squarespace/Google Domains, then call finish.",
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _dns_instructions(fqdn: str, cname_target: str | None) -> dict[str, Any]:
    host = fqdn.rstrip(".")
    # apex vs subdomain
    parts = host.split(".")
    is_apex = len(parts) == 2
    target = cname_target or f"(run domain get — typically a host under {OLARES_ID}.olares.com)"
    squarespace = [
        {
            "type": "CNAME" if not is_apex else "CNAME or ALIAS",
            "host": host if is_apex else ".".join(parts[:-2]) if len(parts) > 2 else "@",
            "host_ui": "@" if is_apex else parts[0],
            "data": target,
            "ttl": "Default",
            "note": "Squarespace Domains → DNS Settings → Add record. No public DNS API — paste manually.",
        },
        {
            "type": "TXT (optional ownership)",
            "host": host,
            "data": "(only if Olares Space asks for a verification TXT — rare for CNAME path)",
            "note": "Usually not needed for standard third-party CNAME + cert.",
        },
    ]
    google = [
        {
            "type": "CNAME",
            "host": "@" if is_apex else parts[0],
            "data": target,
            "note": "Google Domains / Squarespace DNS for thinkermaker.studio — same paste UX.",
        }
    ]
    return {
        "fqdn": host,
        "cname_target": target,
        "squarespace": squarespace,
        "google_domains": google,
        "warning": "Custom domains via Olares Tunnel are unreliable (known miss: vault.woojincho.com). Always verify after finish. Prefer *.olares.com third-level routes when possible.",
    }


@app.post("/api/apps/{name}/domains/{entrance}/finish")
async def api_domain_finish(name: str, entrance: str):
    code, out, err = await run_cli(
        "settings", "apps", "domain", "finish", name, entrance, timeout=120.0
    )
    if code != 0:
        return JSONResponse(
            status_code=500, content={"ok": False, "error": (err or out)[:800]}
        )
    setup = None
    try:
        setup = await cli_json("settings", "apps", "domain", "get", name, entrance)
        if isinstance(setup, dict):
            setup = {**setup, "cert": "(set)" if setup.get("cert") else "", "key": "(set)" if setup.get("key") else ""}
    except Exception:
        pass
    return {"ok": True, "message": out.strip(), "domain": setup}


@app.get("/api/apps/{name}/logs")
async def api_logs(name: str, tail: int = 200, namespace: str | None = None):
    """Find a pod for the app and return recent logs."""
    try:
        # list pods; prefer namespace user-woojinc1205-* or containing app name
        pods = await cli_json("cluster", "pod", "list")
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": f"pod list: {e}"[:800]})

    items: list[dict[str, Any]] = []
    if isinstance(pods, dict):
        items = pods.get("items") or pods.get("data") or []
    elif isinstance(pods, list):
        items = pods

    name_l = name.lower()
    candidates: list[tuple[str, str]] = []  # ns, pod
    for p in items:
        if not isinstance(p, dict):
            continue
        meta = p.get("metadata") or p
        pname = str(meta.get("name") or "")
        pns = str(meta.get("namespace") or p.get("namespace") or "")
        labels = meta.get("labels") or {}
        blob = f"{pname} {pns} {json.dumps(labels)}".lower()
        if name_l in blob or name_l.replace("-", "") in blob.replace("-", ""):
            if namespace and pns != namespace:
                continue
            candidates.append((pns, pname))

    if not candidates:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"No pod found matching app {name}", "hint": "Open Control Hub → Pods if needed."},
        )

    pns, pname = candidates[0]
    code, out, err = await run_cli(
        "cluster",
        "pod",
        "logs",
        f"{pns}/{pname}",
        "--tail",
        str(max(1, min(tail, 2000))),
        "--timestamps=false",
        timeout=60.0,
    )
    if code != 0:
        # try with -n form
        code2, out2, err2 = await run_cli(
            "cluster",
            "pod",
            "logs",
            pname,
            "-n",
            pns,
            "--tail",
            str(max(1, min(tail, 2000))),
            timeout=60.0,
        )
        if code2 != 0:
            return JSONResponse(
                status_code=500,
                content={"ok": False, "error": (err or out or err2 or out2)[:800]},
            )
        out = out2
    return {
        "ok": True,
        "namespace": pns,
        "pod": pname,
        "candidates": [{"namespace": a, "pod": b} for a, b in candidates[:10]],
        "logs": out,
    }


@app.get("/api/releases")
async def api_releases(per_page: int = 20):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "olares-site-console"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/releases?per_page={min(per_page, 50)}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            releases = r.json()
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)[:400]})

    out = []
    for rel in releases:
        assets = []
        for a in rel.get("assets") or []:
            name = a.get("name") or ""
            if name.endswith(".tgz") or name.endswith(".tar.gz"):
                assets.append(
                    {
                        "name": name,
                        "size": a.get("size"),
                        "url": a.get("browser_download_url") or a.get("url"),
                        "api_url": a.get("url"),
                    }
                )
        out.append(
            {
                "tag": rel.get("tag_name"),
                "name": rel.get("name"),
                "published_at": rel.get("published_at"),
                "prerelease": rel.get("prerelease"),
                "assets": assets,
            }
        )
    return {"ok": True, "repo": f"{GH_OWNER}/{GH_REPO}", "releases": out}


async def _download_asset(asset: dict[str, Any], dest: Path) -> None:
    headers = {"Accept": "application/octet-stream", "User-Agent": "olares-site-console"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    url = asset.get("api_url") or asset.get("url")
    if not url:
        raise RuntimeError("asset has no url")
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        dest.write_bytes(r.content)


@app.post("/api/deploy")
async def api_deploy(body: DeployBody):
    global _busy, _busy_msg, _last_error
    if _lock.locked() or _busy:
        raise HTTPException(409, "Another deploy is in progress")
    async with _lock:
        _busy = True
        _busy_msg = f"{body.action} {body.app} @ {body.tag}"
        t0 = time.monotonic()
        tmp = Path(tempfile.mkdtemp(prefix="sc-deploy-"))
        try:
            # resolve release + asset
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "olares-site-console",
            }
            if GH_TOKEN:
                headers["Authorization"] = f"Bearer {GH_TOKEN}"
            tag = body.tag
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(
                    f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/releases/tags/{quote(tag)}",
                    headers=headers,
                )
                if r.status_code == 404:
                    raise RuntimeError(f"Release tag {tag} not found")
                r.raise_for_status()
                rel = r.json()
            assets = [
                a
                for a in (rel.get("assets") or [])
                if (a.get("name") or "").endswith((".tgz", ".tar.gz"))
            ]
            if not assets:
                raise RuntimeError(f"No chart .tgz assets on release {tag}")
            chosen = None
            if body.asset:
                for a in assets:
                    if a.get("name") == body.asset:
                        chosen = a
                        break
                if not chosen:
                    raise RuntimeError(f"Asset {body.asset} not on {tag}")
            else:
                # prefer chart whose name starts with app name
                for a in assets:
                    if (a.get("name") or "").startswith(body.app):
                        chosen = a
                        break
                chosen = chosen or assets[0]

            dest = tmp / (chosen.get("name") or f"{body.app}.tgz")
            await _download_asset(
                {
                    "api_url": chosen.get("url"),
                    "url": chosen.get("browser_download_url"),
                },
                dest,
            )

            code, out, err = await run_cli("market", "upload", str(dest), timeout=300.0)
            if code != 0:
                raise RuntimeError(f"upload failed: {(err or out)[:800]}")

            if body.action == "install":
                code, out, err = await run_cli(
                    "market",
                    "install",
                    body.app,
                    "-s",
                    "upload",
                    "--watch",
                    f"--watch-timeout={WATCH_TIMEOUT}",
                    timeout=1500.0,
                )
            else:
                code, out, err = await run_cli(
                    "market",
                    "upgrade",
                    body.app,
                    "-s",
                    "upload",
                    "--watch",
                    f"--watch-timeout={WATCH_TIMEOUT}",
                    timeout=1500.0,
                )
            if code != 0:
                raise RuntimeError(f"{body.action} failed: {(err or out)[:800]}")

            elapsed = round(time.monotonic() - t0, 1)
            entry = {
                "ok": True,
                "action": body.action,
                "app": body.app,
                "tag": tag,
                "asset": chosen.get("name"),
                "elapsed_s": elapsed,
            }
            _append_history(entry)
            await notify("deploy_success", entry)
            _last_error = ""
            return {"ok": True, **entry, "app_status": await app_status(body.app)}
        except Exception as e:
            _last_error = str(e)[:1000]
            logger.exception("deploy failed")
            entry = {
                "ok": False,
                "action": body.action,
                "app": body.app,
                "tag": body.tag,
                "error": _last_error,
            }
            _append_history(entry)
            await notify("deploy_failure", entry)
            return JSONResponse(status_code=500, content={"ok": False, **entry})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            _busy = False
            _busy_msg = ""


@app.get("/api/history")
async def api_history():
    return {"ok": True, "history": _load_json(HISTORY_FILE, [])}


@app.get("/api/redirects/{name}")
async def api_redirects_get(name: str):
    all_r = _load_json(REDIRECTS_FILE, {})
    if not isinstance(all_r, dict):
        all_r = {}
    return {"ok": True, "app": name, "rules": all_r.get(name, [])}


@app.put("/api/redirects/{name}")
async def api_redirects_put(name: str, body: RedirectsBody):
    all_r = _load_json(REDIRECTS_FILE, {})
    if not isinstance(all_r, dict):
        all_r = {}
    rules = [r.model_dump() for r in body.rules]
    all_r[name] = rules
    _save_json(REDIRECTS_FILE, all_r)
    applied = None
    if body.apply:
        payload = json.dumps(rules, separators=(",", ":"))
        code, out, err = await run_cli(
            "settings",
            "apps",
            "env",
            "set",
            name,
            "--var",
            f"REDIRECT_RULES_JSON={payload}",
            timeout=180.0,
        )
        applied = {"ok": code == 0, "detail": (out or err)[:400]}
        if code != 0:
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "saved": True,
                    "rules": rules,
                    "apply": applied,
                    "error": "Saved locally but failed to push REDIRECT_RULES_JSON — ensure the app declares that editable env.",
                },
            )
    return {"ok": True, "rules": rules, "apply": applied}


@app.get("/api/registry")
async def api_registry_get():
    return {"ok": True, "apps": _load_json(REGISTRY_FILE, []), "env_filter": MANAGED_FILTER}


@app.put("/api/registry")
async def api_registry_put(body: RegistryBody):
    _save_json(REGISTRY_FILE, body.apps)
    return {"ok": True, "apps": body.apps}


@app.get("/api/notifications")
async def api_notifications():
    return {"ok": True, "notifications": _load_json(NOTIF_FILE, [])}



ANALYTICS_FILE = DATA_DIR / "analytics.jsonl"


class AnalyticsEvent(BaseModel):
    type: str = Field(..., min_length=1)  # pageview | webvital | error
    path: str | None = None
    name: str | None = None
    value: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/analytics/collect")
async def analytics_collect(body: AnalyticsEvent):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **body.model_dump()})
    with ANALYTICS_FILE.open("a") as f:
        f.write(line + "\n")
    return {"ok": True}


@app.get("/api/analytics/summary")
async def analytics_summary(limit: int = 200):
    if not ANALYTICS_FILE.exists():
        return {"ok": True, "events": [], "counts": {}}
    lines = ANALYTICS_FILE.read_text().splitlines()[-max(1, min(limit, 2000)):]
    events = []
    counts: dict[str, int] = {}
    for line in lines:
        try:
            ev = json.loads(line)
        except Exception:
            continue
        events.append(ev)
        t = str(ev.get("type") or "unknown")
        counts[t] = counts.get(t, 0) + 1
    return {"ok": True, "events": events[-100:], "counts": counts}



STARTERS = [
    {"id": "nextjs", "path": "starters/nextjs", "port": 3000, "notes": "Next.js"},
    {"id": "python-fastapi", "path": "starters/python-fastapi", "port": 8000, "notes": "FastAPI"},
    {"id": "static-vite", "path": "starters/static-vite", "port": 3000, "notes": "Static Vite"},
    {"id": "node-express", "path": "starters/node-express", "port": 3000, "notes": "Express"},
    {"id": "django", "path": "starters/django", "port": 8000, "notes": "Django"},
    {"id": "go", "path": "starters/go", "port": 8080, "notes": "Go"},
    {"id": "swift-vapor", "path": "starters/swift-vapor", "port": 8080, "notes": "Swift Vapor"},
]


class WizardPlan(BaseModel):
    app_name: str = Field(..., min_length=2, pattern=r"^[a-z][a-z0-9-]{1,40}$")
    starter: str
    title: str = ""
    postgres: bool = True
    storage: bool = False


@app.get("/api/wizard/starters")
async def wizard_starters():
    return {"ok": True, "starters": STARTERS, "checklist_doc": "docs/new-site-checklist.md"}


@app.post("/api/wizard/plan")
async def wizard_plan(body: WizardPlan):
    if body.starter not in {s["id"] for s in STARTERS}:
        raise HTTPException(400, f"unknown starter {body.starter}")
    title = body.title or body.app_name
    return {
        "ok": True,
        "plan": {
            "app_name": body.app_name,
            "starter": body.starter,
            "title": title,
            "steps": [
                f"Copy starters/{body.starter} into a new repo or apps/{body.app_name}",
                f"Copy chart/site-template → chart/{body.app_name}; replace SITE_* with {body.app_name}",
                f"Set postgres.enabled={str(body.postgres).lower()}, storage.enabled={str(body.storage).lower()}",
                "Push to GitHub; wait for publish workflow chart .tgz",
                f"In Site Console → Deploy: install {body.app_name} from the release asset",
            ],
            "preview_note": "Full PR preview installs are not automated on Olares (see docs/phase3-wizard-backups-previews.md).",
        },
    }


BACKUP_DIR = DATA_DIR / "backups"


@app.get("/api/backups")
async def backups_list():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(BACKUP_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file():
            items.append({"name": f.name, "size": f.stat().st_size, "mtime": f.stat().st_mtime})
    return {
        "ok": True,
        "backups": items,
        "note": "Create backups via POST /api/backups/{app} once Postgres dump credentials are available in-pod (Phase 3).",
    }


@app.post("/api/backups/{name}")
async def backups_create(name: str):
    """Placeholder: records intent; real pg_dump needs DB URL from settings/env (not always exposed to console)."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    meta = BACKUP_DIR / f"{name}-{stamp}.json"
    meta.write_text(json.dumps({
        "app": name,
        "at": stamp,
        "status": "planned",
        "message": "Wire pg_dump + MinIO tar when console can read middleware DSN; for now this is a stub marker.",
    }, indent=2))
    return {"ok": True, "file": meta.name, "status": "planned"}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main():
    import uvicorn

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        log_level="info",
    )


if __name__ == "__main__":
    main()

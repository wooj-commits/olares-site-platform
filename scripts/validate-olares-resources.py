#!/usr/bin/env python3
"""Fail if summed container CPU/memory in a chart exceed OlaresManifest accelerator caps.

Usage:
  validate-olares-resources.py <chart-dir> [--values file.yaml]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML required (apt install python3-yaml or pip install pyyaml)\n")
    sys.exit(2)


def parse_cpu(s) -> int:
    if s is None or s == "":
        return 0
    if isinstance(s, (int, float)):
        return int(float(s) * 1000)
    s = str(s).strip()
    if s.endswith("m"):
        return int(s[:-1])
    return int(float(s) * 1000)


def parse_mem(s) -> int:
    """Return mebibytes."""
    if s is None or s == "":
        return 0
    if isinstance(s, (int, float)):
        return int(s)
    s = str(s).strip()
    for u, mul in (("Ki", 1 / 1024), ("Mi", 1), ("Gi", 1024), ("Ti", 1024 * 1024)):
        if s.endswith(u):
            return int(float(s[: -len(u)]) * mul)
    return int(int(s) / (1024 * 1024))


def fmt_cpu(m: int) -> str:
    return f"{m}m" if m % 1000 else str(m // 1000)


def fmt_mem(mi: int) -> str:
    if mi % 1024 == 0:
        return f"{mi // 1024}Gi"
    return f"{mi}Mi"


def sum_workload_resources(docs: list) -> dict:
    totals = {"req_cpu": 0, "req_mem": 0, "lim_cpu": 0, "lim_mem": 0}
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") not in ("Deployment", "StatefulSet", "DaemonSet"):
            continue
        replicas = int(doc.get("spec", {}).get("replicas") or 1)
        pod = doc.get("spec", {}).get("template", {}).get("spec", {})
        for c in pod.get("containers") or []:
            res = c.get("resources") or {}
            req = res.get("requests") or {}
            lim = res.get("limits") or {}
            totals["req_cpu"] += parse_cpu(req.get("cpu")) * replicas
            totals["req_mem"] += parse_mem(req.get("memory")) * replicas
            totals["lim_cpu"] += parse_cpu(lim.get("cpu")) * replicas
            totals["lim_mem"] += parse_mem(lim.get("memory")) * replicas
    return totals


def read_manifest_caps(manifest_path: Path) -> dict:
    data = yaml.safe_load(manifest_path.read_text())
    caps: dict = {}
    # Top-level accelerator (v3 style) or nested under spec
    acc = data.get("accelerator")
    if not acc:
        acc = (data.get("spec") or {}).get("accelerator")
    if isinstance(acc, list) and acc:
        a = acc[0]
        caps = {
            "req_cpu": parse_cpu(a.get("requiredCpu")),
            "req_mem": parse_mem(a.get("requiredMemory")),
            "lim_cpu": parse_cpu(a.get("limitedCpu")),
            "lim_mem": parse_mem(a.get("limitedMemory")),
        }
    spec = data.get("spec") or {}
    mapping = (
        ("requiredCpu", "req_cpu", parse_cpu),
        ("requiredMemory", "req_mem", parse_mem),
        ("limitedCpu", "lim_cpu", parse_cpu),
        ("limitedMemory", "lim_mem", parse_mem),
    )
    for src, dst, fn in mapping:
        if caps.get(dst, 0) == 0 and src in spec:
            caps[dst] = fn(spec[src])
    return caps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chart_dir", type=Path)
    ap.add_argument("--values", type=Path, action="append", default=[])
    ap.add_argument("--name", default="lint")
    args = ap.parse_args()
    chart = args.chart_dir.resolve()
    manifest = chart / "OlaresManifest.yaml"
    if not manifest.exists():
        print(f"ERROR: missing {manifest}", file=sys.stderr)
        return 2

    stub = chart / ".ci-stub-values.yaml"
    stub.write_text(
        """
userspace:
  appData: /tmp/appdata
  appCache: /tmp/appcache
postgres:
  host: postgres
  port: 5432
  username: app
  password: unused
  databases:
    olaresdemo: olaresdemo
    SITE_NAME: SITE_NAME
domain:
  web: example.local
olaresEnv: {}
"""
    )
    cmd = ["helm", "template", args.name, str(chart), "-f", str(stub)]
    for v in args.values:
        cmd.extend(["-f", str(v)])
    rendered = subprocess.check_output(cmd, text=True)
    docs = list(yaml.safe_load_all(rendered))
    totals = sum_workload_resources(docs)
    caps = read_manifest_caps(manifest)

    print(f"chart={chart.name}")
    print(f"  containers sum requests: cpu={fmt_cpu(totals['req_cpu'])} mem={fmt_mem(totals['req_mem'])}")
    print(f"  containers sum limits:   cpu={fmt_cpu(totals['lim_cpu'])} mem={fmt_mem(totals['lim_mem'])}")
    print(f"  manifest caps requests:  cpu={fmt_cpu(caps.get('req_cpu', 0))} mem={fmt_mem(caps.get('req_mem', 0))}")
    print(f"  manifest caps limits:    cpu={fmt_cpu(caps.get('lim_cpu', 0))} mem={fmt_mem(caps.get('lim_mem', 0))}")

    errors = []
    if totals["req_cpu"] > caps.get("req_cpu", 0):
        errors.append(f"sum requests cpu {fmt_cpu(totals['req_cpu'])} > requiredCpu {fmt_cpu(caps['req_cpu'])}")
    if totals["req_mem"] > caps.get("req_mem", 0):
        errors.append(f"sum requests mem {fmt_mem(totals['req_mem'])} > requiredMemory {fmt_mem(caps['req_mem'])}")
    if totals["lim_cpu"] > caps.get("lim_cpu", 0):
        errors.append(f"sum limits cpu {fmt_cpu(totals['lim_cpu'])} > limitedCpu {fmt_cpu(caps['lim_cpu'])}")
    if totals["lim_mem"] > caps.get("lim_mem", 0):
        errors.append(f"sum limits mem {fmt_mem(totals['lim_mem'])} > limitedMemory {fmt_mem(caps['lim_mem'])}")

    if errors:
        print("FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: container resource sums within OlaresManifest caps")
    return 0


if __name__ == "__main__":
    sys.exit(main())

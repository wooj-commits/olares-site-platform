import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// Process-local counters (reset on pod restart). Good enough for Phase 2 scrape.
const g = globalThis as unknown as {
  __scMetrics?: {
    req: Map<string, number>;
    err: Map<string, number>;
    latSum: Map<string, number>;
    latCount: Map<string, number>;
  };
};
function store() {
  if (!g.__scMetrics) {
    g.__scMetrics = {
      req: new Map(),
      err: new Map(),
      latSum: new Map(),
      latCount: new Map(),
    };
  }
  return g.__scMetrics;
}

export function recordMetric(method: string, path: string, status: number, seconds: number) {
  const s = store();
  const rk = `${method}|${path}|${status}`;
  s.req.set(rk, (s.req.get(rk) || 0) + 1);
  const lk = `${method}|${path}`;
  s.latSum.set(lk, (s.latSum.get(lk) || 0) + seconds);
  s.latCount.set(lk, (s.latCount.get(lk) || 0) + 1);
  if (status >= 500) s.err.set(lk, (s.err.get(lk) || 0) + 1);
}

export async function GET() {
  const s = store();
  const lines: string[] = [
    "# HELP http_requests_total Total HTTP requests",
    "# TYPE http_requests_total counter",
  ];
  for (const [k, n] of s.req) {
    const [method, path, status] = k.split("|");
    lines.push(`http_requests_total{method="${method}",path="${path}",status="${status}"} ${n}`);
  }
  lines.push("# HELP http_errors_total Total HTTP 5xx");
  lines.push("# TYPE http_errors_total counter");
  for (const [k, n] of s.err) {
    const [method, path] = k.split("|");
    lines.push(`http_errors_total{method="${method}",path="${path}"} ${n}`);
  }
  lines.push("# HELP http_request_duration_seconds_sum Request latency sum");
  lines.push("# TYPE http_request_duration_seconds_sum counter");
  lines.push("# HELP http_request_duration_seconds_count Request latency count");
  lines.push("# TYPE http_request_duration_seconds_count counter");
  for (const [k, sum] of s.latSum) {
    const [method, path] = k.split("|");
    const c = s.latCount.get(k) || 0;
    lines.push(`http_request_duration_seconds_sum{method="${method}",path="${path}"} ${sum.toFixed(6)}`);
    lines.push(`http_request_duration_seconds_count{method="${method}",path="${path}"} ${c}`);
  }
  return new NextResponse(lines.join("\n") + "\n", {
    headers: { "Content-Type": "text/plain; version=0.0.4" },
  });
}

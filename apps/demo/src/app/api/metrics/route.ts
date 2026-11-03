import { NextResponse } from "next/server";
import { metricsStore } from "@/lib/metrics";

export const dynamic = "force-dynamic";

export async function GET() {
  const s = metricsStore();
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

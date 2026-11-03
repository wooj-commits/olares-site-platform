import { NextRequest, NextResponse } from "next/server";
import { recordMetric } from "@/lib/metrics";

type Handler = (req: NextRequest, ctx?: any) => Promise<Response> | Response;

export function withMetrics(handler: Handler): Handler {
  return async (req, ctx) => {
    const start = performance.now();
    let status = 500;
    try {
      const res = await handler(req, ctx);
      status = res.status;
      return res;
    } catch (e) {
      status = 500;
      throw e;
    } finally {
      const path = new URL(req.url).pathname;
      recordMetric(req.method, path, status, (performance.now() - start) / 1000);
    }
  };
}

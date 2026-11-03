type Store = {
  req: Map<string, number>;
  err: Map<string, number>;
  latSum: Map<string, number>;
  latCount: Map<string, number>;
};

const g = globalThis as unknown as { __scMetrics?: Store };

export function metricsStore(): Store {
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
  const s = metricsStore();
  const rk = `${method}|${path}|${status}`;
  s.req.set(rk, (s.req.get(rk) || 0) + 1);
  const lk = `${method}|${path}`;
  s.latSum.set(lk, (s.latSum.get(lk) || 0) + seconds);
  s.latCount.set(lk, (s.latCount.get(lk) || 0) + 1);
  if (status >= 500) s.err.set(lk, (s.err.get(lk) || 0) + 1);
}

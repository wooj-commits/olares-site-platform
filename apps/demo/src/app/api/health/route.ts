import { NextResponse } from "next/server";
import { ensureSchema, getPool } from "@/lib/db";
import { minioConfigured, ensureBucket } from "@/lib/s3";
import { authEnabledOAuth, ensureAuthMigrated } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  const checks: Record<string, string> = {
    ok: "true",
    service: "olares-demo",
    oauth_google: authEnabledOAuth.google ? "enabled" : "disabled",
    oauth_github: authEnabledOAuth.github ? "enabled" : "disabled",
    minio: minioConfigured() ? "configured" : "missing",
  };
  try {
    await ensureAuthMigrated();
    checks.auth_schema = "ok";
  } catch (e) {
    checks.auth_schema = "error";
    checks.auth_schema_error = e instanceof Error ? e.message : "unknown";
  }
  try {
    await ensureSchema();
    const r = await getPool().query("select 1 as n");
    checks.postgres = r.rows[0]?.n === 1 ? "ok" : "bad";
  } catch (e) {
    checks.postgres = "error";
    checks.postgres_error = e instanceof Error ? e.message : "unknown";
  }
  try {
    if (minioConfigured()) {
      await ensureBucket();
      checks.minio_bucket = "ok";
    }
  } catch (e) {
    checks.minio_bucket = "error";
    checks.minio_error = e instanceof Error ? e.message : "unknown";
  }
  const healthy = checks.postgres === "ok" && checks.auth_schema === "ok";
  return NextResponse.json(checks, { status: healthy ? 200 : 503 });
}

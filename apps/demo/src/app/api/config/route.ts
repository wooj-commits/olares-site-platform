import { NextResponse } from "next/server";
import { authEnabledOAuth } from "@/lib/auth";
import { minioConfigured } from "@/lib/s3";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    oauth: authEnabledOAuth,
    minio: minioConfigured(),
  });
}

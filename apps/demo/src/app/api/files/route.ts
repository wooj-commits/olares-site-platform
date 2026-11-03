import { NextRequest, NextResponse } from "next/server";
import { auth, ensureAuthMigrated } from "@/lib/auth";
import { headers } from "next/headers";
import {
  minioConfigured,
  ensureBucket,
  getS3,
  getBucket,
  PutObjectCommand,
  ListObjectsV2Command,
  GetObjectCommand,
  DeleteObjectCommand,
  getSignedUrl,
} from "@/lib/s3";

export const dynamic = "force-dynamic";

async function requireUser() {
  await ensureAuthMigrated();
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session?.user?.id) return null;
  return session.user;
}

export async function GET(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  if (!minioConfigured()) {
    return NextResponse.json({ error: "minio not configured", files: [] }, { status: 503 });
  }
  await ensureBucket();
  const key = new URL(req.url).searchParams.get("key");
  const s3 = getS3();
  const Bucket = getBucket();
  if (key) {
    if (!key.startsWith(`${user.id}/`)) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    const url = await getSignedUrl(s3, new GetObjectCommand({ Bucket, Key: key }), {
      expiresIn: 300,
    });
    return NextResponse.json({ url });
  }
  const listed = await s3.send(
    new ListObjectsV2Command({ Bucket, Prefix: `${user.id}/`, MaxKeys: 100 }),
  );
  const files = (listed.Contents || []).map((o) => ({
    key: o.Key,
    size: o.Size,
    lastModified: o.LastModified,
  }));
  return NextResponse.json({ files });
}

export async function POST(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  if (!minioConfigured()) {
    return NextResponse.json({ error: "minio not configured" }, { status: 503 });
  }
  await ensureBucket();
  const form = await req.formData();
  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "file required" }, { status: 400 });
  }
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 120) || "upload.bin";
  const key = `${user.id}/${Date.now()}-${safeName}`;
  const buf = Buffer.from(await file.arrayBuffer());
  await getS3().send(
    new PutObjectCommand({
      Bucket: getBucket(),
      Key: key,
      Body: buf,
      ContentType: file.type || "application/octet-stream",
    }),
  );
  return NextResponse.json({ key, size: buf.length }, { status: 201 });
}

export async function DELETE(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  if (!minioConfigured()) {
    return NextResponse.json({ error: "minio not configured" }, { status: 503 });
  }
  const key = new URL(req.url).searchParams.get("key");
  if (!key || !key.startsWith(`${user.id}/`)) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }
  await getS3().send(new DeleteObjectCommand({ Bucket: getBucket(), Key: key }));
  return NextResponse.json({ ok: true });
}

import { NextResponse } from "next/server";
import { auth, ensureAuthMigrated } from "@/lib/auth";
import { headers } from "next/headers";
import { ensureSchema, getPool } from "@/lib/db";
import {
  minioConfigured,
  getS3,
  getBucket,
  ListObjectsV2Command,
  DeleteObjectCommand,
} from "@/lib/s3";

export const dynamic = "force-dynamic";

/** DELETE — remove current user's notes, files, and Better Auth rows. */
export async function DELETE() {
  await ensureAuthMigrated();
  const session = await auth.api.getSession({ headers: await headers() });
  const user = session?.user;
  if (!user?.id) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  await ensureSchema();
  const pool = getPool();
  await pool.query(`DELETE FROM notes WHERE user_id = $1`, [user.id]);

  if (minioConfigured()) {
    const s3 = getS3();
    const Bucket = getBucket();
    const listed = await s3.send(
      new ListObjectsV2Command({ Bucket, Prefix: `${user.id}/`, MaxKeys: 1000 }),
    );
    for (const o of listed.Contents || []) {
      if (o.Key) await s3.send(new DeleteObjectCommand({ Bucket, Key: o.Key }));
    }
  }

  // Better Auth core tables (ignore missing)
  for (const sql of [
    `DELETE FROM session WHERE "userId" = $1`,
    `DELETE FROM account WHERE "userId" = $1`,
    `DELETE FROM "user" WHERE id = $1`,
  ]) {
    try {
      await pool.query(sql, [user.id]);
    } catch {
      // column naming variants
      try {
        const alt = sql.replace(/"userId"/g, "user_id");
        await pool.query(alt, [user.id]);
      } catch {
        /* ignore */
      }
    }
  }

  return NextResponse.json({ ok: true, deletedUserId: user.id });
}

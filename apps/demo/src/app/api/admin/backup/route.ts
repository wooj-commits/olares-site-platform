import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import { createWriteStream, promises as fs } from "node:fs";
import path from "node:path";
import { pipeline } from "node:stream/promises";
import {
  minioConfigured,
  getS3,
  getBucket,
  ListObjectsV2Command,
  GetObjectCommand,
} from "@/lib/s3";
import { recordMetric } from "@/lib/metrics";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

function authorized(req: NextRequest): boolean {
  const token = (process.env.BACKUP_TOKEN || "").trim();
  if (!token) return false;
  const hdr = req.headers.get("authorization") || "";
  if (hdr === `Bearer ${token}`) return true;
  return (req.headers.get("x-backup-token") || "") === token;
}

function run(cmd: string, args: string[], env?: NodeJS.ProcessEnv): Promise<void> {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { env: { ...process.env, ...(env || {}) } });
    let err = "";
    p.stderr.on("data", (d) => { err += d.toString(); });
    p.on("error", reject);
    p.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} exited ${code}: ${err.slice(0, 500)}`));
    });
  });
}

export async function POST(req: NextRequest) {
  const start = performance.now();
  let status = 500;
  try {
    if (!authorized(req)) {
      status = 401;
      return NextResponse.json({ error: "unauthorized" }, { status });
    }
    const dbUrl = process.env.DATABASE_URL;
    if (!dbUrl) {
      status = 500;
      return NextResponse.json({ error: "DATABASE_URL missing" }, { status });
    }

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const work = path.join("/tmp", `olaresdemo-backup-${stamp}`);
    await fs.mkdir(work, { recursive: true });
    const sqlPath = path.join(work, "postgres.sql");
    const minioDir = path.join(work, "minio");
    await fs.mkdir(minioDir, { recursive: true });

    await run("pg_dump", ["--no-owner", "--no-acl", "-f", sqlPath, dbUrl]);

    let objectCount = 0;
    if (minioConfigured()) {
      const s3 = getS3();
      const Bucket = getBucket();
      let token: string | undefined;
      do {
        const out = await s3.send(
          new ListObjectsV2Command({ Bucket, ContinuationToken: token }),
        );
        for (const obj of out.Contents || []) {
          if (!obj.Key) continue;
          const got = await s3.send(new GetObjectCommand({ Bucket, Key: obj.Key }));
          const dest = path.join(minioDir, obj.Key);
          await fs.mkdir(path.dirname(dest), { recursive: true });
          if (got.Body) {
            await pipeline(got.Body as NodeJS.ReadableStream, createWriteStream(dest));
            objectCount += 1;
          }
        }
        token = out.IsTruncated ? out.NextContinuationToken : undefined;
      } while (token);
    }

    const tarName = `olaresdemo-${stamp}.tar.gz`;
    const tarPath = path.join("/tmp", tarName);
    await run("tar", ["-czf", tarPath, "-C", work, "."]);

    // Persist under appData when mounted (optional)
    const persist = process.env.BACKUP_DIR || "";
    if (persist) {
      await fs.mkdir(persist, { recursive: true });
      await fs.copyFile(tarPath, path.join(persist, tarName));
    }

    const buf = await fs.readFile(tarPath);
    // cleanup
    await fs.rm(work, { recursive: true, force: true }).catch(() => {});
    await fs.unlink(tarPath).catch(() => {});

    status = 200;
    return new NextResponse(buf, {
      status: 200,
      headers: {
        "Content-Type": "application/gzip",
        "Content-Disposition": `attachment; filename="${tarName}"`,
        "X-Backup-Objects": String(objectCount),
        "X-Backup-App": "olaresdemo",
      },
    });
  } catch (e) {
    status = 500;
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "backup failed" },
      { status },
    );
  } finally {
    recordMetric("POST", "/api/admin/backup", status, (performance.now() - start) / 1000);
  }
}

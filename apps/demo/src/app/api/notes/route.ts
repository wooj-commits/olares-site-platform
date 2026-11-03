import { NextRequest, NextResponse } from "next/server";
import { auth, ensureAuthMigrated } from "@/lib/auth";
import { ensureSchema, getPool } from "@/lib/db";
import { headers } from "next/headers";

export const dynamic = "force-dynamic";

async function requireUser() {
  await ensureAuthMigrated();
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session?.user?.id) return null;
  return session.user;
}

export async function GET() {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  await ensureSchema();
  const { rows } = await getPool().query(
    `SELECT id, title, body, created_at FROM notes WHERE user_id = $1 ORDER BY id DESC LIMIT 100`,
    [user.id],
  );
  return NextResponse.json({ notes: rows });
}

export async function POST(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const title = String(body.title || "").trim();
  const text = String(body.body || "").trim();
  if (!title) return NextResponse.json({ error: "title required" }, { status: 400 });
  await ensureSchema();
  const { rows } = await getPool().query(
    `INSERT INTO notes (user_id, title, body) VALUES ($1, $2, $3)
     RETURNING id, title, body, created_at`,
    [user.id, title, text],
  );
  return NextResponse.json({ note: rows[0] }, { status: 201 });
}

export async function DELETE(req: NextRequest) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const id = Number(new URL(req.url).searchParams.get("id"));
  if (!Number.isFinite(id)) return NextResponse.json({ error: "id required" }, { status: 400 });
  await ensureSchema();
  await getPool().query(`DELETE FROM notes WHERE id = $1 AND user_id = $2`, [id, user.id]);
  return NextResponse.json({ ok: true });
}

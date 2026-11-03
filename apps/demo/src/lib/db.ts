import { Pool } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var __olaresDemoPool: Pool | undefined;
}

function createPool() {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error("DATABASE_URL is not set");
  }
  return new Pool({ connectionString: url, max: 10 });
}

export function getPool() {
  if (!globalThis.__olaresDemoPool) {
    globalThis.__olaresDemoPool = createPool();
  }
  return globalThis.__olaresDemoPool;
}

export async function ensureSchema() {
  const pool = getPool();
  await pool.query(`
    CREATE TABLE IF NOT EXISTS notes (
      id SERIAL PRIMARY KEY,
      user_id TEXT NOT NULL,
      title TEXT NOT NULL,
      body TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS notes_user_id_idx ON notes (user_id);
  `);
}

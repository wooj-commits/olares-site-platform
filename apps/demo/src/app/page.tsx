"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Note = { id: number; title: string; body: string; created_at: string };
type FileItem = { key?: string; size?: number; lastModified?: string };
type SessionUser = { id: string; name?: string | null; email?: string | null };

export default function HomePage() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [oauth, setOauth] = useState({ google: false, github: false });
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [health, setHealth] = useState<Record<string, string> | null>(null);

  const refreshSession = useCallback(async () => {
    const res = await fetch("/api/auth/get-session", { credentials: "include" });
    if (!res.ok) {
      setUser(null);
      return null;
    }
    const data = await res.json();
    const u = data?.user ?? data?.session?.user ?? null;
    setUser(u);
    return u as SessionUser | null;
  }, []);

  const loadData = useCallback(async () => {
    const [n, f] = await Promise.all([
      fetch("/api/notes", { credentials: "include" }),
      fetch("/api/files", { credentials: "include" }),
    ]);
    if (n.ok) {
      const j = await n.json();
      setNotes(j.notes || []);
    }
    if (f.ok) {
      const j = await f.json();
      setFiles(j.files || []);
    } else if (f.status === 503) {
      setFiles([]);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [cfg, h] = await Promise.all([
          fetch("/api/config").then((r) => r.json()),
          fetch("/api/health").then((r) => r.json()),
        ]);
        setOauth(cfg.oauth || { google: false, github: false });
        setHealth(h);
        const u = await refreshSession();
        if (u) await loadData();
      } catch (e) {
        setError(e instanceof Error ? e.message : "failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, [loadData, refreshSession]);

  async function onAuth(e: FormEvent) {
    e.preventDefault();
    setError("");
    const path = mode === "signup" ? "/api/auth/sign-up/email" : "/api/auth/sign-in/email";
    const payload =
      mode === "signup"
        ? { email, password, name: name || email.split("@")[0] }
        : { email, password };
    const res = await fetch(path, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const t = await res.text();
      setError(t || `auth failed (${res.status})`);
      return;
    }
    const u = await refreshSession();
    if (u) await loadData();
  }

  async function signOut() {
    await fetch("/api/auth/sign-out", { method: "POST", credentials: "include" });
    setUser(null);
    setNotes([]);
    setFiles([]);
  }

  async function addNote(e: FormEvent) {
    e.preventDefault();
    setError("");
    const res = await fetch("/api/notes", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title, body }),
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    setTitle("");
    setBody("");
    await loadData();
  }

  async function deleteNote(id: number) {
    await fetch(`/api/notes?id=${id}`, { method: "DELETE", credentials: "include" });
    await loadData();
  }

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const fd = new FormData(e.currentTarget);
    const res = await fetch("/api/files", { method: "POST", credentials: "include", body: fd });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    e.currentTarget.reset();
    await loadData();
  }

  async function downloadFile(key: string) {
    const res = await fetch(`/api/files?key=${encodeURIComponent(key)}`, {
      credentials: "include",
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    const j = await res.json();
    window.open(j.url, "_blank");
  }

  if (loading) return <p className="sub">Loading…</p>;

  return (
    <>
      <h1>Olares site platform demo</h1>
      <p className="sub">
        Next.js single container · Better Auth · Postgres middleware · MinIO
      </p>

      <div className="card">
        <div className="badge">/api/health</div>
        {health ? (
          <pre style={{ margin: "0.5rem 0 0", fontSize: 12 }}>
            {JSON.stringify(health, null, 2)}
          </pre>
        ) : null}
      </div>

      {!user ? (
        <div className="card">
          <div className="row" style={{ marginBottom: "1rem" }}>
            <button type="button" className={mode === "signin" ? "" : "secondary"} onClick={() => setMode("signin")}>
              Sign in
            </button>
            <button type="button" className={mode === "signup" ? "" : "secondary"} onClick={() => setMode("signup")}>
              Sign up
            </button>
          </div>
          <form onSubmit={onAuth} className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
            {mode === "signup" ? (
              <label>
                Name
                <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
              </label>
            ) : null}
            <label>
              Email
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            </label>
            <label>
              Password
              <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "signup" ? "new-password" : "current-password"} />
            </label>
            <button type="submit">{mode === "signup" ? "Create account" : "Sign in"}</button>
          </form>
          <div className="row" style={{ marginTop: "1rem" }}>
            {oauth.google ? (
              <a className="secondary" href="/api/auth/sign-in/social?provider=google">
                Continue with Google
              </a>
            ) : (
              <span className="badge">Google OAuth disabled (set GOOGLE_CLIENT_ID/SECRET)</span>
            )}
            {oauth.github ? (
              <a className="secondary" href="/api/auth/sign-in/social?provider=github">
                Continue with GitHub
              </a>
            ) : (
              <span className="badge">GitHub OAuth disabled (set GITHUB_CLIENT_ID/SECRET)</span>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="card row" style={{ justifyContent: "space-between" }}>
            <div>
              Signed in as <strong>{user.email || user.name || user.id}</strong>
            </div>
            <button type="button" className="secondary" onClick={signOut}>
              Sign out
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Notes (Postgres)</h2>
            <form onSubmit={addNote} className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
              <label>
                Title
                <input required value={title} onChange={(e) => setTitle(e.target.value)} />
              </label>
              <label>
                Body
                <textarea value={body} onChange={(e) => setBody(e.target.value)} />
              </label>
              <button type="submit">Add note</button>
            </form>
            <ul className="list">
              {notes.map((n) => (
                <li key={n.id}>
                  <div>
                    <strong>{n.title}</strong>
                    <div className="badge">{new Date(n.created_at).toLocaleString()}</div>
                    <div>{n.body}</div>
                  </div>
                  <button type="button" className="danger" onClick={() => deleteNote(n.id)}>
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Files (MinIO)</h2>
            <form onSubmit={onUpload} className="row">
              <input type="file" name="file" required />
              <button type="submit">Upload</button>
            </form>
            <ul className="list">
              {files.map((f) => (
                <li key={f.key}>
                  <div>
                    <code>{f.key}</code>
                    <div className="badge">{f.size ?? 0} bytes</div>
                  </div>
                  {f.key ? (
                    <button type="button" className="secondary" onClick={() => downloadFile(f.key!)}>
                      Download
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {error ? <p className="err">{error}</p> : null}
    </>
  );
}

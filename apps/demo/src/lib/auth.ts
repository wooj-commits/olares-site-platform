import { betterAuth } from "better-auth";
import { getMigrations } from "better-auth/db/migration";
import { Pool } from "pg";

function databaseUrl() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  return url;
}

const googleId = process.env.GOOGLE_CLIENT_ID?.trim();
const googleSecret = process.env.GOOGLE_CLIENT_SECRET?.trim();
const githubId = process.env.GITHUB_CLIENT_ID?.trim();
const githubSecret = process.env.GITHUB_CLIENT_SECRET?.trim();

const socialProviders: Record<string, { clientId: string; clientSecret: string }> = {};
if (googleId && googleSecret) {
  socialProviders.google = { clientId: googleId, clientSecret: googleSecret };
}
if (githubId && githubSecret) {
  socialProviders.github = { clientId: githubId, clientSecret: githubSecret };
}

export const authEnabledOAuth = {
  google: Boolean(googleId && googleSecret),
  github: Boolean(githubId && githubSecret),
};

const buildPlaceholder = process.env.NEXT_PHASE === "phase-production-build";
const connectionString =
  process.env.DATABASE_URL ||
  (buildPlaceholder ? "postgresql://build:build@127.0.0.1:5432/build" : databaseUrl());

/** Optional static override; otherwise derive from request Host behind Envoy. */
const fallbackURL = (
  process.env.BETTER_AUTH_URL ||
  process.env.NEXT_PUBLIC_APP_URL ||
  ""
).replace(/\/$/, "");

const allowedHosts = (
  process.env.BETTER_AUTH_ALLOWED_HOSTS ||
  "*.woojinc1205.olares.com,*.olares.com,localhost,localhost:3000,127.0.0.1,127.0.0.1:3000"
)
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const authOptions = {
  database: new Pool({ connectionString, max: 5 }),
  secret: process.env.AUTH_SECRET || (buildPlaceholder ? "build-time-placeholder-secret-32chars" : undefined),
  // Dynamic base URL from X-Forwarded-Host / Host — no per-install BETTER_AUTH_URL required.
  baseURL: {
    allowedHosts,
    protocol: "https" as const,
    ...(fallbackURL ? { fallback: fallbackURL } : {}),
  },
  advanced: {
    // Olares Envoy sets X-Forwarded-Host / X-Forwarded-Proto
    trustedProxyHeaders: true,
  },
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
  },
  socialProviders,
  trustedOrigins: [
    "https://*.woojinc1205.olares.com",
    "https://*.olares.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ],
};

export const auth = betterAuth(authOptions);

let migratePromise: Promise<void> | null = null;

/** Create Better Auth tables on first use (idempotent). */
export function ensureAuthMigrated(): Promise<void> {
  if (buildPlaceholder) return Promise.resolve();
  if (!migratePromise) {
    migratePromise = (async () => {
      const { runMigrations } = await getMigrations(authOptions as never);
      await runMigrations();
    })().catch((err) => {
      migratePromise = null;
      throw err;
    });
  }
  return migratePromise;
}

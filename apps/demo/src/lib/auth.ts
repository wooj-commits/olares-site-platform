import { betterAuth } from "better-auth";
import { Pool } from "pg";

function databaseUrl() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  return url;
}

function baseURL() {
  return (
    process.env.BETTER_AUTH_URL ||
    process.env.NEXT_PUBLIC_APP_URL ||
    "http://localhost:3000"
  ).replace(/\/$/, "");
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

// better-auth is constructed once per process. During `next build` we may not
 // have real credentials — use placeholders so the module can be evaluated.
const buildPlaceholder = process.env.NEXT_PHASE === "phase-production-build";
const connectionString =
  process.env.DATABASE_URL ||
  (buildPlaceholder ? "postgresql://build:build@127.0.0.1:5432/build" : databaseUrl());

export const auth = betterAuth({
  database: new Pool({ connectionString, max: 5 }),
  secret: process.env.AUTH_SECRET || (buildPlaceholder ? "build-time-placeholder-secret-32chars" : undefined),
  baseURL: baseURL(),
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
  },
  socialProviders,
  trustedOrigins: [baseURL()],
});

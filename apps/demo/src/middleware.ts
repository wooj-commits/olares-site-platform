import { NextRequest, NextResponse } from "next/server";

type Rule = { from_path: string; to_url: string; status?: number };

function loadRules(): Rule[] {
  const raw = process.env.REDIRECT_RULES_JSON || "[]";
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname;
  for (const rule of loadRules()) {
    const from = (rule.from_path || "").trim();
    if (!from) continue;
    if (path === from || path.startsWith(from.endsWith("/") ? from : from + "/")) {
      const status = rule.status === 301 ? 301 : 302;
      return NextResponse.redirect(rule.to_url, status);
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};

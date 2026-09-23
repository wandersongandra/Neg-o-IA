import { NextRequest, NextResponse } from "next/server";

const SAFE_SEGMENT = /^[A-Za-z0-9_-]{1,128}$/;

export function enforceSameOriginMutation(request: NextRequest): NextResponse | null {
  if (process.env.NODE_ENV !== "production") return null;
  const origin = request.headers.get("origin");
  if (!origin || origin !== request.nextUrl.origin) {
    return NextResponse.json({ error: "origin_not_allowed" }, { status: 403 });
  }
  return null;
}

export function isSafeDynamicSegment(value: string): boolean {
  return SAFE_SEGMENT.test(value);
}

export function resolvePublicWsBase(request: NextRequest, configured: string): string | null {
  const fallbackProtocol = request.nextUrl.protocol === "https:" ? "wss:" : "ws:";
  const candidate = configured || `${fallbackProtocol}//${request.nextUrl.host}`;
  try {
    const parsed = new URL(candidate);
    if (parsed.protocol !== "ws:" && parsed.protocol !== "wss:") return null;
    if (process.env.NODE_ENV === "production" && parsed.protocol !== "wss:") return null;
    parsed.pathname = parsed.pathname.replace(/\/$/, "");
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

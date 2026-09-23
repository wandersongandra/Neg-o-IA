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


const IP_LITERAL = /^[0-9A-Fa-f:.]{3,64}$/;

export function trustedClientIpHeadersFromHeaders(
  headers: Headers,
): Record<string, string> {
  if (process.env.NODE_ENV !== "production") return {};
  const realIp = headers.get("x-real-ip")?.trim() ?? "";
  if (!IP_LITERAL.test(realIp)) return {};
  return {
    "X-Real-IP": realIp,
    "X-Forwarded-For": realIp,
  };
}

export function trustedClientIpHeaders(request: NextRequest): Record<string, string> {
  return trustedClientIpHeadersFromHeaders(request.headers);
}

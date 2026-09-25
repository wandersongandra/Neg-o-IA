import { NextRequest, NextResponse } from "next/server";

const SAFE_SEGMENT = /^[A-Za-z0-9_-]{1,128}$/;

function enforceFetchMetadata(request: NextRequest): NextResponse | null {
  if (process.env.NODE_ENV !== "production") return null;
  const site = request.headers.get("sec-fetch-site");
  if (site && site !== "same-origin") {
    return NextResponse.json({ error: "cross_site_request_blocked" }, { status: 403 });
  }
  const destination = request.headers.get("sec-fetch-dest");
  if (destination && destination !== "empty") {
    return NextResponse.json({ error: "unexpected_fetch_destination" }, { status: 403 });
  }
  return null;
}

export function enforceSameOriginMutation(request: NextRequest): NextResponse | null {
  const metadataBlock = enforceFetchMetadata(request);
  if (metadataBlock) return metadataBlock;
  if (process.env.NODE_ENV !== "production") return null;
  const origin = request.headers.get("origin");
  if (!origin || origin !== request.nextUrl.origin) {
    return NextResponse.json({ error: "origin_not_allowed" }, { status: 403 });
  }
  return null;
}

export function enforceSensitiveSameOriginGet(request: NextRequest): NextResponse | null {
  return enforceFetchMetadata(request);
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
  headers: Pick<Headers, "get">,
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

import { NextRequest, NextResponse } from "next/server";
import { resolveApiConfig } from "@/lib/env";
import { getSessionToken } from "@/lib/session-cookie";
import { trustedClientIpHeaders } from "@/lib/request-security";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const { apiUrl } = resolveApiConfig();
  const token = getSessionToken(request.cookies);
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  try {
    const upstream = await fetch(`${apiUrl}/security/status`, {
      headers: {
        Authorization: `Bearer ${token}`,
        ...trustedClientIpHeaders(request),
      },
      cache: "no-store",
    });
    const payload = await upstream.json();
    return NextResponse.json(payload, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { error: "identity_dependency_unavailable" },
      { status: 503 },
    );
  }
}

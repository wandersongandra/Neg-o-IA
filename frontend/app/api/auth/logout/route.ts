import { NextRequest, NextResponse } from "next/server";
import { resolveApiConfig } from "@/lib/env";
import {
  DEV_SESSION_COOKIE,
  PROD_SESSION_COOKIE,
  getSessionToken,
} from "@/lib/session-cookie";
import {
  enforceSameOriginMutation,
  trustedClientIpHeaders,
} from "@/lib/request-security";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const originBlock = enforceSameOriginMutation(request);
  if (originBlock) return originBlock;
  const { apiUrl } = resolveApiConfig();
  const token = getSessionToken(request.cookies);
  if (token) {
    try {
      await fetch(`${apiUrl}/security/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          ...trustedClientIpHeaders(request),
        },
        cache: "no-store",
      });
    } catch {
      // Always remove the browser cookie; the backend will reject expired/revoked state.
    }
  }
  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete(DEV_SESSION_COOKIE);
  response.cookies.delete(PROD_SESSION_COOKIE);
  return response;
}

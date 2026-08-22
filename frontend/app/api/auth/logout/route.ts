import { NextRequest, NextResponse } from "next/server";
import { resolveApiConfig } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const { apiUrl } = resolveApiConfig();
  const token = request.cookies.get("sophie_session")?.value;
  if (token) {
    try {
      await fetch(`${apiUrl}/security/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
    } catch {
      // Always remove the browser cookie; the backend will reject expired/revoked state.
    }
  }
  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete("sophie_session");
  return response;
}

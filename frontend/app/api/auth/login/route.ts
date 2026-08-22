import { NextRequest, NextResponse } from "next/server";
import { resolveApiConfig } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const { apiUrl } = resolveApiConfig();
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }
  try {
    const upstream = await fetch(`${apiUrl}/security/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const payload = (await upstream.json()) as Record<string, unknown>;
    if (!upstream.ok) return NextResponse.json(payload, { status: upstream.status });
    const response = NextResponse.json(
      {
        user_id: payload.user_id,
        username: payload.username,
        display_name: payload.display_name,
        expires_in: payload.expires_in,
      },
      { status: 200 },
    );
    if (typeof payload.access_token === "string") {
      response.cookies.set("sophie_session", payload.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: typeof payload.expires_in === "number" ? payload.expires_in : 28_800,
        path: "/",
      });
    }
    return response;
  } catch {
    return NextResponse.json(
      { error: "identity_dependency_unavailable" },
      { status: 503 },
    );
  }
}

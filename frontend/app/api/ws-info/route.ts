import { NextRequest, NextResponse } from "next/server";
import { resolveApiConfig, resolveWsUrl } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const { apiUrl } = resolveApiConfig();
  const purpose = request.nextUrl.searchParams.get("purpose") ?? "conversation";
  const sessionId = request.nextUrl.searchParams.get("session_id");
  if (purpose !== "conversation" && purpose !== "voice") {
    return NextResponse.json({ error: "invalid_ticket_purpose" }, { status: 400 });
  }
  if (purpose === "voice" && !sessionId) {
    return NextResponse.json({ error: "voice_session_required" }, { status: 400 });
  }
  const configuredWs = resolveWsUrl();
  const wsBase =
    configuredWs && /^wss?:\/\//.test(configuredWs)
      ? configuredWs
      : apiUrl.replace(/^http/, "ws");

  try {
    const sessionToken = request.cookies.get("sophie_session")?.value;
    const res = await fetch(`${apiUrl}/security/ws-ticket`, {
      method: "POST",
      headers: {
        ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ purpose, session_id: sessionId }),
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json(
        { error: "ticket_unavailable" },
        { status: res.status === 401 || res.status === 403 ? res.status : 502 },
      );
    }
    const payload = (await res.json()) as {
      ticket?: unknown;
      expires_in?: unknown;
      purpose?: unknown;
      session_id?: unknown;
    };
    if (typeof payload.ticket !== "string" || payload.ticket.length === 0) {
      return NextResponse.json({ error: "ticket_unavailable" }, { status: 502 });
    }
    return NextResponse.json(
      {
        ticket: payload.ticket,
        ws_base: wsBase,
        expires_in: payload.expires_in,
        purpose: payload.purpose,
        session_id: payload.session_id,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return NextResponse.json(
      { error: "ticket_unavailable" },
      { status: 502 },
    );
  }
}

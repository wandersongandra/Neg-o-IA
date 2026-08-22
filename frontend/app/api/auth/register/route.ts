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
    const upstream = await fetch(`${apiUrl}/security/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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

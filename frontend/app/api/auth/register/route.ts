import { NextRequest, NextResponse } from "next/server";
import {
  resolveApiConfig,
  resolveRuntimeEnv,
  resolveWorkerServiceBinding,
} from "@/lib/env";
import {
  enforceSameOriginMutation,
  trustedClientIpHeaders,
} from "@/lib/request-security";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const originBlock = enforceSameOriginMutation(request);
  if (originBlock) return originBlock;
  const { apiUrl } = resolveApiConfig();
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }
  try {
    const bootstrapSecret = resolveRuntimeEnv("SOPHIE_BOOTSTRAP_SECRET");
    const upstreamRequest = new Request(`${apiUrl}/security/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(bootstrapSecret
          ? { "X-Ultron-Bootstrap-Secret": bootstrapSecret }
          : {}),
        ...trustedClientIpHeaders(request),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const service = resolveWorkerServiceBinding("SOPHIE_API");
    const upstream = service
      ? await service.fetch(upstreamRequest)
      : await fetch(upstreamRequest);
    const payload = await upstream.json();
    return NextResponse.json(payload, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { error: "identity_dependency_unavailable" },
      { status: 503 },
    );
  }
}

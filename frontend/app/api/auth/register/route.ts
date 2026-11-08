import { NextRequest, NextResponse } from "next/server";
import { resolveApiConfig, resolveRuntimeEnv } from "@/lib/env";
import {
  enforceSameOriginMutation,
  trustedClientIpHeaders,
} from "@/lib/request-security";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const publicOrigin = resolveRuntimeEnv("SOPHIE_PUBLIC_ORIGIN");
  const apiUrlFromRuntime = resolveRuntimeEnv("SOPHIE_API_URL");
  const bootstrapFromRuntime = resolveRuntimeEnv("SOPHIE_BOOTSTRAP_SECRET");
  console.log("[ultron-register-runtime-diagnostic]", JSON.stringify({
    nodeProduction: process.env.NODE_ENV === "production",
    runtimePublicOrigin: Boolean(publicOrigin),
    runtimePublicOriginMatchesRequest: publicOrigin === request.nextUrl.origin,
    processPublicOrigin: Boolean(process.env.SOPHIE_PUBLIC_ORIGIN),
    runtimeApiUrl: Boolean(apiUrlFromRuntime),
    processApiUrl: Boolean(process.env.SOPHIE_API_URL),
    runtimeBootstrapSecret: Boolean(bootstrapFromRuntime),
  }));
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
    const upstream = await fetch(`${apiUrl}/security/register`, {
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
    const payload = await upstream.json();
    return NextResponse.json(payload, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { error: "identity_dependency_unavailable" },
      { status: 503 },
    );
  }
}

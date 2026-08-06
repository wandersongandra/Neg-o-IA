import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const apiUrl = process.env.NEGAO_API_URL ?? "http://localhost:8000";
  const apiKey = process.env.NEGAO_API_KEY ?? "negao-dev-api-key";
  const configuredWs = process.env.NEGAO_WS_URL ?? "";
  const wsBase =
    configuredWs && /^wss?:\/\//.test(configuredWs)
      ? configuredWs
      : apiUrl.replace(/^http/, "ws");
  return NextResponse.json(
    { api_key: apiKey, ws_base: wsBase },
    { headers: { "Cache-Control": "no-store" } },
  );
}

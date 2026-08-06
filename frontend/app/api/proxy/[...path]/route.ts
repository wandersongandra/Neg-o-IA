import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const API_URL = process.env.NEGAO_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEGAO_API_KEY ?? "negao-dev-api-key";
const VOICE_TIMEOUT_MS = 35_000;
const DEFAULT_TIMEOUT_MS = 60_000;

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${API_URL}/${path.join("/")}${req.nextUrl.search}`;
  const timeoutMs = path.includes("voice")
    ? VOICE_TIMEOUT_MS
    : DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers: Record<string, string> = { "X-API-Key": API_KEY };
    let body: string | FormData | undefined;
    if (req.method === "POST") {
      const contentType = req.headers.get("content-type") ?? "";
      if (contentType.includes("multipart/form-data")) {
        body = await req.formData();
      } else {
        if (contentType) headers["Content-Type"] = contentType;
        body = await req.text();
      }
    }
    const res = await fetch(target, {
      method: req.method,
      headers,
      body,
      signal: controller.signal,
      cache: "no-store",
    });
    const resContentType = res.headers.get("content-type") ?? "";
    const resHeaders = new Headers();
    if (resContentType) resHeaders.set("Content-Type", resContentType);
    resHeaders.set("Cache-Control", "no-store");
    if (
      resContentType.startsWith("text/") ||
      resContentType.includes("json") ||
      resContentType.includes("xml")
    ) {
      return new Response(await res.text(), {
        status: res.status,
        headers: resHeaders,
      });
    }
    return new Response(await res.arrayBuffer(), {
      status: res.status,
      headers: resHeaders,
    });
  } catch (err) {
    const detail =
      err instanceof Error && err.name === "AbortError"
        ? "request timed out"
        : err instanceof Error
          ? err.message
          : String(err);
    return Response.json({ error: "proxy_error", detail }, { status: 502 });
  } finally {
    clearTimeout(timer);
  }
}

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

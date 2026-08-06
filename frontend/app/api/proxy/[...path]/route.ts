import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const API_URL = process.env.NEGAO_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEGAO_API_KEY ?? "negao-dev-api-key";
const VOICE_TIMEOUT_MS = 35_000;
const DEFAULT_TIMEOUT_MS = 60_000;

type Method = "GET" | "POST" | "PATCH" | "DELETE";

interface AllowEntry {
  path: string;
  methods: Method[];
}

const ALLOWLIST: AllowEntry[] = [
  { path: "brain/status", methods: ["GET"] },
  { path: "brain/router", methods: ["GET"] },
  { path: "brain/complete", methods: ["POST"] },
  { path: "brain/config", methods: ["GET", "PATCH"] },
  { path: "conversation/status", methods: ["GET"] },
  { path: "conversation/sessions", methods: ["GET", "POST"] },
  { path: "conversation/sessions/:id", methods: ["GET", "PATCH", "DELETE"] },
  { path: "conversation/sessions/:id/messages", methods: ["GET", "POST"] },
  { path: "voice/status", methods: ["GET"] },
  { path: "voice/transcribe", methods: ["POST"] },
  { path: "voice/synthesize", methods: ["POST"] },
  { path: "memory/status", methods: ["GET"] },
  { path: "database/status", methods: ["GET"] },
  { path: "events/status", methods: ["GET"] },
  { path: "security/status", methods: ["GET"] },
  { path: "monitoring/logs", methods: ["GET"] },
  { path: "healthz", methods: ["GET"] },
  { path: "readyz", methods: ["GET"] },
];

function matchAllowlist(path: string, method: string): boolean {
  const methodUpper = method.toUpperCase() as Method;
  for (const entry of ALLOWLIST) {
    const entrySegments = entry.path.split("/");
    const pathSegments = path.split("/");
    if (entrySegments.length !== pathSegments.length) continue;
    let ok = true;
    for (let i = 0; i < entrySegments.length; i++) {
      const es = entrySegments[i];
      const ps = pathSegments[i];
      if (es.startsWith(":")) {
        if (!ps) {
          ok = false;
          break;
        }
        continue;
      }
      if (es !== ps) {
        ok = false;
        break;
      }
    }
    if (ok) return entry.methods.includes(methodUpper);
  }
  return false;
}

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const joined = path.join("/");
  if (!matchAllowlist(joined, req.method)) {
    return Response.json(
      { error: "not_allowed", detail: "Rota ou método não permitido pelo proxy." },
      { status: 403 },
    );
  }

  const target = `${API_URL}/${joined}${req.nextUrl.search}`;
  const timeoutMs = path.includes("voice")
    ? VOICE_TIMEOUT_MS
    : DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers: Record<string, string> = { "X-API-Key": API_KEY };
    let body: string | FormData | undefined;
    if (req.method === "POST" || req.method === "PATCH") {
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
    const isTimeout =
      err instanceof Error && err.name === "AbortError";
    return Response.json(
      {
        error: "proxy_error",
        detail: isTimeout
          ? "O servidor demorou para responder. Tente novamente."
          : "Falha de comunicação com o servidor.",
      },
      { status: 502 },
    );
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

export async function PATCH(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

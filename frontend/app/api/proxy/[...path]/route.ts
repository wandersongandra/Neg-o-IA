import type { NextRequest } from "next/server";
import { resolveApiConfig } from "@/lib/env";
import { getSessionToken } from "@/lib/session-cookie";
import {
  enforceSameOriginMutation,
  isSafeDynamicSegment,
  trustedClientIpHeaders,
} from "@/lib/request-security";

export const dynamic = "force-dynamic";

const { apiUrl: API_URL, serviceApiKey: SERVICE_API_KEY } = resolveApiConfig();
const VOICE_TIMEOUT_MS = 35_000;
const DEFAULT_TIMEOUT_MS = 60_000;
const DEFAULT_MAX_BODY_BYTES = 128 * 1024;
const KNOWLEDGE_MAX_BODY_BYTES = 256 * 1024;
const VOICE_MAX_BODY_BYTES = 12 * 1024 * 1024;
const VISION_MAX_BODY_BYTES = 12 * 1024 * 1024;

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
  { path: "memory/long-term", methods: ["POST"] },
  { path: "memory/long-term/:id", methods: ["DELETE"] },
  { path: "memory/search", methods: ["GET"] },
  { path: "memory/policy", methods: ["GET", "PATCH"] },
  { path: "knowledge/documents", methods: ["GET", "POST"] },
  { path: "knowledge/documents/:id", methods: ["DELETE"] },
  { path: "knowledge/search", methods: ["GET"] },
  { path: "reasoning/resolve", methods: ["POST"] },
  { path: "planner/plans", methods: ["POST"] },
  { path: "planner/plans/:id", methods: ["GET"] },
  { path: "planner/plans/:id/replan", methods: ["POST"] },
  { path: "planner/plans/:id/execute", methods: ["POST"] },
  { path: "tool-manager/catalog", methods: ["GET"] },
  { path: "tool-manager/execute", methods: ["POST"] },
  { path: "automation/capabilities", methods: ["GET"] },
  { path: "automation/rules", methods: ["GET", "POST"] },
  { path: "automation/rules/:id", methods: ["PATCH", "DELETE"] },
  { path: "automation/evaluate", methods: ["POST"] },
  { path: "vision/status", methods: ["GET"] },
  { path: "vision/analyze", methods: ["POST"] },
  { path: "events/status", methods: ["GET"] },
  { path: "security/status", methods: ["GET"] },
  { path: "monitoring/health", methods: ["GET"] },
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
      const expected = entrySegments[i];
      const actual = pathSegments[i];
      if (expected.startsWith(":")) {
        if (!actual || !isSafeDynamicSegment(actual)) {
          ok = false;
          break;
        }
        continue;
      }
      if (expected !== actual) {
        ok = false;
        break;
      }
    }
    if (ok) return entry.methods.includes(methodUpper);
  }
  return false;
}

function buildTarget(path: string[], search: string): string {
  const target = new URL(API_URL);
  const prefix = target.pathname.replace(/\/$/, "");
  target.pathname = `${prefix}/${path.map((segment) => encodeURIComponent(segment)).join("/")}`;
  target.search = search;
  target.hash = "";
  return target.toString();
}

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const mutationBlock =
    req.method === "GET" ? null : enforceSameOriginMutation(req);
  if (mutationBlock) return mutationBlock;

  const joined = path.join("/");
  if (!matchAllowlist(joined, req.method)) {
    return Response.json(
      { error: "not_allowed", detail: "Rota ou método não permitido pelo proxy." },
      { status: 403 },
    );
  }

  const isVoice = path.includes("voice");
  const isKnowledge = path[0] === "knowledge";
  const isVision = path[0] === "vision";
  const timeoutMs = isVoice ? VOICE_TIMEOUT_MS : DEFAULT_TIMEOUT_MS;
  const maxBodyBytes = isVoice
    ? VOICE_MAX_BODY_BYTES
    : isVision
      ? VISION_MAX_BODY_BYTES
      : isKnowledge
        ? KNOWLEDGE_MAX_BODY_BYTES
        : DEFAULT_MAX_BODY_BYTES;
  const declaredLength = Number(req.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > maxBodyBytes) {
    return Response.json({ error: "payload_too_large" }, { status: 413 });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers: Record<string, string> = {
      Accept: "*/*",
      ...trustedClientIpHeaders(req),
    };
    const sessionToken = getSessionToken(req.cookies);
    if (sessionToken) {
      headers.Authorization = `Bearer ${sessionToken}`;
    } else if (SERVICE_API_KEY && process.env.NODE_ENV !== "production") {
      headers["X-API-Key"] = SERVICE_API_KEY;
    }

    let body: BodyInit | undefined;
    if (req.method === "POST" || req.method === "PATCH") {
      const contentType = req.headers.get("content-type") ?? "";
      if (contentType) headers["Content-Type"] = contentType;
      const raw = new Uint8Array(await req.arrayBuffer());
      if (raw.byteLength > maxBodyBytes) {
        return Response.json({ error: "payload_too_large" }, { status: 413 });
      }
      body = raw.byteLength > 0 ? raw : undefined;
    }

    const res = await fetch(buildTarget(path, req.nextUrl.search), {
      method: req.method,
      headers,
      body,
      signal: controller.signal,
      cache: "no-store",
    });

    const resContentType = res.headers.get("content-type") ?? "";
    const resHeaders = new Headers({
      "Cache-Control": "no-store, max-age=0",
      "X-Content-Type-Options": "nosniff",
    });
    if (resContentType) resHeaders.set("Content-Type", resContentType);

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
    const isTimeout = err instanceof Error && err.name === "AbortError";
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

import { NextResponse } from "next/server";
import { cookies, headers as requestHeaders } from "next/headers";
import { resolveApiConfig } from "@/lib/env";
import { trustedClientIpHeadersFromHeaders } from "@/lib/request-security";
import type {
  DashboardData,
  InfrastructureHealth,
  EventsStatus,
  Healthz,
  MemoryStatus,
  Readyz,
  RootInfo,
  SecurityStatus,
} from "@/lib/types";

const { apiUrl: API_URL, serviceApiKey: SERVICE_API_KEY } = resolveApiConfig();
const FETCH_TIMEOUT_MS = 3500;
const LOGS_URLS = ["/monitoring/logs"];

async function getJson<T>(
  path: string,
  sessionToken: string,
  clientHeaders: Record<string, string>,
): Promise<T | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const headers: Record<string, string> = {
      Accept: "application/json",
      Authorization: `Bearer ${sessionToken}`,
      ...clientHeaders,
    };
    if (SERVICE_API_KEY && process.env.NODE_ENV !== "production" && !sessionToken) {
      headers["X-API-Key"] = SERVICE_API_KEY;
    }
    const res = await fetch(`${API_URL}${path}`, {
      headers,
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function getLogs(
  sessionToken: string,
  clientHeaders: Record<string, string>,
): Promise<string[] | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2000);
  try {
    const headers: Record<string, string> = {
      Accept: "application/json",
      Authorization: `Bearer ${sessionToken}`,
      ...clientHeaders,
    };
    if (SERVICE_API_KEY && process.env.NODE_ENV !== "production" && !sessionToken) {
      headers["X-API-Key"] = SERVICE_API_KEY;
    }
    const res = await fetch(`${API_URL}${LOGS_URLS[0]}`, {
      headers,
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { lines?: string[] };
    return body.lines ?? null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export const dynamic = "force-dynamic";

export async function GET() {
  const sessionToken = (await cookies()).get("sophie_session")?.value;
  if (!sessionToken) {
    return NextResponse.json(
      { error: "unauthenticated" },
      { status: 401, headers: { "Cache-Control": "no-store, max-age=0" } },
    );
  }
  const incomingHeaders = await requestHeaders();
  const clientHeaders = trustedClientIpHeadersFromHeaders(incomingHeaders);
  const started = performance.now();
  const results: [
    RootInfo | null,
    Healthz | null,
    Readyz | null,
    InfrastructureHealth | null,
    MemoryStatus | null,
    EventsStatus | null,
    SecurityStatus | null,
    string[] | null,
  ] = await Promise.all([
    getJson<RootInfo>("/", sessionToken, clientHeaders),
    getJson<Healthz>("/healthz", sessionToken, clientHeaders),
    getJson<Readyz>("/readyz", sessionToken, clientHeaders),
    getJson<InfrastructureHealth>("/monitoring/health", sessionToken, clientHeaders),
    getJson<MemoryStatus>("/memory/status", sessionToken, clientHeaders),
    getJson<EventsStatus>("/events/status", sessionToken, clientHeaders),
    getJson<SecurityStatus>("/security/status", sessionToken, clientHeaders),
    getLogs(sessionToken, clientHeaders),
  ]);
  const [root, healthz, readyz, infrastructure, memory, events, security, logs] =
    results;
  const latency_ms = Math.round(performance.now() - started);

  const data: DashboardData = {
    fetched_at: Date.now(),
    backend_reachable: healthz !== null,
    latency_ms,
    root,
    healthz,
    readyz,
    infrastructure,
    memory,
    events,
    security,
    logs,
  };

  return NextResponse.json(data, {
    headers: {
      "Cache-Control": "no-store, max-age=0",
    },
  });
}

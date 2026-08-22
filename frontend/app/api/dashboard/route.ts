import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { resolveApiConfig } from "@/lib/env";
import type {
  DashboardData,
  DatabaseStatus,
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

async function getJson<T>(path: string): Promise<T | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    const sessionToken = (await cookies()).get("sophie_session")?.value;
    if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;
    else if (SERVICE_API_KEY && process.env.NODE_ENV !== "production") headers["X-API-Key"] = SERVICE_API_KEY;
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

async function getLogs(): Promise<string[] | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2000);
  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    const sessionToken = (await cookies()).get("sophie_session")?.value;
    if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;
    else if (SERVICE_API_KEY && process.env.NODE_ENV !== "production") headers["X-API-Key"] = SERVICE_API_KEY;
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
  const started = performance.now();
  const results: [
    RootInfo | null,
    Healthz | null,
    Readyz | null,
    DatabaseStatus | null,
    MemoryStatus | null,
    EventsStatus | null,
    SecurityStatus | null,
    string[] | null,
  ] = await Promise.all([
    getJson<RootInfo>("/"),
    getJson<Healthz>("/healthz"),
    getJson<Readyz>("/readyz"),
    getJson<DatabaseStatus>("/database/status"),
    getJson<MemoryStatus>("/memory/status"),
    getJson<EventsStatus>("/events/status"),
    getJson<SecurityStatus>("/security/status"),
    getLogs(),
  ]);
  const [root, healthz, readyz, database, memory, events, security, logs] =
    results;
  const latency_ms = Math.round(performance.now() - started);

  const data: DashboardData = {
    fetched_at: Date.now(),
    backend_reachable: healthz !== null,
    latency_ms,
    root,
    healthz,
    readyz,
    database,
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

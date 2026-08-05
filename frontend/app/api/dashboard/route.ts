import { NextResponse } from "next/server";
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

const API_URL = process.env.NEGAO_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEGAO_API_KEY ?? "negao-dev-api-key";
const FETCH_TIMEOUT_MS = 3500;
const LOGS_URLS = ["/monitoring/logs"];

async function getJson<T>(path: string): Promise<T | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { "X-API-Key": API_KEY, Accept: "application/json" },
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
    const res = await fetch(`${API_URL}${LOGS_URLS[0]}`, {
      headers: { "X-API-Key": API_KEY, Accept: "application/json" },
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

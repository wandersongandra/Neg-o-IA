export interface RootInfo {
  name: string;
  version: string;
  status: string;
  environment: string;
}

export interface Healthz {
  status: string;
}

export interface Readyz {
  status: string;
  checks: Record<string, string>;
}

export interface DatabaseStatus {
  connected: boolean;
  engine_url: string;
  active_connections: number;
  detail: string;
}

export interface MemoryStatus {
  redis_connected: boolean;
}

export interface EventsStatus {
  streams?: Record<string, unknown>;
  handlers?: unknown[];
  deliveries?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SecurityStatus {
  status: string;
  authenticated: boolean;
  authorization_level: string;
  authorization_level_id: number;
  principal: string;
}

export interface DashboardData {
  fetched_at: number;
  backend_reachable: boolean;
  latency_ms: number | null;
  root: RootInfo | null;
  healthz: Healthz | null;
  readyz: Readyz | null;
  database: DatabaseStatus | null;
  memory: MemoryStatus | null;
  events: EventsStatus | null;
  security: SecurityStatus | null;
  logs: string[] | null;
}

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

// --- Brain -------------------------------------------------------------------

export interface BrainStatus {
  mode: string;
  primary_model: string;
  fallback_model: string;
  cache_ttl_seconds: number;
  retry_attempts: number;
  circuit_failures: number;
}

export interface BrainRouterInfo {
  mode: string;
  primary_model: string;
  fallback_model: string;
  instance_router: boolean;
}

export interface BrainCompleteResponse {
  text: string;
  model: string;
  latency_ms: number;
  cached: boolean;
  fallback_used: boolean;
}

// --- Conversation ------------------------------------------------------------

export interface ConversationStatus {
  sessions: number;
  degraded: boolean;
}

export interface ConversationSession {
  session_id: string;
  user_id: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  name?: string;
}

export interface ConversationStoredMessage {
  role: string;
  content: string;
  created_at: string;
}

export interface ConversationMessageResponse {
  text: string;
  model: string;
  latency_ms: number;
  fallback_used: boolean;
}

// --- Voice -------------------------------------------------------------------

export interface VoiceStatus {
  stt_available: boolean;
  tts_available: boolean;
  stt_model: string;
  tts_voice: string;
}

// --- WebSocket / Chat --------------------------------------------------------

export interface WsInfo {
  api_key: string;
  ws_base: string | null;
}

export type WsServerMessage =
  | { type: "session"; session_id: string; created: boolean }
  | { type: "tokens"; delta: string }
  | {
      type: "done";
      text: string;
      model: string;
      latency_ms: number;
      fallback_used: boolean;
      session_id: string;
    }
  | { type: "error"; detail: string }
  | { type: "pong" };

export interface ChatViewMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "streaming" | "done" | "error";
  model?: string;
  latency_ms?: number;
  fallback_used?: boolean;
}

export interface RootInfo {
  name: string;
  version: string;
  status: "ready" | "not_ready" | string;
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

export interface VoiceStatus {
  stt_available: boolean;
  tts_available: boolean;
  stt_model: string;
  tts_voice: string;
  protocol_version?: number;
  audio_format?: string;
  limits?: {
    max_chunk_bytes: number;
    max_turn_bytes: number;
    max_turn_seconds: number;
  };
}

export type VoiceState =
  | "IDLE"
  | "CONNECTING"
  | "LISTENING"
  | "TRANSCRIBING"
  | "THINKING"
  | "SPEAKING"
  | "ERROR";

export interface AudioDevice {
  deviceId: string;
  groupId: string;
  label: string;
  kind: "audioinput" | "audiooutput";
}

export type VoiceServerMessage =
  | {
      type: "voice.session.started";
      version: 1;
      session_id: string;
    }
  | {
      type: "voice.state";
      version: 1;
      state: string;
      session_id: string | null;
      interaction_id: string | null;
    }
  | {
      type: "voice.transcript.final";
      version: 1;
      interaction_id: string;
      text: string;
    }
  | {
      type: "voice.response.started";
      version: 1;
      interaction_id: string;
    }
  | {
      type: "voice.response.text";
      version: 1;
      interaction_id: string;
      text: string;
    }
  | {
      type: "voice.response.audio";
      version: 1;
      interaction_id: string;
      format: string;
      bytes: number;
    }
  | {
      type: "voice.response.completed";
      version: 1;
      interaction_id: string;
    }
  | {
      type: "voice.session.stopped";
      version: 1;
      session_id: string | null;
    }
  | {
      type: "voice.error";
      version: 1;
      code: string;
      message: string;
      interaction_id: string | null;
    };

export interface WsInfo {
  ticket: string;
  ws_base: string | null;
  expires_in?: number;
  purpose?: "conversation" | "voice";
  session_id?: string | null;
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

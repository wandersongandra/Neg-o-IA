/**
 * Resolução de env vars do backend com compatibilidade SOPHIE_* / NEGAO_* —
 * SOPHIE_* tem precedência; se ausente, cai para NEGAO_* (comportamento
 * atual, sem mudanças em deploys existentes). Usado pelas rotas BFF
 * server-side (ws-info, dashboard, proxy) — nunca exposto ao cliente.
 */
function resolveEnv(newName: string, legacyName: string, fallback: string): string {
  return process.env[newName] ?? process.env[legacyName] ?? fallback;
}

export function resolveApiConfig(): {
  apiUrl: string;
  serviceApiKey: string;
  internalProxyKey: string;
} {
  return {
    apiUrl: resolveEnv("SOPHIE_API_URL", "NEGAO_API_URL", "http://localhost:8000"),
    serviceApiKey: resolveEnv("SOPHIE_SERVICE_API_KEY", "NEGAO_SERVICE_API_KEY", ""),
    internalProxyKey: resolveEnv(
      "SOPHIE_INTERNAL_PROXY_KEY",
      "NEGAO_INTERNAL_PROXY_KEY",
      "",
    ),
  };
}

export function resolvePublicOrigin(): string {
  return resolveEnv("SOPHIE_PUBLIC_ORIGIN", "NEGAO_PUBLIC_ORIGIN", "");
}

export function resolveWsUrl(): string {
  return resolveEnv("SOPHIE_WS_URL", "NEGAO_WS_URL", "");
}

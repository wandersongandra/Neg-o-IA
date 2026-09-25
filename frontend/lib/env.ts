import { readFileSync, statSync } from "node:fs";
import { isAbsolute } from "node:path";

/**
 * Resolução de env vars do backend com compatibilidade SOPHIE_* / NEGAO_* —
 * SOPHIE_* tem precedência; se ausente, cai para NEGAO_* (comportamento
 * atual, sem mudanças em deploys existentes). Usado pelas rotas BFF
 * server-side (ws-info, dashboard, proxy) — nunca exposto ao cliente.
 */
function resolveEnv(newName: string, legacyName: string, fallback: string): string {
  return process.env[newName] ?? process.env[legacyName] ?? fallback;
}

function resolveSecretEnv(newName: string, legacyName: string, fallback: string): string {
  const direct = process.env[newName] ?? process.env[legacyName];
  const fileName = `${newName}_FILE`;
  const legacyFileName = `${legacyName}_FILE`;
  const newFile = process.env[fileName]?.trim() ?? "";
  const legacyFile = process.env[legacyFileName]?.trim() ?? "";

  if (newFile && legacyFile && newFile !== legacyFile) {
    throw new Error(`${fileName} and ${legacyFileName} disagree`);
  }
  const file = newFile || legacyFile;
  if (!file) return direct ?? fallback;
  if (direct) {
    throw new Error(`${newName}: do not define both a direct secret and *_FILE`);
  }
  if (!isAbsolute(file)) {
    throw new Error(`${newName}_FILE must use an absolute path`);
  }

  const stat = statSync(file);
  if (!stat.isFile() || stat.size <= 0 || stat.size > 64 * 1024) {
    throw new Error(`${newName}_FILE points to an invalid secret file`);
  }
  const value = readFileSync(file, "utf8").trim();
  if (!value || value.includes("\0")) {
    throw new Error(`${newName}_FILE contains an empty or invalid secret`);
  }
  return value;
}

export function resolveApiConfig(): {
  apiUrl: string;
  serviceApiKey: string;
  internalProxyKey: string;
} {
  return {
    apiUrl: resolveEnv("SOPHIE_API_URL", "NEGAO_API_URL", "http://localhost:8000"),
    serviceApiKey: resolveSecretEnv(
      "SOPHIE_SERVICE_API_KEY",
      "NEGAO_SERVICE_API_KEY",
      "",
    ),
    internalProxyKey: resolveSecretEnv(
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

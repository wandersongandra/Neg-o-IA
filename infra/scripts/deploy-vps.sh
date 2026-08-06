#!/usr/bin/env bash
# deploy-vps.sh — Deploy do NEGÃO AI na VPS Ubuntu 26.04
# Requisitos na VPS: Docker + Docker Compose v2
# Uso: chmod +x deploy-vps.sh && ./deploy-vps.sh
set -euo pipefail

REPO="https://github.com/complianceX/Neg-o-IA.git"
WORKDIR="/opt/negao"
COMPOSE_FILE="infra/docker/compose/prod.yml"

echo "=== NEGÃO AI — Deploy VPS ==="

# --- Verifica Docker ---
if ! command -v docker &>/dev/null; then
    echo "[ERRO] Docker não instalado na VPS." >&2
    exit 1
fi
if ! docker compose version &>/dev/null; then
    echo "[ERRO] Docker Compose v2 não instalado na VPS." >&2
    exit 1
fi

# --- Clone ou pull do repo ---
if [ -d "$WORKDIR/.git" ]; then
    echo "[1/5] Atualizando código..."
    cd "$WORKDIR"
    git fetch --all --tags
    git reset --hard origin/main
else
    echo "[1/5] Clonando repositório..."
    git clone "$REPO" "$WORKDIR"
    cd "$WORKDIR"
fi

# --- .env ---
if [ ! -f "$WORKDIR/.env" ]; then
    echo "[2/5] Criando .env a partir de .env.example..."
    cp "$WORKDIR/.env.example" "$WORKDIR/.env"
    echo "  -> Ajuste $WORKDIR/.env com suas chaves e rode novamente."
    echo "  -> Especialmente: NEGAO_NVIDIA_API_KEY, NEGAO_SECRET_KEY, NEXT_PUBLIC_VAPID_PUBLIC_KEY"
    read -p "Continuar mesmo assim? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# --- Build ---
echo "[3/5] Building imagens..."
docker compose -f "$COMPOSE_FILE" build --pull

# --- Migrate ---
echo "[4/5] Migrações do banco..."
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head || {
    echo "[WARN] Migração falhou — continuando mesmo assim"
}

# --- Up ---
echo "[5/5] Subindo stack..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# --- Healthcheck ---
echo ""
echo "=== Aguardando healthcheck ==="
HEALTH_URL="http://localhost/healthz"
RETRIES="${NEGAO_HEALTH_RETRIES:-30}"
SLEEP="${NEGAO_HEALTH_SLEEP:-5}"

for i in $(seq 1 "$RETRIES"); do
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
        echo "✅ Deploy concluído! NEGÃO AI está online em http://$(hostname -I | awk '{print $1}')"
        docker compose -f "$COMPOSE_FILE" ps
        exit 0
    fi
    echo "  aguardando backend... (${i}/${RETRIES})"
    sleep "$SLEEP"
done

echo "[ERRO] Healthcheck falhou. Logs:" >&2
docker compose -f "$COMPOSE_FILE" logs --tail=50 backend || true
exit 1

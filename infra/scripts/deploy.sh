#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker/compose/prod.yml}"
HEALTH_URL="${NEGAO_HEALTH_URL:-http://localhost/healthz}"
RETRIES="${HEALTH_RETRIES:-30}"
SLEEP="${HEALTH_SLEEP:-5}"

if [ ! -f .env ]; then
    echo "ERRO: .env não encontrado. Copie .env.example para .env antes do deploy." >&2
    exit 1
fi

echo "[1/4] Build das imagens"
docker compose -f "$COMPOSE_FILE" build --pull

echo "[2/4] Migrações do banco"
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head

echo "[3/4] Subindo a stack"
docker compose -f "$COMPOSE_FILE" up -d

echo "[4/4] Healthcheck (até ${RETRIES}x, intervalo ${SLEEP}s)"
for i in $(seq 1 "$RETRIES"); do
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
        echo "Deploy concluído com sucesso."
        exit 0
    fi
    echo "  aguardando backend... (${i}/${RETRIES})"
    sleep "$SLEEP"
done

echo "ERRO: healthcheck falhou após ${RETRIES} tentativas." >&2
docker compose -f "$COMPOSE_FILE" logs --tail=100 backend || true
exit 1

# ROLLBACK (manual, descomente e ajuste a tag):
# docker compose -f "$COMPOSE_FILE" up -d --no-deps backend:<tag-anterior>

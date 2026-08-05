#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "Uso: restore.sh <arquivo.sql.gz>" >&2
    exit 1
fi

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker/compose/prod.yml}"
POSTGRES_USER="${POSTGRES_USER:-negao}"
POSTGRES_DB="${POSTGRES_DB:-negao}"

DB_CONTAINER="$(docker compose -f "$COMPOSE_FILE" ps -q db)"
if [ -z "$DB_CONTAINER" ]; then
    echo "ERRO: container do banco não está em execução." >&2
    exit 1
fi

read -r -p "Isso SUBSTITUI o banco '$POSTGRES_DB'. Continuar? [s/N] " CONFIRM
if [ "${CONFIRM:-n}" != "s" ]; then
    echo "Restauração cancelada."
    exit 1
fi

gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --set ON_ERROR_STOP=1

echo "Restauração concluída: $BACKUP_FILE"

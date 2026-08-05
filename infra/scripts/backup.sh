#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker/compose/prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
POSTGRES_USER="${POSTGRES_USER:-negao}"
POSTGRES_DB="${POSTGRES_DB:-negao}"

mkdir -p "$BACKUP_DIR"

DB_CONTAINER="$(docker compose -f "$COMPOSE_FILE" ps -q db)"
if [ -z "$DB_CONTAINER" ]; then
    echo "ERRO: container do banco não está em execução." >&2
    exit 1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/negao-$TIMESTAMP.sql.gz"

docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner | gzip > "$BACKUP_FILE"

find "$BACKUP_DIR" -name "negao-*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "Backup criado: $BACKUP_FILE"
echo "Rotação: mantendo backups dos últimos $RETENTION_DAYS dias em $BACKUP_DIR"

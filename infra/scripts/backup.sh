#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker/compose/prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
POSTGRES_USER="${POSTGRES_USER:-negao}"
POSTGRES_DB="${POSTGRES_DB:-negao}"
KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-}"

if [ -z "$KEY_FILE" ] || [ ! -r "$KEY_FILE" ]; then
    echo "ERRO: defina BACKUP_ENCRYPTION_KEY_FILE apontando para um arquivo legível (chmod 600)." >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

DB_CONTAINER="$(docker compose -f "$COMPOSE_FILE" ps -q db)"
if [ -z "$DB_CONTAINER" ]; then
    echo "ERRO: container do banco não está em execução." >&2
    exit 1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/sophie-$TIMESTAMP.sql.gz.enc"
TMP_FILE="$(mktemp "$BACKUP_DIR/.sophie-$TIMESTAMP.XXXXXX.sql.gz")"
trap 'rm -f "$TMP_FILE"' EXIT

docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner | gzip > "$TMP_FILE"
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000     -pass "file:$KEY_FILE" -in "$TMP_FILE" -out "$BACKUP_FILE"
sha256sum "$BACKUP_FILE" > "$BACKUP_FILE.sha256"
rm -f "$TMP_FILE"
trap - EXIT

find "$BACKUP_DIR" -name "sophie-*.sql.gz.enc" -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "sophie-*.sql.gz.enc.sha256" -mtime +"$RETENTION_DAYS" -delete

echo "Backup criptografado criado: $BACKUP_FILE"
echo "Checksum: $BACKUP_FILE.sha256"

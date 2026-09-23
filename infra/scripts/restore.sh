#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_FILE="${1:-}"
KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "Uso: restore.sh <arquivo.sql.gz.enc>" >&2
    exit 1
fi
if [ -z "$KEY_FILE" ] || [ ! -r "$KEY_FILE" ]; then
    echo "ERRO: defina BACKUP_ENCRYPTION_KEY_FILE apontando para a chave do backup." >&2
    exit 1
fi
if [ ! -f "$BACKUP_FILE.sha256" ]; then
    echo "ERRO: checksum ausente: $BACKUP_FILE.sha256" >&2
    exit 1
fi

sha256sum -c "$BACKUP_FILE.sha256"

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

openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000     -pass "file:$KEY_FILE" -in "$BACKUP_FILE"     | gunzip     | docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --set ON_ERROR_STOP=1

echo "Restauração concluída: $BACKUP_FILE"

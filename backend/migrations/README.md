# Migrações Alembic — Sophie AI

## Como rodar (local, a partir de `backend/`)

```bash
alembic -c migrations/alembic.ini upgrade head        # aplica todas
alembic -c migrations/alembic.ini downgrade base      # somente em dev
alembic -c migrations/alembic.ini revision -m "desc"  # gera uma migração
```

A URL é resolvida em `env.py` a partir de `NEGAO_DATABASE_URL`
(default: `postgresql+asyncpg://negao:negao@localhost:5432/negao`).

Em produção, via container:

```bash
docker compose -f infra/docker/compose/prod.yml exec backend \
  alembic -c migrations/alembic.ini upgrade head
```

## Esquema criado (0001 + 0002)

- Schemas: `identity`, `events`, `config`
- `identity.users`, `identity.api_keys` (hash SHA-256 da chave)
- `identity.devices`, `identity.sessions` (sessões opacas com hash, expiração e revogação)
- `events.audit_events` — **particionada** por RANGE mensal; um trigger
  (`events.create_partition_if_missing()`) cria partições novas automaticamente.
- `config.app_config` — pares key/value JSONB.
- Extensões: `vector` (pgvector, para a v1) e `pgcrypto` (gen_random_uuid).

## Testes de integração

Exigem um PostgreSQL real:

```bash
$env:NEGAO_TEST_DATABASE_URL="postgresql+asyncpg://negao:negao@localhost:5432/negao_test"
pytest -m integration
```

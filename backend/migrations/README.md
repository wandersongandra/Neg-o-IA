# Migrações Alembic — NEGÃO AI

## Como rodar (local, a partir de `backend/`)

```bash
alembic upgrade head        # aplica todas as migrações
alembic downgrade base      # desfaz tudo (para dev)
alembic revision -m "desc"  # gera nova migração (edite upgrade/downgrade)
```

A URL é resolvida em `env.py` a partir de `NEGAO_DATABASE_URL`
(default: `postgresql+asyncpg://negao:negao@localhost:5432/negao`).

Em produção, via container:

```bash
docker compose -f infra/docker/compose/prod.yml exec backend alembic upgrade head
```

## Esquema criado (0001)

- Schemas: `identity`, `events`, `config`
- `identity.users`, `identity.api_keys` (hash SHA-256 da chave)
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

# Migrações Alembic — Ultron / Neg-o-IA

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

## Esquema atual (0001–0011)

- Schemas: `identity`, `events`, `config`, `memory`, `knowledge`, `learning`, `automation`, `ai`
- `identity.users`, `identity.api_keys` (hash SHA-256 da chave)
- `identity.devices`, `identity.sessions` (sessões opacas com hash, expiração e revogação)
- `events.audit_events` — **particionada** por RANGE mensal. A migração 0001 cria a
  partição do mês da execução; a migração 0003 remove o DDL por trigger e adiciona uma
  partição `DEFAULT` para que eventos continuem sendo gravados sem partição mensal futura.
- `config.app_config` — pares key/value JSONB.
- `memory.entries` e `knowledge.documents/chunks` — dados e embeddings com isolamento por
  usuário. A migração 0008 vincula cada chunk ao par `(document_id, user_id)` do documento,
  impedindo que o banco aceite trechos atribuídos a outro proprietário.
- `automation.rules` — regras por usuário.
- `learning.experiences` — correções explícitas isoladas por usuário, usadas como contexto de recuperação.
- `ai.openai_plan_host` — identidade estável da instalação para SIWC.
- `ai.openai_plan_credentials` — tokens de plano ChatGPT cifrados em repouso e isolados por RLS.
- Extensões: `vector` (pgvector) e `pgcrypto` (`gen_random_uuid`).

## Migração 0008: integridade entre tenants

A migração valida os dados existentes antes de trocar a chave estrangeira dos chunks. Se
encontrar qualquer trecho cujo `user_id` difere do proprietário do documento, ela falha
com uma mensagem explícita e a transação é revertida; nenhum registro é reassociado
automaticamente. Corrija os dados identificados antes de reaplicar a migração.

## Migração 0010: RLS para memória e conhecimento

Ativa e força Row-Level Security em `memory.entries`, `knowledge.documents` e
`knowledge.chunks`; a conexão precisa definir `app.user_id` dentro da transação para
ler ou alterar registros do usuário correspondente.

## Migração 0011: credenciais SIWC

Cria a identidade de host persistente e a tabela de credenciais ChatGPT. As credenciais
são cifradas pelo backend com AES-256-GCM e uma chave dedicada externa ao banco. A tabela
força RLS por `app.user_id`. Não altere nem regenere essa chave sem um plano de
reautorização: credenciais cifradas com a chave antiga não podem ser lidas com uma nova.

## Testes de integração

Exigem um PostgreSQL real:

```bash
$env:NEGAO_TEST_DATABASE_URL="postgresql+asyncpg://negao:negao@localhost:5432/negao_test"
pytest -m integration
```

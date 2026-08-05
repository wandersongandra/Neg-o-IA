# NEGÃO AI

**Uma única inteligência.** O NEGÃO é uma IA pessoal com memória única, aprendizagem contínua e evolução constante — não uma coleção de agentes soltos. Todos os módulos são órgãos do mesmo cérebro, orquestrados pelo **Brain** e comunicando-se por eventos.

- **Visão de 10 anos:** `docs/ROADMAP.md`
- **Arquitetura de referência (17 módulos, Clean Architecture):** `docs/ARQUITETURA-CORE-MODULOS.md`

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Banco | PostgreSQL 17 + pgvector, Redis 7 (cache, sessão, streams) |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Observabilidade | OpenTelemetry, Prometheus, Grafana, Loki |
| Infra | Docker Compose (dev/prod), nginx, VPS Linux, K8s (futuro v5.0) |

## Estrutura do Monorepo

```
negao-ai/
├── backend/       # API + cérebro (FastAPI) — módulos em app/modules/
├── frontend/      # Dashboard (Next.js + Tailwind)
├── infra/         # Docker Compose, nginx, scripts de deploy/backup, k8s (futuro)
├── docs/          # Arquitetura, roadmap, contratos, ADRs
├── tests/         # Testes e2e (Playwright/Cypress + API)
├── Makefile       # Atalhos: make dev, make test, make deploy
└── .env.example   # Template de configuração (copie para .env)
```

## Como rodar (desenvolvimento)

Pré-requisitos: Docker + Docker Compose v2, Make (opcional — os comandos também rodam direto via `docker compose`).

```bash
cp .env.example .env   # configure as variáveis (segredos ficam fora do git)
make dev               # sobe db, redis, backend (hot reload) e frontend
```

- API: http://localhost:8000 (docs interativas em `/docs`)
- Frontend: http://localhost:3000
- Grafana: http://localhost:9091 (admin/admin) · Prometheus: http://localhost:9090

Outros alvos: `make dev-build`, `make stop`, `make prod`, `make logs`, `make test`, `make lint`, `make db-migrate m="mensagem"`, `make db-upgrade`, `make backup`, `make restore`.

## Fase atual

**v0.x — Fundação:** infraestrutura rodando e observável em produção, sem IA/LLM ainda. Núcleo vivo (conversa, memória, Model Router) na v1.0.

## Backup

`make backup` gera um dump compactado em `./backups/` (rotação de 7 dias). Restaure com `make restore backups/negao-YYYYMMDD-HHMMSS.sql.gz`. Teste de restauração mensal é obrigatório (critério da v0.x).

## Segurança

- Nunca commite `.env` — segredos ficam fora do repositório.
- Em produção, use HTTPS (TLS) e rode por dentro do nginx (porta 80/443).

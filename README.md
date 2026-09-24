# Sophie

Sophie is a personal AI assistant built as a secure modular monolith. The same conversation core now coordinates identity, conversation, long-term memory, semantic retrieval, planning, governed tools, event automations, voice and opt-in vision.

## Current architecture

- **Backend:** FastAPI, Python 3.13, SQLAlchemy, PostgreSQL 17 + pgvector and Redis.
- **Frontend:** Next.js 15, React 19 and Tailwind CSS.
- **Brain:** OpenAI-compatible NVIDIA endpoint with retry, circuit breaker and Redis cache.
- **Memory:** short-term Redis plus long-term PostgreSQL/pgvector, per-user retention policy and semantic recall.
- **Knowledge Vault:** chunking, local deterministic embeddings and pgvector retrieval.
- **Agent Core:** deterministic intent resolution, bounded plans and an allowlisted Tool Manager.
- **Automation:** persisted event rules that may call only tools explicitly marked automation-safe.
- **Scheduler:** persistent one-shot/recurring jobs claimed transactionally across replicas and restricted to automation-safe tools.
- **Learning:** explicit feedback stored through long-term memory; no autonomous prompt mutation or training.
- **Voice:** authenticated WebSocket voice sessions with NVIDIA STT and edge-tts synthesis.
- **Vision V1:** explicit authenticated PNG/JPEG/WebP uploads to a configured multimodal provider.
- **Operations:** Docker Compose, Nginx, Prometheus, Grafana and Loki.

## Safety model

Agent actions are fail-closed:

- Tool names come from a closed catalog.
- Read-only tools may execute automatically after intent resolution.
- Write tools require an explicit user action/confirmation.
- Automations may use only tools marked `automation_safe` and never confirmation-required writes.
- Retrieved memory/knowledge is injected as **untrusted data**, never as executable instructions.
- Vision is disabled by default and sends only images explicitly selected by the authenticated user.
- User data is namespaced by authenticated identity across conversations, memory, knowledge and automations.

## Development

Prerequisites:

- Docker and Docker Compose v2
- Git
- Python 3.13
- Node.js and npm

Create the local environment:

```bash
cp .env.example .env
make dev
```

Default endpoints:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs in non-production: `http://localhost:8000/docs`

Useful commands:

```bash
make test
make lint
make db-migrate
make db-upgrade
make logs
make stop
```

## Product workspaces

The frontend exposes authenticated workspaces for:

- Conversation
- Voice
- Long-term Memory
- Knowledge Vault
- Agent inspection (Reasoning / Planner / Tool catalog)
- Event Automations
- Persistent Scheduler
- Controlled Learning
- Vision
- Monitoring
- Configuration

## Compatibility

`SOPHIE_*` environment variables are accepted with precedence over legacy `NEGAO_*` names. Persistent database identifiers and deployment paths retain compatibility names until an explicit migration is scheduled.

## Repository layout

```text
backend/       FastAPI application, domain modules, tests and migrations
frontend/      Next.js BFF and UI workspaces
infra/         Docker, Nginx and deployment scripts
docs/          Architecture, compatibility and current-state references
```

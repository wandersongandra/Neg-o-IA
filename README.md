# Sophie

Sophie is a personal AI assistant with conversation, memory, knowledge, automation, voice and vision modules. The modules share one conversation core; voice and Bluetooth are input/output concerns, not a separate assistant.

## Architecture

- Backend: FastAPI, Python 3.13, SQLAlchemy, PostgreSQL and Redis.
- Frontend: Next.js 15, React 19 and Tailwind CSS.
- Integrations: NVIDIA APIs for model and speech services, `edge-tts` for synthesis, WebSockets for realtime sessions.
- Operations: Docker Compose, Nginx, Prometheus, Grafana and Loki.

The backend is organized by domain modules under `backend/app/modules`. The frontend uses the Next.js App Router under `frontend/app` and shared components under `frontend/components`.

## Development

Prerequisites:

- Docker and Docker Compose v2
- Git
- Python 3.13
- Node.js and npm

Create a local environment from the versioned template and review every value before starting the services:

```bash
cp .env.example .env
make dev
```

The default local endpoints are:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`

Useful commands:

```bash
make test
make lint
make db-migrate
make db-upgrade
make logs
make stop
```

Detailed validation procedures are documented in [TESTING_GUIDE.md](TESTING_GUIDE.md). Infrastructure notes are in [INFRASTRUCTURE_READY.md](INFRASTRUCTURE_READY.md) and [REDIS_CLOUD_CONFIG.md](REDIS_CLOUD_CONFIG.md).

## Voice

Voice V1 is exposed through `/ws/voice`. A session uses a short-lived, purpose-bound WebSocket ticket and keeps conversation context through the existing conversation service. Audio is held in memory for the active turn and is discarded after processing.

The browser can select independent input and output devices when supported. Bluetooth pairing remains managed by the operating system.

## Security and compatibility

User sessions are server-side. Service credentials are separate from user sessions. Secrets belong in ignored environment files or a secret manager.

The `NEGAO_*` environment variables, internal metric names, logger names, database identifiers and deployment paths are retained for compatibility. Optional `SOPHIE_*` aliases are documented in [docs/sophie/COMPATIBILITY.md](docs/sophie/COMPATIBILITY.md). Do not rename persistent identifiers without a migration plan.

## Repository layout

```text
backend/       FastAPI application and migrations
frontend/      Next.js application
infra/         Docker, Nginx and deployment scripts
docs/          Architecture and compatibility references
```

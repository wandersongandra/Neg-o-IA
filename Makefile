COMPOSE_DEV := docker compose -f infra/docker/compose/dev.yml
COMPOSE_PROD := docker compose -f infra/docker/compose/prod.yml
VENV_PY := backend/.venv/Scripts/python

.PHONY: dev dev-build stop prod logs test lint db-migrate db-upgrade backup restore

dev:
	$(COMPOSE_DEV) up

dev-build:
	$(COMPOSE_DEV) up --build

stop:
	$(COMPOSE_DEV) down
	$(COMPOSE_PROD) down

prod:
	$(COMPOSE_PROD) up -d --build

logs:
	$(COMPOSE_PROD) logs -f --tail=100

test:
	cd backend && .venv/Scripts/python -m pytest

lint:
	cd backend && .venv/Scripts/python -m ruff check .
	cd backend && .venv/Scripts/python -m mypy app

db-migrate:
	cd backend && .venv/Scripts/python -m alembic revision --autogenerate -m "$(m)"

db-upgrade:
	cd backend && .venv/Scripts/python -m alembic upgrade head

backup:
	bash infra/scripts/backup.sh

restore:
	bash infra/scripts/restore.sh

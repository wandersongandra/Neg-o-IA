# Kubernetes (futuro — v5.0)

Este diretório é um **placeholder**. A migração para Kubernetes está planejada
apenas na **v5.0 — Maturidade** (ver `docs/ROADMAP.md`), quando houver escala real
e necessidade de auto-scaling horizontal.

## Fase atual

- **v0.x → v4.0:** deploy via Docker Compose em VPS Linux (`infra/docker/compose/prod.yml`).
- **v5.0:** migração gradual Compose → Kubernetes (deploy canário, rollout/rollback automático).

## Decisões de arquitetura para a migração (v5.0)

- Os `deploy.resources` definidos nos compose files servem como referência inicial
  de requests/limits nos manifests (memory/cpu).
- O Event Bus (Redis Streams) é abstraído por contrato no `domain` — a troca por
  Kafka/RabbitMQ na migração não quebra produtores/consumidores.
- Volumes nomeados (`pgdata`, `redis-data`) mapearão para PersistentVolumeClaims.
- O nginx passa a ser Ingress Controller (ou Nginx Ingress oficial).

Nenhum manifest será criado antes da v5.0 — non-goal explícito das fases v0–v4.

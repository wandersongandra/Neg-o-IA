# SOPHIE — Current State

**Date:** 2026-09-24  
**Scope:** current implementation on the active Sophie codebase.

## Executive summary

Sophie has moved beyond the original prototype phase. The security foundation, identity/session model, backend hardening, long-term memory, Knowledge Vault, Reasoning, Planner, Tool Manager, event automations, voice and frontend workspaces are implemented and wired into the application.

The current evolution adds a governed Agent Core to the live conversation flow and Vision V1. The system remains intentionally conservative: arbitrary shell execution, unrestricted filesystem access, silent screen capture and unattended write tools are not enabled.

## Implemented modules

| Module | State |
|---|---|
| Identity / sessions | Production-oriented server-side sessions, revocation and ownership |
| Conversation | Working Redis-backed sessions, WebSocket and REST chat |
| Brain | Provider routing, retry, circuit breaker and cache |
| Short-term memory | Redis, isolated by user + session |
| Long-term memory | PostgreSQL + pgvector with retention policy |
| Knowledge Vault | Ingestion, chunking, embeddings and semantic retrieval |
| Reasoning | Deterministic intent resolution |
| Planner | Bounded plans with capped replanning |
| Tool Manager | Closed allowlist, timeout, circuit breaker, idempotency and confirmation gates |
| Automation | Persisted event rules restricted to automation-safe tools |
| Scheduler | Persistent one-shot/recurring jobs, transactional claim and safe-tool-only execution |
| Learning | Explicit feedback recorded via long-term memory; no autonomous model/prompt mutation |
| Voice | Authenticated WebSocket sessions, STT and TTS |
| Vision V1 | Explicit image analysis behind feature/provider gates |
| Monitoring / events | Metrics, durable audit/event flow and redacted logs |

## Agent flow

```text
authenticated user
      ↓
ConversationService
      ↓
semantic memory + knowledge retrieval
      ↓
ReasoningService
      ↓
PlannerService (when needed)
      ↓
ToolManager (allowlisted only)
      ↓
tool result injected as untrusted data
      ↓
BrainService
      ↓
assistant response
```

Read operations may be executed automatically. A write tool such as `memory.remember` requires an explicit user action. Automation rules cannot invoke confirmation-required tools.

## Memory and RAG

Long-term memory and Knowledge Vault use PostgreSQL + pgvector. The current embedding baseline is local deterministic feature hashing (384 dimensions), which means no memory/knowledge text is sent to a third-party embedding provider. It is intentionally simple and can later be replaced behind the same persistence contract.

Retrieved content is inserted into model context with a clear **untrusted-data boundary** so instructions inside stored documents are not treated as system instructions.

## Vision

Vision V1 accepts only explicit authenticated uploads:

- PNG
- JPEG
- WebP

Default maximum image size is 5 MiB. Vision is disabled unless both external AI and Vision are explicitly enabled and a multimodal model is configured.

No webcam activation, continuous surveillance or automatic screenshot capture is implemented.

## Security posture

The earlier shared-browser API-key exposure, unauthenticated database administration, unsafe production defaults, raw session metrics paths, weak branch workflow assumptions and secret-scanning gaps have been addressed in code/CI.

Current CI gates cover backend lint/format/typecheck/tests/migrations/dependency audit, frontend lint/build/typecheck/dependency audit, Nginx validation and Gitleaks history scanning.

One repository-level administrative item remains external to the codebase: GitHub branch protection for `main` must be enabled in repository settings if it is still disabled.

## Deliberately not implemented

The following are intentionally not granted to the agent by default:

- arbitrary shell / subprocess execution
- unrestricted local filesystem writes
- unattended destructive tools
- silent camera access
- silent desktop screenshots
- generic SSH control
- unrestricted e-mail/calendar actions

Scheduler and Learning are deliberately bounded: Scheduler cannot call write/confirmation-required tools, and Learning cannot silently rewrite the system prompt or fine-tune models.

Those capabilities should only be introduced as separately permissioned tools with scoped credentials, confirmation rules, idempotency and audit trails.

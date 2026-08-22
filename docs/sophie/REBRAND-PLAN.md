# SOPHIE — Phase 1 Rebrand Plan

## Strategy

Rename Layer A (user-facing) and Layer B (internal, non-persistent) now. Leave every Layer C/D identifier (env var names, DB user/schema, Docker/Compose project names, Redis consumer group, Prometheus/OTel names, structlog logger names, `/opt/negao`, package/registry names) untouched, with an additive `SOPHIE_*` env-var alias layer on top of the existing `NEGAO_*` names. No database migration, no repo/package/service rename, no CI change. Full detail and per-occurrence classification: `REBRAND-INVENTORY.md`.

## Identity centralization

**Backend**: new `backend/app/modules/brain/identity.py` holds the single source of truth for the assistant name and the system prompt text. `brain/router.py`'s `DEFAULT_CONFIG["system_prompt"]` and `conversation/application/__init__.py`'s `SYSTEM_PROMPT` both import from it instead of each hardcoding their own copy — this was already flagged in `CURRENT_STATE.md` as a "must be kept in sync manually" fragility; centralizing removes that risk entirely rather than just relabeling both copies.

**Frontend**: new `frontend/lib/brand.ts` (name/displayName/shortName/description) consumed by `layout.tsx` metadata and the PWA-adjacent surfaces. Component-level UI copy (chat header, voice panel labels, sidebar, etc.) is renamed as direct literal text — importing a shared constant into ~15 components for a name inside a sentence would be more churn than a safe rebrand calls for.

## Env var compatibility layer

Backend: a generic alias resolver in `settings.py`, run once before `Settings()` construction. For every `Settings` field, if `SOPHIE_<FIELD>` is set and `NEGAO_<FIELD>` is not, it copies the value across (`SOPHIE_*` wins, no functional change if only `NEGAO_*` is set — today's behavior is fully preserved). If any `NEGAO_*` var is in use, one dev/non-production-only log line lists which — never the values.

Frontend: new `frontend/lib/env.ts` with a `resolveApiConfig()` helper reused by the three BFF route files (`ws-info`, `dashboard`, `proxy`), same precedence.

## Ownership (no file touched by two owners)

| Owner | Scope |
|---|---|
| Orchestrator (this session) | `brain/identity.py` (new), `brain/router.py`, `conversation/application/__init__.py`, `configuration/settings.py`, `brain/infrastructure/__init__.py` (mock message), `voice/application/__init__.py` (error message), `frontend/lib/brand.ts` (new), `frontend/lib/env.ts` (new), `frontend/app/layout.tsx`, the 3 frontend BFF routes, `frontend/app/config/page.tsx`, `quick-start.sh`, `quick-start.bat`, `infra/scripts/deploy-vps.sh`, `infra/scripts/vps-setup.sh` (banner text only) |
| Agent 2 (backend) | Every other backend docstring/prose occurrence, `README.md`, `backend/pyproject.toml` description, `backend/migrations/README.md` title, `backend/tests/__init__.py`, `backend/tests/tests_unit/test_conversation.py` (fixture text only) |
| Agent 3 (frontend) | Every remaining frontend component: `conversa/page.tsx`, `voz/page.tsx`, `monitor/page.tsx`, `providers.tsx`, `top-bar.tsx`, `voice-panel.tsx`, `dashboard.tsx`, `sidebar.tsx`, `sections.tsx`, `panels.tsx`, `core-sphere.tsx`, `chat-panel.tsx` (copy only, not the WS logic from Phase 2), `avatar-core.tsx`, `typing-indicator.tsx`, `prompt-suggestions.tsx`, `pwa/install-prompt.tsx`, `public/manifest.json`, `public/offline.html` |
| Agent 4 (tests/regression, after 2 & 3 land) | New rebrand-specific tests (identity constant, env-alias precedence, legacy-string scan), re-run full backend + frontend gates |
| Agent 5 (security, after 4) | Re-verify route-auth-coverage, settings-security, rate-limit, ws-ticket/ws-info tests still pass; confirm no new public route, no secret exposed to frontend, no CORS/docs regression |

## Execution order

1. Inventory + this plan (done).
2. Orchestrator applies the cross-cutting/identity/compat files.
3. Agent 2 + Agent 3 run in parallel (disjoint file sets).
4. Orchestrator reviews both diffs, resolves anything unexpected.
5. Rebrand regression tests + full gates.
6. Legacy string scan + `COMPATIBILITY.md` + `PHASE-1-REPORT.md`.

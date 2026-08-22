# SOPHIE — Worklog

## Phase 2 — Security Hardening (complete)
See `CURRENT_STATE.md` §7 for findings addressed; all changes already committed to working tree (uncommitted, pending user review).

## Phase 1 — Safe Rebrand

AGENT: Orchestrator
TASK: Identity centralization + env-var compatibility layer + cross-cutting files
FILES: backend/app/modules/brain/identity.py (new), brain/router.py, conversation/application/__init__.py, configuration/settings.py, brain/infrastructure/__init__.py, voice/application/__init__.py, frontend/lib/brand.ts (new), frontend/lib/env.ts (new), frontend/app/layout.tsx, frontend/app/api/{ws-info,dashboard,proxy/[...path]}/route.ts, frontend/app/config/page.tsx, quick-start.sh, quick-start.bat, infra/scripts/{deploy-vps,vps-setup}.sh
CHANGES: SYSTEM_PROMPT/ASSISTANT_NAME centralized in brain/identity.py (was duplicated in 3 places); SOPHIE_* env alias resolver added to Settings (generic, all fields, precedence over NEGAO_*, dev-only log, never logs values); app_name default renamed; frontend BFF routes + layout metadata now use lib/brand.ts + lib/env.ts; config/page.tsx prompt+copy renamed; deploy/quick-start script banners renamed (env var names/paths untouched)
TESTS: backend ruff/mypy/pytest re-run clean (75 passed, 1 skip) after each backend edit; frontend tsc --noEmit clean
STATUS: done
BLOCKERS: none

AGENT: Agent 2 (backend docstrings/README)
TASK: Rename remaining Layer A/B backend prose per REBRAND-INVENTORY.md — docstrings, README.md, pyproject.toml description, migrations/README.md title, test fixture text. Explicitly must NOT touch: logger names (negao.*), env var names (NEGAO_*), default secret literals, DB connection string examples, package name in pyproject.toml, applied migration files.
FILES: see REBRAND-PLAN.md ownership table
START: dispatched
STATUS: dispatched
DEPENDENCIES: none (disjoint from Agent 3 and orchestrator's files)
BLOCKERS: none

AGENT: Agent 3 (frontend components)
TASK: Rename remaining Layer A UI copy + 2 localStorage keys per REBRAND-INVENTORY.md, across the frontend component files not already handled by the orchestrator.
FILES: see REBRAND-PLAN.md ownership table
START: dispatched
STATUS: dispatched
DEPENDENCIES: none (disjoint from Agent 2 and orchestrator's files)
BLOCKERS: none

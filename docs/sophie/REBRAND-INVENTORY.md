# SOPHIE — Rebrand Nomenclature Inventory (Phase 1)

Search: case-insensitive `neg[aã]o` across the whole repository (excludes `.git`, `node_modules`, `.venv`, `__pycache__`, `.next`), plus the specific compound identifiers named in the Phase 1 brief (`NEGAO_API_KEY`, `NEGAO_NVIDIA_API_KEY`, `NEGAO_AI`, etc. — all substrings of the base pattern, so already captured). No files were modified to produce this inventory.

Layers: **A** user-facing · **B** internal non-persistent · **C** external contract · **D** persistent/infra · **E** historical/documentation-only.

Actions: `RENAME_NOW` · `ADD_ALIAS` · `KEEP_LEGACY` · `MIGRATE_LATER` · `DOCUMENT_ONLY`.

## Backend — application code

| Occurrence | File | Line | Layer | Risk | Action |
|---|---|---:|---|---|---|
| Docstring "NEGÃO AI" | `backend/app/domain/__init__.py` | 1 | B | Low | RENAME_NOW |
| Docstring "NEGÃO AI" | `backend/app/infrastructure/__init__.py` | 1 | B | Low | RENAME_NOW |
| Docstring "NEGÃO AI" | `backend/app/domain/models.py` | 1 | B | Low | RENAME_NOW |
| Docstring "NEGÃO AI" | `backend/app/modules/api/websocket.py` | 1 | B | Low | RENAME_NOW |
| Docstring "NEGÃO AI" | `backend/app/modules/learning/__init__.py` | 1 | B | Low | RENAME_NOW |
| Docstring "NEGÃO AI" | `backend/app/modules/knowledge/__init__.py` | 1 | B | Low | RENAME_NOW |
| Docstring "NEGÃO AI" | `backend/app/modules/events/envelope.py` | 3, 21 | B | Low | RENAME_NOW |
| Docstring "NEGÃO AI" | `backend/app/modules/conversation/__init__.py` | 1 | B | Low | RENAME_NOW |
| Docstring "persona do NEGÃO" | `backend/app/modules/conversation/domain/__init__.py` | 4 | B | Low | RENAME_NOW |
| Event description "Resposta do NEGÃO persistida..." | `backend/app/modules/conversation/events.py` | 24 | B | Low | RENAME_NOW |
| Docstring "núcleo de inteligência único do NEGÃO AI" | `backend/app/modules/brain/domain/__init__.py` | 3 | B | Low | RENAME_NOW |
| Docstring "cérebro único do NEGÃO AI" | `backend/app/modules/brain/application/__init__.py` | 35 | B | Low | RENAME_NOW |
| Docstring "memória única do NEGÃO AI" | `backend/app/modules/memory/__init__.py` | 1 | B | Low | RENAME_NOW |
| Docstring "memória do NEGÃO AI" | `backend/app/modules/memory/application/__init__.py` | 25 | B | Low | RENAME_NOW |
| Docstring "métrica do NEGÃO AI" | `backend/app/modules/monitoring/domain/__init__.py` | 11 | B | Low | RENAME_NOW |
| Event description mentions `NEGAO_NVIDIA_API_KEY` | `backend/app/modules/voice/events.py` | 24 | B (text) / D (var name) | Low | RENAME_NOW (text only; keep var name) |
| `structlog.get_logger("negao.*")` (main, ws, brain, security, voice, conversation, telemetry, errors, access) | `backend/app/main.py`, `api/websocket.py`, `brain/router.py`, `security/router.py`, `voice/router.py`, `voice/application/__init__.py`, `conversation/router.py` | multiple | B/C | Medium — logger name may be used as a Loki/Grafana filter label | MIGRATE_LATER (documented, not renamed this phase) |
| System prompt "Você é o NEGÃO, assistente pessoal..." (live path) | `backend/app/modules/conversation/application/__init__.py` | 30 | A | High-value, low technical risk (prompt text, not a contract) | RENAME_NOW → centralize |
| `DEFAULT_CONFIG["system_prompt"]` duplicate | `backend/app/modules/brain/router.py` | 27 | A | Same | RENAME_NOW → centralize |
| Docstring "Configuração atual do agente NEGÃO" | `backend/app/modules/brain/router.py` | 162 | B | Low | RENAME_NOW |
| Mock adapter response text mentions `NEGAO_NVIDIA_API_KEY` | `backend/app/modules/brain/infrastructure/__init__.py` | 246 | A (text) / D (var name) | Low | RENAME_NOW (text only; keep var name, add alias mention) |
| Error message "defina NEGAO_NVIDIA_API_KEY" | `backend/app/modules/voice/application/__init__.py` | 53 | A (text) / D (var name) | Low | RENAME_NOW (text only; keep var name, add alias mention) |
| `_is_debug()` reads `NEGAO_DEBUG` | `backend/app/modules/memory/router.py:21`, `backend/app/modules/monitoring/router.py:24` | — | D | Breaks debug-gate if renamed without alias | KEEP_LEGACY |
| `_is_production()` reads `NEGAO_ENV` | `backend/app/modules/events/router.py` | 38 | D | Breaks prod-gate (fail-open risk already flagged in Phase 0) | KEEP_LEGACY |
| `env_prefix="NEGAO_"` | `backend/app/modules/configuration/settings.py` | 15 | D | Highest blast radius — every setting | KEEP_LEGACY + ADD_ALIAS (`SOPHIE_*`) |
| `app_name: str = "NEGÃO AI"` | `backend/app/modules/configuration/settings.py` | 19 | A | Low (default value, not the field name) | RENAME_NOW |
| Legacy development secret literals and inline database credentials | `backend/app/modules/configuration/settings.py` | 24, 25, 27 | D | Changing default secret *values* is a separate hardening concern, not branding | REDACTED_IN_DOCS / ROTATE_IF_REAL |
| `DEFAULT_GROUP = "negao-consumers"` (Redis Streams consumer group) | `backend/app/modules/events/infrastructure/__init__.py` | 24 | D | High — renaming drops in-flight/pending stream entries | KEEP_LEGACY |
| `negao_metrics` dict + Prometheus metric names (`negao_requests_total` etc.) + OTel service name `"negao-ai"` | `backend/app/modules/monitoring/infrastructure/__init__.py` | 17, 83, 93-107, 132, 141, 152-170 | D | High — breaks dashboards/alerts built on these names | KEEP_LEGACY (documented; explicitly deferred to metrics phase per Phase 1 brief) |
| `negao_metrics` import/usage | `backend/app/modules/monitoring/application/__init__.py` | 9, 38 | D | Same as above (internal reference to the dict, not user-facing) | KEEP_LEGACY |

## Backend — tests / migrations

| Occurrence | File | Line | Layer | Risk | Action |
|---|---|---:|---|---|---|
| Docstring "Testes do NEGÃO AI" | `backend/tests/__init__.py` | 1 | E | None | RENAME_NOW (trivial) |
| `NEGAO_ENV`, `NEGAO_API_KEY` env fixtures | `backend/tests/conftest.py` | 41-42 | D (must match real var) | Breaks tests if changed without matching Settings | KEEP_LEGACY |
| Test fixture with a legacy development API key (`[REDACTED_LEGACY_DEV_KEY]`) + env fixture | `backend/tests/tests_e2e/test_api_smoke.py` | 15, 22-23 | D | Test-only compatibility value; never use in deploys | KEEP_TEST_ONLY |
| "Resposta do NEGÃO" fixture text, legacy development query key (`[REDACTED_LEGACY_DEV_KEY]`) | `backend/tests/tests_unit/test_conversation.py` | 124, 155, 224 | B/D | Fixture text safe to rename; query value is test-only compatibility | RENAME_TEXT / KEEP_TEST_ONLY |
| `NEGAO_TEST_DATABASE_URL` references | `backend/tests/tests_integration/test_database_live.py` | 3-4, 29, 35 | D | Breaks the opt-in live-DB test | KEEP_LEGACY |
| `assert "NEGAO_NVIDIA_API_KEY" in response.text` | `backend/tests/tests_unit/test_brain.py` | 162 | D (asserts on the var name in a message) | Breaks test if var renamed without updating assertion together | KEEP_LEGACY (update only if the message text itself changes) |
| `match="NEGAO_NVIDIA_API_KEY"` | `backend/tests/tests_unit/test_voice.py` | 109 | D | Same | KEEP_LEGACY |
| `alembic.ini` comment, `env.py` docstring reference `NEGAO_DATABASE_URL` | `backend/migrations/alembic.ini:4`, `backend/migrations/env.py:1` | — | D | Breaks migration tooling docs if misleading | KEEP_LEGACY (comment only, no functional change) |
| `backend/migrations/README.md` title + connection string examples | `backend/migrations/README.md` | 1, 11-12, 34 | A (title) / D (examples) | Low | RENAME_NOW (title only) / DOCUMENT_ONLY (examples, real var names) |
| `backend/migrations/versions/0001_initial_schema.py` docstring "fundação do banco NEGÃO AI" | — | 1 | E | An **applied migration** — never edit | DOCUMENT_ONLY |
| `pyproject.toml` package name `negao-ai-backend` | `backend/pyproject.toml` | 6 | D | Package/registry identity — explicitly out of scope this phase (§46) | KEEP_LEGACY |
| `pyproject.toml` description "NEGÃO AI - Fundação..." | `backend/pyproject.toml` | 8 | A | Low | RENAME_NOW |

## Frontend

| Occurrence | File | Line | Layer | Risk | Action |
|---|---|---:|---|---|---|
| Page title/meta "NEGÃO AI — Centro de Comando" | `frontend/app/layout.tsx` | 20-45 | A | Low | RENAME_NOW → centralize via `lib/brand.ts` |
| Page titles/copy | `frontend/app/conversa/page.tsx:6-19`, `frontend/app/voz/page.tsx:6-27`, `frontend/app/monitor/page.tsx:735`, `frontend/app/config/page.tsx:202,242,319,326` | — | A | Low | RENAME_NOW |
| System prompt default (frontend copy) | `frontend/app/config/page.tsx` | 8 | A | Low (UI fallback default, not a contract) | RENAME_NOW |
| `process.env.NEGAO_API_URL/API_KEY/WS_URL` | `frontend/app/api/ws-info/route.ts:6-8`, `frontend/app/api/dashboard/route.ts:13-14`, `frontend/app/api/proxy/[...path]/route.ts:5-6` | — | D | Breaks the BFF if renamed without matching deploy env | KEEP_LEGACY + ADD_ALIAS (`SOPHIE_API_URL/API_KEY/WS_URL`) via shared `lib/env.ts` |
| UI copy across components (headings, buttons, placeholders, aria-labels) | `providers.tsx` (localStorage key only), `top-bar.tsx`, `voice-panel.tsx`, `dashboard.tsx`, `sidebar.tsx`, `sections.tsx`, `panels.tsx`, `core-sphere.tsx`, `chat-panel.tsx`, `avatar-core.tsx`, `typing-indicator.tsx`, `prompt-suggestions.tsx` | see below | A | Low | RENAME_NOW |
| `localStorage` keys `negao-theme`, `negao-install-dismissed` | `providers.tsx:10`, `top-bar.tsx:59,69,81`, `pwa/install-prompt.tsx:30,68` | — | B (client-only, non-persistent across deploys) | Trivial — one-time reset of a user's saved theme/dismissed-install flag, no data loss | RENAME_NOW (documented as accepted minor reset) |
| PWA install copy | `pwa/install-prompt.tsx:82,108,184` | — | A | Low | RENAME_NOW |
| `manifest.json` name/short_name/description + shortcut descriptions | `frontend/public/manifest.json` | 2-4, 66, 79, 92 | A | Low, but existing installed-PWA icons keep the old label until reinstalled/cache-busted | RENAME_NOW (documented caveat) |
| `offline.html` title | `frontend/public/offline.html` | 6 | A | Low | RENAME_NOW |
| `package.json` name `negao-frontend` | `frontend/package.json` | 2 | D | Package registry identity — explicitly out of scope (§46) | KEEP_LEGACY |
| `.vercel/project.json` `name`/`projectName` `negao-frontend` | `frontend/.vercel/project.json` | 4 | D | Deployment project pointer — explicitly out of scope (§46) | KEEP_LEGACY |

## Infra / deploy scripts

| Occurrence | File | Line | Layer | Risk | Action |
|---|---|---:|---|---|---|
| Compose project names `negao`, `negao-prod`, `negao-observability` | `infra/docker/compose/{dev,prod,observability}.yml` | 1 | D | Container/network name prefixes | KEEP_LEGACY (§46-49) |
| `POSTGRES_USER/PASSWORD/DB` defaults `negao` | `infra/docker/compose/{dev,prod}.yml` | 7-9 | D | Live DB credential identity | KEEP_LEGACY (§47) |
| `NEGAO_ENV`, `NEGAO_API_URL`, `NEGAO_API_KEY` service env | `infra/docker/compose/{dev,prod}.yml` | 42/50, 59/68, 60/69 | D | Container startup config | KEEP_LEGACY |
| nginx config filename `negao.conf` | `infra/nginx/conf.d/negao.conf` | — | D | Referenced by nginx's `include conf.d/*.conf` glob (safe to rename technically, but a deploy/infra identifier) | KEEP_LEGACY (§46) |
| Backup filename prefix, `POSTGRES_USER/DB` defaults | `infra/scripts/backup.sh:9-10,21,25`, `infra/scripts/restore.sh:13-14` | — | D | Prune/restore correctness depends on consistency | KEEP_LEGACY |
| `NEGAO_HEALTH_URL/RETRIES/SLEEP` | `infra/scripts/deploy.sh:7`, `infra/scripts/deploy-vps.sh:66-67` | — | D | Deploy tooling config | KEEP_LEGACY |
| `/opt/negao` VPS deploy path | `infra/scripts/deploy-vps.sh:8`, `infra/scripts/vps-setup.sh:25,39` | — | D | Live server directory — renaming needs a migration step, not a code edit | KEEP_LEGACY (§46-49) |
| Console banner text "NEGÃO AI — Deploy VPS" etc. | `infra/scripts/deploy-vps.sh:2,11,71`, `infra/scripts/vps-setup.sh:6` | — | A | Cosmetic echo output only | RENAME_NOW (banner text only, paths/vars untouched) |
| `quick-start.sh`/`quick-start.bat` banner text | `quick-start.sh:3,9,181,191`, `quick-start.bat:2,8,129` | — | A | Cosmetic echo output only | RENAME_NOW (banner text only; `NEGAO_API_URL/API_KEY` refs and `pg_isready -U negao` at `quick-start.sh:88` untouched) |
| `.env.example` — all `NEGAO_*` variable names + `NEGAO_APP_NAME=negao-ai` value | `.env.example` (whole file) | — | D | Deploy template — must stay in lockstep with `Settings` | KEEP_LEGACY + document the new optional `SOPHIE_*` aliases |

## Documentation (Layer E — document only, no edits this phase except README)

`docs/ARQUITETURA.md`, `docs/ARQUITETURA-CORE-MODULOS.md`, `docs/ARQUITETURA-MEMORIA-APRENDIZADO-KNOWLEDGE.md`, `docs/README-ARQUITETURA.md`, `docs/ROADMAP.md`, and the 14 root-level `.md`/`.txt` snapshot files (`COMPLETION_SUMMARY.txt`, `DESIGN_AUDIT_REPORT.md`, `GO_GO_GO.md`, `IMPLEMENTATION_ROADMAP.md`, `INFRASTRUCTURE_READY.md`, `INTEGRATION_README.md`, `PROGRESS_REPORT.md`, `REDIS_CLOUD_CONFIG.md`, `SETUP_STATUS.md`, `START_HERE.md`, `SUMMARY.txt`, `TESTING_GUIDE.md`, `API_INTEGRATION_GUIDE.md`) already flagged in `docs/sophie/CURRENT_STATE.md` §9/§4 as duplicative work-session snapshots. Left untouched — a full rewrite of ~15 narrative documents is out of proportion to a "safe rebrand" and was already recommended for consolidation/removal independent of branding. `README.md` is the one exception: it's the living, primary entry point (explicitly listed as in-scope in §3 of the Phase 1 brief), so it gets a full literal `NEGÃO`→`Sophie` text pass (no restructuring, no content rewrite).

## Summary

- **RENAME_NOW** (this phase): ~120 occurrences — backend docstrings/log-adjacent prose, the two backend + one frontend copy of the system prompt (now centralized to one backend source), `app_name`/`pyproject.toml` description defaults, all frontend UI copy, `manifest.json`, `offline.html`, two `localStorage` keys, script banner text, `README.md`.
- **ADD_ALIAS**: `SOPHIE_*` env vars (generic, all `Settings` fields) on the backend; `SOPHIE_API_URL`/`SOPHIE_API_KEY`/`SOPHIE_WS_URL` on the frontend BFF routes — both with `SOPHIE_*` taking precedence and falling back to `NEGAO_*`, dev-only deprecation log, never logging values.
- **KEEP_LEGACY / MIGRATE_LATER**: everything Layer D (env var *names*, DB user/schema, Docker/Compose project names, Redis consumer group, Prometheus/OTel identifiers, structlog logger names, `/opt/negao` VPS path, package/registry names, `.vercel` project pointer) plus the applied migration file. None of these are touched this phase.
- **DOCUMENT_ONLY**: architecture docs, root snapshot files, default-secret literal values (a hardening concern, not branding).

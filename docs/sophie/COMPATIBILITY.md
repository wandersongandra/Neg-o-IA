# SOPHIE — Compatibility Reference (Phase 1)

What changed identity-wise, what didn't, and how the two coexist. Full per-occurrence detail: `REBRAND-INVENTORY.md`.

## Legacy ↔ new identifier map

| Legacy | New | Status | Removal |
|---|---|---|---|
| "NEGÃO AI" / "NEGÃO" (all user-facing text, UI copy, prompts, README, PWA manifest) | "Sophie AI" / "Sophie" | migrated | complete |
| `NEGAO_*` env var prefix (all `Settings` fields) | `SOPHIE_*` (optional) | alias — `SOPHIE_*` takes precedence, `NEGAO_*` still fully functional | future major (no forced date; remove only once all deploys have migrated) |
| `NEGAO_API_URL` / `NEGAO_API_KEY` / `NEGAO_WS_URL` (frontend BFF) | `SOPHIE_API_URL` / `SOPHIE_API_KEY` / `SOPHIE_WS_URL` (optional) | alias, same precedence rule, via `frontend/lib/env.ts` | future major |
| `localStorage["negao-theme"]` | `localStorage["sophie-theme"]` | migrated (one-time reset of saved theme for existing users — no data loss, just falls back to default once) | complete |
| `localStorage["negao-install-dismissed"]` | `localStorage["sophie-install-dismissed"]` | migrated (same one-time reset caveat) | complete |
| `app_name` default `"NEGÃO AI"` | `"Sophie AI"` | migrated (still overridable via env, no contract change — the field name is unchanged) | complete |
| Duplicated system-prompt text (3 independent copies) | Centralized in `backend/app/modules/brain/identity.py` (`SYSTEM_PROMPT`, `ASSISTANT_NAME`) | migrated — backend now has one source; frontend `config/page.tsx` keeps a manually-synced copy since it can't import Python | complete (backend); documented duplication (frontend) |
| structlog logger names (`negao.main`, `negao.ws`, `negao.brain`, `negao.security`, `negao.voice`, `negao.conversation`, `negao.errors`, `negao.access`, `negao.telemetry`) | — | **kept as-is** | deferred — see below |
| Prometheus metric names (`negao_requests_total`, `negao_request_duration_seconds`, `negao_active_connections`, `negao_events_published_total`), OTel service name (`negao-ai`) | — | **kept as-is** | deferred — explicitly out of scope this phase, bundled with the metrics-instrumentation work already deferred from Phase 2 |
| Redis Streams consumer group `negao-consumers` | — | **kept as-is** | deferred — renaming drops in-flight/pending stream entries, needs a dedicated migration, not a branding edit |
| `NEGAO_DEBUG`, `NEGAO_ENV` (raw `os.getenv` fallback reads in `memory/router.py`, `monitoring/router.py`, `events/router.py`) | — | **kept as-is** (still covered by the generic `SOPHIE_*` alias since `_apply_legacy_env_aliases` copies `SOPHIE_ENV`/`SOPHIE_DEBUG` into `NEGAO_ENV`/`NEGAO_DEBUG` before these reads happen) | n/a |
| Postgres user/db `negao`, Docker Compose project names (`negao`, `negao-prod`, `negao-observability`), `/opt/negao` VPS path, nginx conf filename `negao.conf`, GitHub repo URL, `package.json`/`pyproject.toml` package names, `.vercel/project.json` | — | **kept as-is** | out of scope for Phase 1 entirely (repo/package/infra rename needs its own plan, per the Phase 1 brief §46-49) |
| Legacy development secret literals and inline database credentials | — | **redacted in documentation** | this is a hardening concern (rotate any real credentials), not branding — see `CURRENT_STATE.md` §8 |

## Env var alias mechanism (how it actually works)

`backend/app/modules/configuration/settings.py::_apply_legacy_env_aliases()` runs once per `get_settings()` cache miss, before `Settings()` is constructed. For every field on `Settings` (generic — not hardcoded to a specific list), it checks `SOPHIE_<FIELD>`:

- If set, it **overwrites** `NEGAO_<FIELD>` in `os.environ` with that value (SOPHIE_* always wins, even if NEGAO_* is also set).
- If not set but `NEGAO_<FIELD>` is, nothing changes — today's behavior is fully preserved.
- If any `NEGAO_*` var is in use and the effective environment isn't `production`, one log line (via stdlib `logging`, logger `sophie.config`) lists which var *names* are legacy — never values.

The frontend mirrors this with `frontend/lib/env.ts::resolveApiConfig()`/`resolveWsUrl()`, used by all three BFF route files (`ws-info`, `dashboard`, `proxy`).

**Known limitation**: the backend alias writes into the real process `os.environ` (not a copy), so it isn't automatically undone. This is intentional and harmless for a real server process (config is resolved once at startup), but means a test that sets `SOPHIE_*` env vars via `monkeypatch` should also explicitly clean up the derived `NEGAO_*` var afterward, since `monkeypatch` only reverts variables it set directly. `test_env_aliases.py` documents and works around this.

## What did NOT change

Per the Phase 1 brief's explicit stop-list: no database migration, no table/column rename, no Docker/Compose project rename, no repo/package/registry rename, no VPS path change, no CI change, no metrics/logger identifier change, no security regression (all Phase 2 gates re-verified — see `PHASE-1-REPORT.md`).

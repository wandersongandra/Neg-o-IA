# SOPHIE — Current State Report (Phase 0 Discovery)

**Date:** 2026-08-20
**Scope:** Read-only audit of the existing "NEGÃO AI" system prior to the SOPHIE rebrand/evolution initiative. No files were modified to produce this report.
**Method:** 5 parallel read-only agents (Architecture, AI Brain/Memory, Interfaces/Voice, Platform/Tools/Permissions, Security/QA) audited the codebase independently. Findings below are merged and cross-referenced; every claim carries file:line evidence from the source agent reports (kept in this session's transcript).

---

## 0. Executive summary

NEGÃO AI is a real, partially-working v0 prototype: FastAPI modular-monolith backend (`backend/app/modules/*`) + Next.js 15 frontend, Redis + Postgres/pgvector, deployed via Docker Compose to a VPS. Of the 18 documented backend modules, **9 are functional and wired into the app; 9 are pure unmounted scaffolding** (knowledge, learning, planner, reasoning, scheduler, tool_manager, vision, automation — plus `tool_manager` explicitly documented as the future permission/sandbox layer). The chat + voice-transcription + voice-synthesis + memory(short-term) + monitoring pipeline works end-to-end. Vision, long-term/vector memory, tool-calling, and any permission engine do not exist yet despite being extensively designed in `docs/ARQUITETURA*.md`.

**The system is not production-safe today.** Security audit found two BLOCKER-severity issues (the shared API key is served to every browser visitor; a key-minting endpoint has no auth) plus a live credential leak in git-tracked files (Redis Cloud password, Supabase password). These are independent of the SOPHIE rebrand and should be remediated regardless of what phase is chosen next — **recommend rotating `NEGAO_API_KEY`, `NEGAO_NVIDIA_API_KEY`, the Redis Cloud password, and the Supabase password now.**

The "NEGÃO" rebrand surface spans 101 files. Most is low-risk UI copy and docstrings, but the `NEGAO_` env-var prefix, three hardcoded copies of the AI persona system prompt, Prometheus metric names, the Redis consumer-group name, and the `/opt/negao` VPS deploy path are all high-blast-radius renames that need a migration/compat step, not a find-replace.

---

## 1. Real request flow (observed, not assumed)

```
USER
 → FRONTEND (Next.js App Router, frontend/app/*)
 → BFF PROXY (frontend/app/api/proxy/[...path]/route.ts)
     - hardcoded {path, method} allowlist; injects X-API-Key server-side
     - separate, duplicated env-reading logic also in api/dashboard/route.ts and api/ws-info/route.ts
 → BACKEND (backend/app/main.py, FastAPI create_app())
     - middleware: rate_limit → CORS → request_context → access_log
 → MODULE ROUTER (9 mounted: api, security, database, events, monitoring, memory, brain, voice, conversation)
     - Depends(require_api_key) applied per-route, opt-in, NOT global (11 of ~20 endpoints have no auth at all)
 → application layer → infrastructure layer → Postgres / Redis / NVIDIA NIM (external)
```

The frontend proxy's route allowlist and the backend's actually-mounted routes are two independently maintained lists that have already drifted (e.g. stub modules aren't in either; `/database`/`/monitoring` shapes differ between the two).

---

## 2. Module inventory

| Module | Wired in `main.py`? | State |
|---|---|---|
| api, brain, conversation, memory, voice, security, monitoring, events, database | Yes | Functional (sizes vary; `brain` is largest at ~400 lines infra) |
| configuration | N/A (imported directly) | Functional (pydantic-settings, `env_prefix="NEGAO_"`) |
| automation, knowledge, learning, planner, reasoning, scheduler, tool_manager, vision | **No** | **Pure stub** — router has zero routes, application/domain/infra files are docstring-only ("esqueleto de contrato... v1+") |

`tool_manager` is the most consequential stub: it's the designed home for AI tool-calling + the permission/sandbox gate described extensively in `docs/ARQUITETURA.md` (~90 lines of spec, 14 named plugins) — none of it is built. There is currently **no way for the AI to call a tool at all**, and no sandbox exists because there's no execution capability to isolate yet.

---

## 3. Documentation vs. code drift

`docs/ARQUITETURA*.md` and `docs/ROADMAP.md` are explicitly design-only documents ("Escopo: design," no implementation claimed) — they are not stale in the sense of being wrong, but the codebase has diverged from them in specific, checkable ways:

- Docs specify `backend/app/core/brain/` as the orchestrator home; code puts all brain logic under `backend/app/modules/brain/` instead — `app/core/` only has `context.py`/`di.py`.
- Docs describe a 3-tier memory system (STM Redis / LTM Postgres / vector pgvector + BGE-M3 embeddings + reranking); code has **only** the STM Redis tier. `CREATE EXTENSION vector` is provisioned in the one existing migration but no memory tables exist.
- Docs specify JWT+OAuth2+MFA+4-level authorization; code has single-shared-API-key auth with one flat `READ_ONLY` authorization level. `ApiKeyRecord.scopes`, `UserRecord`, `AuditEventRecord` exist as unused stub models for the richer system.
- Docs specify a standalone pluggable Model Router with driver pattern + cost tracking + `model_catalog` table; code has a single NVIDIA-NIM-only router collapsed into `brain/infrastructure/__init__.py`, with primary and "fallback" models both served by the same vendor/endpoint (not true vendor diversity).

---

## 4. AI Brain / Memory / Multimodal

- **Model provider**: NVIDIA NIM only (OpenAI-compatible shape), models `deepseek-ai/deepseek-v4-flash` (primary) / `meta/llama-3.1-8b-instruct` (fallback) — both through the same `nvidia_base_url`, so a full NVIDIA outage takes down both. HTTP 529 (NVIDIA overload) is correctly treated as retryable, alongside 429/500/502/503/504.
- **Resilience controls are implemented**: per-provider `CircuitBreaker` + `RetryPolicy` with exponential backoff + Redis response caching all implemented in `brain/infrastructure/__init__.py`. However the fallback path reimplements ~45 lines of near-identical NVIDIA-specific HTTP logic instead of reusing the `LLMAdapter` Protocol abstraction that already exists in `brain/domain/__init__.py` — adding a second real vendor means rewriting this method, not registering a new adapter.
- **Persona/system prompt is hardcoded in three separate places** that must be kept in sync manually: `brain/router.py` (admin-config default), `conversation/application/__init__.py` (the one actually used in every live chat turn), and `frontend/app/config/page.tsx` (frontend fallback default). All three currently say: *"Você é o NEGÃO, assistente pessoal de inteligência artificial do Wanderson... Trate o usuário como 'chefe'..."* — this bakes in both the product name and a specific person's name/relationship framing.
- **Memory**: only Redis short-term memory (24h TTL, key `stm:{session_id}:{key}`) exists. `memory` module is explicitly labeled v0/STM-only in its own docstring. `knowledge`/`learning` modules (long-term/RAG) are unmounted stubs.
- **Voice works standalone but is not connected to Brain.** `/voice/transcribe` and `/voice/synthesize` are real, working REST endpoints (NVIDIA Parakeet STT + Microsoft edge-tts). But no code path forwards a transcript into `ConversationService`/`BrainService` — the frontend transcribes client-side and then sends the *text* into chat separately. The backend's `/ws/voice` streaming endpoint exists but nothing in the frontend connects to it (dead code). Event-catalog entries suggesting voice↔brain integration (`voice.asr.completed` etc.) have no actual subscriber code and don't even use consistent names between the two modules' catalogs.
- **Vision module is a pure unmounted stub** — no image/camera capability exists anywhere in the running system today.

---

## 5. Interfaces / UX / Voice (frontend)

- Next.js App Router, no global state library — two React Contexts (avatar state, toasts) plus local component state and polling (no SWR/React Query).
- **Markdown XSS fix verified as real and sound**: hand-rolled renderer never uses `dangerouslySetInnerHTML`; link protocol is validated (only https/mailto render as links). No regression found.
- **WebSocket reconnection is solid**: exponential-ish backoff, heartbeat ping, clean teardown — not a stub.
- **Two disconnected voice UIs** (`voice-panel.tsx`, `chat-panel.tsx`'s mic button) both use plain REST against `/voice/transcribe`/`/voice/synthesize`; neither uses the backend's `/ws/voice` streaming endpoint, which is fully implemented but orphaned.
- **No wake-word, no barge-in** anywhere in the codebase — confirmed via grep. Voice interaction is 100% push-to-talk today.
- **The Config page's model dropdown lists model IDs that don't match what the backend actually runs** (`openai/gpt-oss-120b` in the UI vs. `nvidia/gpt-oss-120b`-style names in settings) — a real, live drift between frontend and backend config surfaces.
- **Hardcoded personalization**: the top bar shows a literal `"Wanderson"` name and "W" avatar initial, not sourced from any session/identity — will need to become dynamic or renamed.
- Several dashboard "chips" (memory %, learning level, confidence) show static fake numbers, not real telemetry.
- **Live bug**: commit `a176148` intended to gitignore `sw.js`/`workbox-*.js` but produced a malformed single-line `.gitignore` entry that does neither, and destroyed the prior `.vercel` ignore rule in the process. Still present in `frontend/.gitignore` today.
- PWA `manifest.json`, `offline.html`, and the install-prompt component are directly "NEGÃO AI" branded; icon *asset filenames* are generic and don't need renaming, only their visual content (not inspected).

---

## 6. Platform / Tools / Permissions / Sandbox

- **No AI-callable tool system exists.** `tool_manager` is a deliberately unimplemented "v0 skeleton," not mounted in `main.py`. A `tools_enabled` list exists in `brain/router.py`'s persisted agent config but nothing reads it to gate or dispatch anything — it's inert configuration data.
- **No sandbox exists** — and there's currently nothing that would need one: no `subprocess`/`eval`/`exec`/shell-execution capability was found anywhere in the backend.
- **Auth = single shared API key → one flat `READ_ONLY` authorization level.** `ApiKeyRecord.scopes`, `UserRecord`, `AuditEventRecord` are unused stub models for a richer, unbuilt permission system.
- **Event bus (Redis Streams) is real and working** — dedup, DLQ, consumer groups — used today mainly for best-effort security-audit signals, not persisted durable audit storage.
- `.env` is correctly gitignored. One drift found: two Supabase keys present in `.env` but missing from `.env.example`.
- The rate-limit "key by API key, not IP" fix (commit `152018d`) was **not applied uniformly** — the plain `/ws` endpoint still rate-limits by IP, unlike `/ws/conversation`. (Security audit additionally found the *global* middleware version of this fix is itself exploitable — see §7, Finding 5.)
- **Highest-blast-radius rename targets**: the `NEGAO_` env-var prefix (silent fallback-to-default failure mode if renamed inconsistently, not a loud crash) and the hardcoded `/opt/negao` VPS deploy path (needs a live-server migration step, not a source edit).

---

## 7. Security / QA / Reliability

**Overall posture: not approved for production.** Clean fundamentals (no injection, no eval/subprocess, correct CSPRNG, `.env` properly gitignored, safe markdown rendering, sound generic error responses) are undermined by a broken authentication model.

### Blockers
1. **`frontend/app/api/ws-info/route.ts` returns the shared backend API key to any unauthenticated caller** — anyone who loads the site (or curls the endpoint) gets full API authority: unmetered NVIDIA spend, agent-config tampering, everything the key unlocks. This defeats the otherwise-correct BFF proxy design elsewhere.
2. **`POST /database/api-keys` has no auth dependency** — anyone can mint a new API key. Currently inert (minted keys aren't checked anywhere yet) but becomes full compromise the instant that verification path ships.
3. **No startup validation rejects default secrets** — if `NEGAO_API_KEY`/`NEGAO_SECRET_KEY` are unset in a deploy environment, the service silently authenticates with a legacy development value committed in `settings.py` (`[REDACTED_LEGACY_DEV_KEY]`), duplicated in 5 places across frontend and tests.

### Critical/High
4. Auth is opt-in per-route with no global guard — 11 of ~20 endpoints have zero auth, including an unauthenticated arbitrary-write `PUT /database/config/{key}`.
5. The API-key rate-limit fix is implemented incorrectly: the bucket key is the raw, unvalidated `X-API-Key` header read *before* authentication — an attacker can rotate a random header value per request to get an unbounded fresh bucket every time. A correct implementation (`_extract_key`, keyed on the verified principal) already exists in the codebase but has no call sites.
6. Prometheus metrics are fully defined but never recorded anywhere in the request path — `/metrics` is structurally valid but permanently empty. No latency instrumentation exists for model/tool/vision/stt/tts calls; `trace_id`/`session_id` aren't propagated into logs despite the data model supporting it.
7. CORS defaults to `["*"]` (the credentials-guard against `*` is correctly implemented, but combined with Blocker #1 it means any origin can fetch the key and call the API directly).

### Medium
8. API keys are also passed in WebSocket query strings (moot today given #1, but must be fixed alongside it); all three WS endpoints `accept()` before checking auth.
9. Debug/production gates (`memory`, `monitoring`, `events` routers) fail open toward permissive behavior on any settings error — notably `events/_publish` becomes reachable if `NEGAO_ENV` is ever unset, allowing audit-trail forgery.
10. Unauthenticated infrastructure disclosure on `/`, `/readyz`, `/database/status`, `/docs`, `/openapi.json` (DB credentials are correctly stripped from the one that could leak them — verified clean).
11. PWA service worker caches all API responses (including chat content) to disk for 24h with an overly broad `urlPattern` — readable offline on a shared device.
12. No frontend security headers at all (no CSP, HSTS, X-Frame-Options, Referrer-Policy).
13. CI runs lint/typecheck/test/build only — no dependency scanning, secret scanning, SAST, or container scanning.

### Test baseline (verified by running the suite)
**60 tests, 59 passed, 1 skipped** (the one live-DB integration test, correctly skipped for missing env). Good coverage of what's implemented (retry/circuit-breaker, Redis CRUD, WS auth rejection); **zero tests assert that currently-unprotected endpoints should be protected**, no rate-limit tests, no CORS/headers tests.

### Rename risk in this domain
No database table/column names contain "negao" — that's the cleanest category. Prometheus metric names (`negao_requests_total` etc.) and the OTel service name (`negao-ai`) are the highest-risk items here: renaming breaks any dashboards/alerts built on them without a dual-emit transition.

---

## 8. Independent finding: live credentials committed to git

Not part of the rebrand, surfaced during the audit, **recommend acting on immediately regardless of which phase runs next**:
- `REDIS_CLOUD_CONFIG.md` (git-tracked) contains a plaintext Redis Cloud password, appearing 4 times, despite the file's own text claiming it's gitignored.
- `test_supabase.py` / `test_supabase_ssl.py` (git-tracked) hardcode a Supabase Postgres password.
- `test_redis.py` / `test_redis_simple.py` (git-tracked) hardcode the same Redis password as a fallback default.
- The local `.env` (correctly gitignored, not a git leak) contains a live-looking NVIDIA API key and the same Supabase/Redis credentials — worth rotating too since they're duplicated into git-tracked files.

**Recommendation: rotate `NEGAO_API_KEY`, `NEGAO_NVIDIA_API_KEY`, the Redis Cloud password, and the Supabase password.**

---

## 9. Root-level clutter / dead code

The repository previously contained several setup and design status snapshots at the root. Those redundant reports were removed during the cleanup; operational guidance remains in `README.md`, `TESTING_GUIDE.md`, `INFRASTRUCTURE_READY.md`, and `REDIS_CLOUD_CONFIG.md`. The ad-hoc connectivity scripts remain separate from the test suite and should be consolidated when their coverage is replaced. Local RPM installers are not part of the repository.

The 9 unmounted stub modules (~50 files/directories) are forward-scaffolding consistent with the documented roadmap, not leftover dead code — low-value rename targets since they do nothing yet.

---

## 10. Rebrand surface summary (101 files)

| Category | Risk | Examples |
|---|---|---|
| ENV VARIABLE (`NEGAO_` prefix, ~25 vars) | **HIGH** | Read in Python, TS, and shell — needs a dual-read compat shim during rollout |
| DATABASE (Postgres user/db name `negao`) | **HIGH** | Live credential/connection identity, not just a string |
| Persona system prompt (3 hardcoded copies) | **HIGH** | Behavioral instruction to the LLM, not just branding; also hardcodes a real person's name |
| Prometheus metric names, OTel service name, Redis consumer-group name | **HIGH** | Breaks dashboards/alerts and drops in-flight stream state on rename |
| Compose project names, `/opt/negao` VPS path, GitHub repo URL | **HIGH** (infra) | Needs a live-deployment migration step |
| Default legacy API key literal (`[REDACTED_LEGACY_DEV_KEY]`, duplicated in 5 places) | **HIGH** | Drift risk if only some copies updated |
| USER-FACING UI copy (~55 occurrences, ~20 components) | **LOW individually, large volume** | Straightforward text edits; some inside `aria-label`s |
| localStorage keys, logger names, file paths, package names | **LOW** | Cosmetic / client-only |
| Documentation, docstrings | **LOW** | Large volume, no functional risk |

No table/column names in the database are affected — the highest-risk rename category (schema) is clean.

---

## 11. What Phase 0 did not cover

- Runtime exploit verification for the security Blockers (static evidence only — no server was started, no requests issued).
- `npm audit` / `pip-audit` dependency vulnerability scan.
- Full git-history scan for "negao" in old commits/blobs (only working-tree content was checked).
- SVG icon asset *content* (only filenames were checked).
- Deep call-graph verification of the "modules never call each other directly" architectural rule from the docs.

# Sophie / Ultron — Cloudflare Workers Free pilot

This is an **isolated test deployment**, not a replacement for the working
Docker/Next.js/FastAPI deployment. The test Worker is named
`sophie-ultron-free-test` and only uses its own `*.workers.dev` address.

## What this pilot actually hosts

- The **existing** Next.js 15 frontend (including the 3D sentinel avatar),
  middleware, auth endpoints and BFF route handlers, adapted through OpenNext.
- No Cloudflare Containers, paid features, R2 buckets or domain changes.
- **Not yet** the Python/FastAPI backend, PostgreSQL, Redis, migrations or
  scheduled workers. The backend source is in this repository, but it cannot
  be deployed unchanged as a Worker; see the compatibility findings below.

The Worker **must not** be connected to a production backend or reuse
production service API keys, databases, OAuth keys, or user data for this test.

Cloudflare Workers Free has a 10 ms CPU-time limit per request. A successful
build does not prove that this dynamic Next.js application will meet that
runtime limit; actual free-tier requests must be measured before accepting the
pilot. The Free plan also allows 100,000 requests per day, 128 MiB per
isolate, 50 subrequests per request, and a 64 MiB Worker size. The local dry-run
currently reports a 6,211.97 KiB upload (1,249.14 KiB gzip), below the Worker
size limit. Rendering/voice performance and WebSocket availability still
require real browser testing.

R2 is not configured for this pilot, so the optional `rclone.js` peer is
intentionally omitted. The package introduced `adm-zip` and is not required by
the no-R2 build. OpenNext's build-time `glob` dependencies are pinned to the
patched 14.0.2 release; this combination has passed the Cloudflare build and
dry-run locally.

## Backend deployment status

Cloudflare supports FastAPI through Python Workers, so an isolated native
backend pilot is technically possible. The current backend is not a drop-in
Worker, though, and must not be treated as deployed:

- Its database layer uses async SQLAlchemy with `asyncpg`; Cloudflare's Python
  Workers documentation currently says async SQLAlchemy is not supported.
- A `pywrangler sync` compatibility check against the locked dependencies did
  not resolve for the available Worker runtimes: with Python 3.14 it reported
  no usable PyEmscripten wheel for `orjson` (and subsequent checks also exposed
  missing wheels for `cryptography` and the locked `pydantic-core`); with
  Python 3.13 it reported no usable `asyncpg` wheel.
- The backend also uses Redis-backed rate limits, short-term memory,
  conversation persistence, WebSocket tickets, Redis Streams, password hashing,
  encrypted credentials, startup event-bus tasks, and PostgreSQL/pgvector.
  These need independent compatibility and runtime validation in the Worker
  environment; swapping just the entrypoint would leave important routes
  unusable.

An initial, opt-in SQLAlchemy compatibility adapter now exists at
`backend/app/infrastructure/cloudflare_db.py`. It wraps synchronous SQLAlchemy
operations with async-shaped methods and expects Hyperdrive's binding; SQLite
unit tests cover session and transaction behavior. The adapter is not wired to
a Worker entrypoint yet, does not include the required `pg8000` Worker package,
and has not been exercised by Cloudflare's runtime or against PostgreSQL. The
normal Docker path still uses async SQLAlchemy and `asyncpg`.

The remaining port includes more than a database driver. The current password
hasher uses Argon2id with 65,536 KiB of memory, while a Workers Free isolate is
limited to 128 MiB and 10 ms of CPU per request. This needs a separately tested
design that preserves the current password hashes; lowering the password cost
to fit without evidence is not acceptable. SQLite Durable Objects are
available on Free and allow up to 30 seconds of CPU per invocation, so a
separate Argon2-compatible Durable Object is a candidate for testing; it still
has to fit within the 128 MiB isolate memory limit and preserve existing
password hashes. Redis also cannot be replaced by per-isolate memory because
that would break shared rate limits, session state, WebSocket tickets, and
event delivery. Free Durable Objects have request and storage quotas, and
Queues include 10,000 operations per day, so a replacement must preserve the
current atomicity and delivery guarantees within those limits.

The backend port remains isolated from Docker and production. Do not point it
at production data or set the frontend's `SOPHIE_API_URL` / `SOPHIE_WS_URL`
until the Worker package resolves, the full app imports in Python Workers, and
auth, PostgreSQL, chat, WebSocket, voice, security and free-tier performance
checks pass. No paid Cloudflare feature should be enabled for this pilot.

## Build and locally preview the real Workers bundle

From `frontend/`, use Node.js 22+:

```sh
npm ci --ignore-scripts
npm run lint
npm run typecheck
npm run cloudflare:build
npm run cloudflare:dry-run
npm run cloudflare:preview
```

Run the preview without secrets first. The interface may render, but auth and
chat requests should remain unavailable until a test backend is connected.
Do not interpret a successful login-page render as a fully functioning agent.

## Deploy only after a Cloudflare Free account is authenticated

1. Log into the intended **Free** Cloudflare account with `npx wrangler login`.
2. Verify the account and plan in the Cloudflare dashboard; do not upgrade or
   enable Containers or other paid resources.
3. `SOPHIE_PUBLIC_ORIGIN` is set as a non-secret runtime variable in
   `wrangler.jsonc`, using the `workers.dev` subdomain currently shown in the
   account. Confirm Wrangler reports the same URL on first deploy before
   testing auth; the security middleware rejects auth mutations if the origin
   does not match. If a **separate test backend** is available, set
   `SOPHIE_API_URL` (HTTPS) and `SOPHIE_WS_URL` (WSS) as runtime variables on
   the test Worker. Use Cloudflare's encrypted secret storage for any actual
   credentials.
4. Run `npm run cloudflare:deploy` from `frontend/`. It uses `--keep-vars`
   so dashboard-only runtime variables and secrets are not removed.
5. Confirm the resulting `https://sophie-ultron-free-test.<account>.workers.dev`
   address from Wrangler's output; do not guess the account subdomain.

There is deliberately **no CI auto-deploy** and **no permanent API token** in
the repository. Deployment requires the owner to connect the Cloudflare
account. No secret should ever be pasted into a GitHub file or build log.

## Acceptance checks on the real Free plan

- Homepage and login render without Worker error 1102 (CPU/memory limit).
- Desktop and mobile avatar load, remain responsive, and work with reduced
  motion; no sensitive content leaks through public assets or caching.
- The CSP nonce is present and valid; cookies have HttpOnly/Secure/SameSite.
- Requests without a session cannot access protected BFF paths.
- Once a test backend exists: login, chat, session history, WebSocket, voice,
  timeouts and error handling work with test users and test data.
- Cloudflare usage and Workers AI quotas (if added later) stay within free
  allowances; verify there is no billable resource.

## Rollback

Delete or disable **only** the named test Worker in Cloudflare, leaving the
main application, domains and database unchanged. Keep any optional test
database isolated and back it up before deleting it.

Documentation:

- https://developers.cloudflare.com/workers/framework-guides/web-apps/opennext/
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/workers/languages/python/packages/fastapi/
- https://developers.cloudflare.com/hyperdrive/examples/python-workers/
- https://developers.cloudflare.com/durable-objects/platform/pricing/
- https://developers.cloudflare.com/durable-objects/platform/limits/
- https://developers.cloudflare.com/queues/platform/pricing/
- https://opennext.js.org/cloudflare/get-started

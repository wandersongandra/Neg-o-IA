# Sophie / Ultron — Cloudflare Workers Free pilot

This is an **isolated Cloudflare Free pilot**, not a replacement for the
Docker deployment. The frontend Worker is `sophie-ultron-free-test`; the
separate API Worker is `sophie-ultron-api-free-test`. Both use the account's
`workers.dev` subdomain. The test database is a new D1 database named
`sophie-ultron-free-test`; no production domain, PostgreSQL database, Redis
instance, or user data is reused.

## What this pilot actually hosts

- The Next.js 15 frontend, 3D avatar, middleware, auth and BFF endpoints through
  OpenNext.
- A native TypeScript Worker API using D1 for identities, sessions,
  conversations, memory, knowledge, learning feedback, plans, and automations;
  Durable Objects for WebSockets, rate limits and password hashing; and
  Workers AI for chat, vision, transcription and speech synthesis.
- No Containers, paid plan features, R2 bucket or domain changes.
- The Python/FastAPI backend and its PostgreSQL/Redis services remain the
  Docker implementation. They are not run inside this pilot; the UI-facing
  routes are implemented by the separate Worker API to fit the Free runtime.

The Worker **must not** be connected to a production backend or reuse
production service API keys, databases, OAuth keys, or user data for this test.

Workers Free allows 100,000 requests/day, 10 ms CPU/request, 128 MiB memory,
50 subrequests/request, and 64 MiB per Worker. D1 Free provides 5 million rows
read/day, 100,000 rows written/day, 500 MB per database, 5 GB across the
account, and 50 queries per Worker invocation. Workers AI has a 10,000-Neuron
daily free allocation; requests fail after the free allocation is exhausted
unless the account is upgraded. This pilot must not enable a paid plan.

Password derivation uses a SQLite-backed Durable Object because Free Workers
HTTP requests have a 10 ms CPU limit while Durable Object requests have a
30-second CPU limit. The Durable Object receives the password and salt over an
internal service binding, returns the derived hash, and stores no credentials.
Durable Objects are available on Free; verify the account's daily request and
storage quotas during the live pilot.

The prior frontend-only dry-run measured about 6.2 MiB upload (1.2 MiB gzip).
That measurement predates the API port and PWA migration, so it must be
refreshed by the CI build. Real Workers runtime checks are still required for
the 10 ms CPU ceiling, WebSocket behavior, model availability and quota
handling.

R2 is not configured for this pilot, so the optional `rclone.js` peer is
intentionally omitted. The package introduced `adm-zip` and is not required by
the no-R2 build. OpenNext's build-time `glob` dependencies are pinned to the
patched 14.0.2 release. The frontend Cloudflare build in this executor was
terminated by its memory limit (exit 137), so the GitHub Actions build must
confirm the final bundle before deployment.

## Worker API scope and limits

The frontend allowlisted API routes are implemented in
`backend/cloudflare-api/src/index.ts`. This includes registration/login and
session revocation, conversation history and WebSockets, D1-backed memory and
knowledge search, user feedback, planning, safe tool execution and automation
rules, vision, voice, readiness and sanitized monitoring. The Worker tests run
on Cloudflare's local runtime and include owner isolation and confirmation
gates. This local test suite does not call production Workers AI.

The pilot uses Cloudflare Workers AI instead of a ChatGPT Plan token. The
existing ChatGPT Plan OAuth CLI flow is not available in this Worker API;
connecting it requires a separate design and end-to-end validation. External
email, calendar, browser search and arbitrary code execution are not part of
the existing closed Tool Manager catalog and are not enabled by this pilot.
Automation currently accepts only registered read-only tools that do not
require confirmation.

Do not migrate production accounts or data into this pilot. The one-time
bootstrap account is accepted only while D1 has no users and requires the
encrypted `BOOTSTRAP_SECRET` on the API Worker, relayed server-side by the
frontend's `SOPHIE_BOOTSTRAP_SECRET`. Remove both secrets after the initial
account is created. Configure an independent random
`INTERNAL_PROXY_KEY` / `SOPHIE_INTERNAL_PROXY_KEY` pair so the API can safely
honor the original client IP passed by the frontend. Never place these values
in source control or send them in chat.

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

Run the preview without secrets first. API registration and login remain
unavailable until the Cloudflare secrets are configured. The local OpenNext
preview still needs a real browser functional pass after deployment.

## Deploy both isolated Workers

1. Confirm the Cloudflare account stays on **Free**. `workers.dev` is the test
   origin. The frontend variables `SOPHIE_PUBLIC_ORIGIN`, `SOPHIE_API_URL`
   (HTTPS) and `SOPHIE_WS_URL` (WSS) already point to the two pilot Workers.
2. Apply D1 migrations remotely from `backend/cloudflare-api/` with Wrangler.
   The configured D1 database is `sophie-ultron-free-test`; check the database
   id in `wrangler.jsonc` matches the account before applying migrations.
3. Store random `BOOTSTRAP_SECRET` and `INTERNAL_PROXY_KEY` values as encrypted
   API Worker secrets. Store the matching `SOPHIE_BOOTSTRAP_SECRET` and
   `SOPHIE_INTERNAL_PROXY_KEY` secrets on the frontend Worker. Generate and
   pass these values locally; never put them in source or chat.
4. Deploy `sophie-ultron-api-free-test` from `backend/cloudflare-api/`, then
   deploy `sophie-ultron-free-test` from `frontend/` with
   `npm run cloudflare:deploy`. The command retains dashboard variables.
5. Create the first account at `/cadastro`, verify login and then remove the
   bootstrap secret from both Workers. Keep the internal proxy secret.
6. Confirm both `*.workers.dev` URLs in Wrangler and the Cloudflare dashboard.
   The API's `APP_ORIGIN` must exactly match the frontend origin or login
   mutations are rejected.

There is deliberately **no CI auto-deploy** and **no permanent API token** in
the repository. CI typechecks, tests and dry-runs both Workers. Deployment
requires the owner to connect the Cloudflare account. No secret should ever
be pasted into a GitHub file or build log.

## Acceptance checks on the real Free plan

- Homepage and login render without Worker error 1102 (CPU/memory limit).
- Desktop and mobile avatar load, remain responsive, and work with reduced
  motion; no sensitive content leaks through public assets or caching.
- The CSP nonce is present and valid; cookies have HttpOnly/Secure/SameSite.
- Requests without a session cannot access protected BFF paths.
- Use a fresh pilot account and verify login/logout, session revocation, D1
  history, memory retrieval, knowledge search, tool confirmation, automation,
  vision and the 3D avatar.
- Verify both WebSocket chat and voice, transcription and synthesis against
  Workers AI; verify quota exhaustion fails closed without upgrade or charges.
- Check Cloudflare billing and daily Workers, D1 and AI usage; verify that no
  paid resource is enabled.

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

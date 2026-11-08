# Sophie / Ultron — Cloudflare Workers Free pilot

This is an **isolated test deployment**, not a replacement for the working
Docker/Next.js/FastAPI deployment. The test Worker is named
`sophie-ultron-free-test` and only uses its own `*.workers.dev` address.

## What this pilot actually hosts

- The **existing** Next.js 15 frontend (including the 3D sentinel avatar),
  middleware, auth endpoints and BFF route handlers, adapted through OpenNext.
- No Cloudflare Containers, paid features, R2 buckets or domain changes.
- **Not** the Python 3.13/FastAPI backend, PostgreSQL, Redis, migrations or
  scheduled workers. Those dependencies cannot simply be uploaded as a free
  Cloudflare Worker. A working conversational test requires a separately
  provisioned, isolated backend reachable over HTTPS, or a later native
  Cloudflare backend implementation.

The Worker **must not** be connected to a production backend or reuse
production service API keys, databases, OAuth keys, or user data for this test.

Cloudflare Workers Free has a 10 ms CPU-time limit per request. A successful
build does not prove that this dynamic Next.js application will meet that
runtime limit; actual free-tier requests must be measured before accepting the
pilot. Rendering/voice performance and WebSocket availability also require
real browser testing.

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
3. After the first deployment reveals the real `*.workers.dev` address, set
   `SOPHIE_PUBLIC_ORIGIN` to that exact HTTPS origin as a **runtime variable**;
   the production security middleware intentionally rejects auth mutations
   until this value is configured. If a **separate test backend** is available,
   also set `SOPHIE_API_URL` (HTTPS) and `SOPHIE_WS_URL` (WSS) as runtime
   variables on the test Worker.
   Use Cloudflare's encrypted secret storage for any actual credentials.
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
- https://opennext.js.org/cloudflare/get-started

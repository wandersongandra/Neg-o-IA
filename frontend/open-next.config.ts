import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// Pilot without R2/cache bindings or resources that require Workers Paid.
// Keep the app's existing backend and session flows unchanged.
export default defineCloudflareConfig();

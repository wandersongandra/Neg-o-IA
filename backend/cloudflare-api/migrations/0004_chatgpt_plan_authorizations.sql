CREATE TABLE IF NOT EXISTS openai_plan_authorizations (
  state TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  host_id TEXT NOT NULL,
  client_id TEXT NOT NULL,
  nonce TEXT NOT NULL,
  code_challenge TEXT NOT NULL,
  redirect_uri TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS openai_plan_authorizations_expiry ON openai_plan_authorizations(expires_at);

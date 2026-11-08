ALTER TABLE settings ADD COLUMN provider TEXT NOT NULL DEFAULT 'auto';
ALTER TABLE settings ADD COLUMN model TEXT;

CREATE TABLE IF NOT EXISTS openai_plan_hosts (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  host_id TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS openai_plan_credentials (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  client_id TEXT NOT NULL,
  host_id TEXT NOT NULL,
  email TEXT,
  access_token_cipher TEXT NOT NULL,
  refresh_token_cipher TEXT NOT NULL,
  scopes TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  connected_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS openai_plan_credentials_expiry ON openai_plan_credentials(expires_at);

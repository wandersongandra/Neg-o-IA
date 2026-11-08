-- Persistent state for the Cloudflare port of the remaining agent modules.
CREATE TABLE IF NOT EXISTS knowledge_documents (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL, content TEXT NOT NULL CHECK(length(content) <= 200000),
  source_type TEXT NOT NULL CHECK(source_type IN ('manual','markdown','note')),
  source_uri TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS knowledge_documents_user ON knowledge_documents(user_id, created_at DESC);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(document_id UNINDEXED, user_id UNINDEXED, title, content, tokenize='unicode61');
CREATE TABLE IF NOT EXISTS learning_experiences (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  message_ref TEXT NOT NULL, rating INTEGER NOT NULL CHECK(rating IN (-1,1)),
  lesson TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS learning_user_created ON learning_experiences(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS automation_rules (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL, event_type TEXT NOT NULL, action_tool TEXT NOT NULL,
  action_args TEXT NOT NULL DEFAULT '{}', enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_triggered_at TEXT
);
CREATE INDEX IF NOT EXISTS automation_user_rules ON automation_rules(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS execution_plans (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  goal TEXT NOT NULL, intent TEXT NOT NULL, steps TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tool_idempotency (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, tool_name TEXT NOT NULL,
  idempotency_key TEXT NOT NULL, output TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(user_id,tool_name,idempotency_key)
);

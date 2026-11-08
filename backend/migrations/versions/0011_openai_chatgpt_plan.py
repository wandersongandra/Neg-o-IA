"""Store per-user ChatGPT plan authorization and stable app host identity."""

from __future__ import annotations

from alembic import op

revision = "0011_openai_chatgpt_plan"
down_revision = "0010_memory_knowledge_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ai")
    op.execute(
        """
        CREATE TABLE ai.openai_plan_host (
            id smallint PRIMARY KEY CHECK (id = 1),
            host_id varchar(128) NOT NULL UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE ai.openai_plan_credentials (
            user_id uuid PRIMARY KEY REFERENCES identity.users(id) ON DELETE CASCADE,
            email varchar(320),
            client_id varchar(256) NOT NULL,
            host_id varchar(128) NOT NULL,
            access_token_cipher bytea NOT NULL,
            refresh_token_cipher bytea NOT NULL,
            account_subject_cipher bytea NOT NULL,
            scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
            expires_at timestamptz NOT NULL,
            connected_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_openai_plan_scopes_array CHECK (jsonb_typeof(scopes) = 'array')
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_openai_plan_credentials_expiry ON ai.openai_plan_credentials (expires_at)"
    )
    op.execute("ALTER TABLE ai.openai_plan_credentials ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai.openai_plan_credentials FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY openai_plan_credentials_owner_isolation
        ON ai.openai_plan_credentials
        USING (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
        WITH CHECK (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai.openai_plan_credentials")
    op.execute("DROP TABLE IF EXISTS ai.openai_plan_host")
    op.execute("DROP SCHEMA IF EXISTS ai")

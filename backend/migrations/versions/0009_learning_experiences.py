"""Persist explicit, user-owned corrections for personalized retrieval."""

from __future__ import annotations

from alembic import op

revision = "0009_learning_experiences"
down_revision = "0008_knowledge_tenant_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS learning")
    op.execute(
        """
        CREATE TABLE learning.experiences (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            session_id varchar(128) NOT NULL,
            message_ref varchar(128) NOT NULL,
            rating integer NOT NULL CHECK (rating IN (-1, 1)),
            lesson text,
            embedding vector(384),
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_learning_experience_message
                UNIQUE (user_id, session_id, message_ref),
            CONSTRAINT ck_learning_experience_lesson
                CHECK (lesson IS NULL OR char_length(lesson) <= 2000)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_learning_experiences_user_created "
        "ON learning.experiences (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_learning_experiences_user_session "
        "ON learning.experiences (user_id, session_id)"
    )
    op.execute("ALTER TABLE learning.experiences ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE learning.experiences FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY learning_experience_owner_isolation
        ON learning.experiences
        USING (
            user_id = nullif(current_setting('app.user_id', true), '')::uuid
        )
        WITH CHECK (
            user_id = nullif(current_setting('app.user_id', true), '')::uuid
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS learning.experiences")

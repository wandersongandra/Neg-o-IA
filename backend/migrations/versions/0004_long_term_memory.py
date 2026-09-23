"""0004_long_term_memory — persistent, user-isolated memory vault."""

from __future__ import annotations

from alembic import op

revision = "0004_long_term_memory"
down_revision = "0003_audit_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE SCHEMA IF NOT EXISTS memory")
    op.execute(
        """
        CREATE TABLE memory.memories (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL
                REFERENCES identity.users(id) ON DELETE CASCADE,
            source_session_id varchar(128),
            kind varchar(32) NOT NULL DEFAULT 'note'
                CHECK (kind IN ('note', 'preference', 'fact', 'instruction')),
            content text NOT NULL
                CHECK (char_length(content) BETWEEN 1 AND 4000),
            content_hash varchar(64) NOT NULL,
            importance smallint NOT NULL DEFAULT 3
                CHECK (importance BETWEEN 1 AND 5),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            search_vector tsvector GENERATED ALWAYS AS (
                to_tsvector('simple', content)
            ) STORED,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            last_accessed_at timestamptz,
            expires_at timestamptz,
            CONSTRAINT uq_memory_user_content_hash UNIQUE (user_id, content_hash)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_memory_user_updated
        ON memory.memories (user_id, updated_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_memory_user_expires
        ON memory.memories (user_id, expires_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_memory_search_vector
        ON memory.memories USING GIN (search_vector)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_memory_content_trgm
        ON memory.memories USING GIN (content gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory.memories")
    op.execute("DROP SCHEMA IF EXISTS memory")

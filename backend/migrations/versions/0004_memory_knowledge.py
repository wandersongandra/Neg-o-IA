"""0004_memory_knowledge — memória longa e Knowledge Vault com pgvector."""

from __future__ import annotations

from alembic import op

revision = "0004_memory_knowledge"
down_revision = "0003_audit_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS memory")
    op.execute("CREATE SCHEMA IF NOT EXISTS knowledge")

    op.execute(
        """
        CREATE TABLE memory.policies (
            user_id uuid PRIMARY KEY REFERENCES identity.users(id) ON DELETE CASCADE,
            auto_capture_enabled boolean NOT NULL DEFAULT false,
            retention_days integer NOT NULL DEFAULT 90
                CHECK (retention_days BETWEEN 1 AND 3650),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory.entries (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            session_id varchar(128),
            source varchar(32) NOT NULL,
            content text NOT NULL,
            content_hash char(64) NOT NULL,
            importance real NOT NULL DEFAULT 0.5
                CHECK (importance >= 0 AND importance <= 1),
            embedding vector(384) NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz,
            CONSTRAINT uq_memory_entry_content UNIQUE (user_id, content_hash, source)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_memory_entries_user_created
        ON memory.entries (user_id, created_at DESC)
        """
    )
    op.execute("CREATE INDEX ix_memory_entries_expiry ON memory.entries (expires_at)")
    op.execute(
        "CREATE INDEX ix_memory_entries_embedding ON memory.entries "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.execute(
        """
        CREATE TABLE knowledge.documents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            title varchar(256) NOT NULL,
            source_type varchar(32) NOT NULL DEFAULT 'manual',
            source_uri text,
            content_hash char(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_knowledge_document_content UNIQUE (user_id, content_hash)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE knowledge.chunks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id uuid NOT NULL REFERENCES knowledge.documents(id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL,
            content text NOT NULL,
            embedding vector(384) NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_knowledge_chunk_index UNIQUE (document_id, chunk_index)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_knowledge_documents_user
        ON knowledge.documents (user_id, updated_at DESC)
        """
    )
    op.execute("CREATE INDEX ix_knowledge_chunks_user ON knowledge.chunks (user_id)")
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding ON knowledge.chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS knowledge CASCADE")
    op.execute("DROP SCHEMA IF EXISTS memory CASCADE")

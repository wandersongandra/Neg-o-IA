"""Bind each knowledge chunk to its document's owner."""

from __future__ import annotations

from alembic import op

revision = "0008_knowledge_tenant_integrity"
down_revision = "0007_service_api_key_expiry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Refuse the migration if pre-existing rows cross document ownership.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM knowledge.chunks AS chunk
                JOIN knowledge.documents AS document
                  ON document.id = chunk.document_id
                WHERE chunk.user_id <> document.user_id
            ) THEN
                RAISE EXCEPTION
                    'knowledge tenant integrity migration blocked: chunk/document owners differ';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        ALTER TABLE knowledge.documents
        ADD CONSTRAINT uq_knowledge_documents_id_user UNIQUE (id, user_id)
        """
    )
    op.execute(
        """
        ALTER TABLE knowledge.chunks
        DROP CONSTRAINT IF EXISTS chunks_document_id_fkey
        """
    )
    op.execute(
        """
        ALTER TABLE knowledge.chunks
        ADD CONSTRAINT fk_knowledge_chunks_document_user
        FOREIGN KEY (document_id, user_id)
        REFERENCES knowledge.documents (id, user_id)
        ON DELETE CASCADE
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE knowledge.chunks
        DROP CONSTRAINT IF EXISTS fk_knowledge_chunks_document_user
        """
    )
    op.execute(
        """
        ALTER TABLE knowledge.chunks
        ADD CONSTRAINT chunks_document_id_fkey
        FOREIGN KEY (document_id)
        REFERENCES knowledge.documents (id)
        ON DELETE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE knowledge.documents
        DROP CONSTRAINT IF EXISTS uq_knowledge_documents_id_user
        """
    )

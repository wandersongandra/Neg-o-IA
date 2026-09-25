"""0007_service_api_key_expiry — expiração obrigatória para credenciais de serviço."""

from __future__ import annotations

from alembic import op

revision = "0007_service_api_key_expiry"
down_revision = "0006_audit_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE identity.api_keys
        ADD COLUMN IF NOT EXISTS expires_at timestamptz
        """
    )
    # Compatibilidade segura: chaves já existentes recebem pelo menos 30 dias
    # de transição, sem se tornarem credenciais sem expiração.
    op.execute(
        """
        UPDATE identity.api_keys
        SET expires_at = GREATEST(
            created_at + interval '90 days',
            now() + interval '30 days'
        )
        WHERE expires_at IS NULL
        """
    )
    op.execute(
        """
        ALTER TABLE identity.api_keys
        ALTER COLUMN expires_at SET NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_api_keys_expires_at
        ON identity.api_keys (expires_at)
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "0007_service_api_key_expiry is intentionally irreversible once "
        "expiring credentials are in use"
    )

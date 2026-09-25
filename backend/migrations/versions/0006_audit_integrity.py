"""0006_audit_integrity — HMAC integrity tag for newly persisted audit events."""

from __future__ import annotations

from alembic import op

revision = "0006_audit_integrity"
down_revision = "0005_agentic_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE events.audit_events
        ADD COLUMN IF NOT EXISTS integrity_hash varchar(64)
        """
    )
    op.execute(
        """
        ALTER TABLE events.audit_events
        ADD CONSTRAINT ck_audit_events_integrity_hash
        CHECK (
            integrity_hash IS NULL
            OR integrity_hash ~ '^[0-9a-f]{64}$'
        )
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "0006_audit_integrity is intentionally irreversible once signed audit events exist"
    )

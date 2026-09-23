"""0003_audit_hardening — durable audit identifiers and safe rollover."""

from __future__ import annotations

from alembic import op

revision = "0003_audit_hardening"
down_revision = "0002_identity_sessions"
branch_labels = None
depends_on = None

_AUDIT_REFERENCE_COLUMNS = (
    "trace_id",
    "correlation_id",
    "parent_id",
    "user_id",
    "session_id",
)


def upgrade() -> None:
    # The previous trigger tried to create a missing partition from a row-level
    # INSERT path. Remove runtime DDL and guarantee an always-valid destination.
    op.execute("DROP TRIGGER IF EXISTS audit_events_partition_trg ON events.audit_events")
    op.execute("DROP FUNCTION IF EXISTS events.create_partition_if_missing()")

    # Correlation IDs may originate from external callers and conversation
    # session IDs are opaque strings, so these references are not UUID-only.
    for column in _AUDIT_REFERENCE_COLUMNS:
        op.execute(
            "ALTER TABLE events.audit_events "
            f"ALTER COLUMN {column} TYPE varchar(128) "
            f"USING {column}::text"
        )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS events.audit_events_default
        PARTITION OF events.audit_events DEFAULT
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_audit_default_correlation
        ON events.audit_events_default (correlation_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_audit_default_occurred
        ON events.audit_events_default (occurred_at DESC)
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "0003_audit_hardening is intentionally irreversible after opaque audit identifiers exist"
    )

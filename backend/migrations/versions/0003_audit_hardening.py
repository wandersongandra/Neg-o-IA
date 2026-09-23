"""0003_audit_hardening — auditoria durável e resiliente a novos períodos."""

from __future__ import annotations

from alembic import op

revision = "0003_audit_hardening"
down_revision = "0002_identity_sessions"
branch_labels = None
depends_on = None

_UUID_REGEX = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def upgrade() -> None:
    # Conversation session IDs are opaque strings, not UUIDs. Audit principals
    # may also represent service identities, so both columns must be textual.
    op.execute("ALTER TABLE events.audit_events ALTER COLUMN user_id TYPE text USING user_id::text")
    op.execute(
        "ALTER TABLE events.audit_events "
        "ALTER COLUMN session_id TYPE text USING session_id::text"
    )

    # A BEFORE INSERT trigger on the partitioned parent cannot be relied on to
    # create a missing destination partition. A DEFAULT partition keeps audit
    # writes available across month boundaries; maintenance can later detach
    # and repartition rows without losing events.
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
    op.execute("DROP TRIGGER IF EXISTS audit_events_partition_trg ON events.audit_events")
    op.execute("DROP FUNCTION IF EXISTS events.create_partition_if_missing()")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events.audit_events_default")
    op.execute(
        f"""
        ALTER TABLE events.audit_events
        ALTER COLUMN user_id TYPE uuid
        USING CASE
            WHEN user_id ~* '{_UUID_REGEX}'
            THEN user_id::uuid
            ELSE NULL
        END
        """
    )
    op.execute(
        f"""
        ALTER TABLE events.audit_events
        ALTER COLUMN session_id TYPE uuid
        USING CASE
            WHEN session_id ~* '{_UUID_REGEX}'
            THEN session_id::uuid
            ELSE NULL
        END
        """
    )

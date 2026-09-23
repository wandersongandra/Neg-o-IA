"""0003_security_hardening — durable audit identifiers and safe partitions."""

from __future__ import annotations

from alembic import op

revision = "0003_security_hardening"
down_revision = "0002_identity_sessions"
branch_labels = None
depends_on = None

_ENSURE_PARTITIONS_FUNCTION = r"""
CREATE OR REPLACE FUNCTION events.ensure_audit_partitions(months_ahead integer DEFAULT 24)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, events
AS $$
DECLARE
    offset_month integer;
    start_ts date;
    end_ts date;
    partition_name text;
BEGIN
    IF months_ahead < 1 OR months_ahead > 36 THEN
        RAISE EXCEPTION 'months_ahead must be between 1 and 36';
    END IF;

    FOR offset_month IN 0..months_ahead LOOP
        start_ts := (date_trunc('month', CURRENT_DATE) + make_interval(months => offset_month))::date;
        end_ts := (date_trunc('month', CURRENT_DATE) + make_interval(months => offset_month + 1))::date;
        partition_name := 'audit_events_' || to_char(start_ts, 'YYYY_MM');

        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS events.%I PARTITION OF events.audit_events '
            'FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_ts, end_ts
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON events.%I (correlation_id)',
            'ix_' || partition_name || '_correlation', partition_name
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON events.%I (occurred_at DESC)',
            'ix_' || partition_name || '_occurred', partition_name
        );
    END LOOP;
END;
$$;
"""


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_partition_trg ON events.audit_events")
    op.execute("DROP FUNCTION IF EXISTS events.create_partition_if_missing()")

    # Audit references are opaque identifiers; they are not guaranteed to be UUIDs.
    for column in ("trace_id", "correlation_id", "parent_id", "user_id", "session_id"):
        op.execute(
            "ALTER TABLE events.audit_events "
            f"ALTER COLUMN {column} TYPE text USING {column}::text"
        )
    op.execute(_ENSURE_PARTITIONS_FUNCTION)
    op.execute("SELECT events.ensure_audit_partitions(24)")
    op.execute(
        "CREATE TABLE IF NOT EXISTS events.audit_events_default "
        "PARTITION OF events.audit_events DEFAULT"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_default_correlation "
        "ON events.audit_events_default (correlation_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_default_occurred "
        "ON events.audit_events_default (occurred_at DESC)"
    )


def downgrade() -> None:
    # The identifier migration is intentionally not reversible without risking
    # loss of valid non-UUID conversation identifiers.
    raise RuntimeError(
        "0003_security_hardening cannot be safely downgraded after non-UUID session ids are stored"
    )

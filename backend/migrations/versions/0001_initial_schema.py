"""0001_initial_schema — fundação do banco NEGÃO AI.

Cria schemas `identity`, `events`, `config`; extensões vector e pgcrypto;
tabelas base; particionamento mensal da auditoria com helper de partição.
"""

from __future__ import annotations

from datetime import UTC, datetime

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

_CREATE_PARTITION_FUNCTION = """
CREATE OR REPLACE FUNCTION events.create_partition_if_missing()
RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    partition_name text;
    start_date date;
    end_date date;
BEGIN
    partition_name := 'audit_events_' || to_char(NEW.occurred_at, 'YYYY_MM');
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = partition_name AND n.nspname = 'events'
    ) THEN
        start_date := date_trunc('month', NEW.occurred_at)::date;
        end_date := (date_trunc('month', NEW.occurred_at) + interval '1 month')::date;
        EXECUTE format(
            'CREATE TABLE events.%I PARTITION OF events.audit_events '
            'FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        EXECUTE format(
            'CREATE INDEX ix_%I_correlation ON events.%I (correlation_id)',
            partition_name, partition_name
        );
        EXECUTE format(
            'CREATE INDEX ix_%I_occurred ON events.%I (occurred_at DESC)',
            partition_name, partition_name
        );
    END IF;
    RETURN NEW;
END;
$$;
"""


def _current_partition() -> str:
    return datetime.now(UTC).strftime("%Y_%m")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.execute("CREATE SCHEMA IF NOT EXISTS events")
    op.execute("CREATE SCHEMA IF NOT EXISTS config")

    op.execute(
        """
        CREATE TABLE identity.users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            username text NOT NULL UNIQUE,
            display_name text,
            status text NOT NULL DEFAULT 'active',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE identity.api_keys (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            key_hash text NOT NULL UNIQUE,
            name text NOT NULL,
            scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            last_used_at timestamptz,
            revoked_at timestamptz
        )
        """
    )
    op.execute(
        """
        CREATE TABLE events.audit_events (
            id uuid NOT NULL,
            event_type text NOT NULL,
            version integer NOT NULL DEFAULT 1,
            producer text NOT NULL,
            trace_id uuid,
            correlation_id uuid,
            parent_id uuid,
            user_id uuid,
            session_id uuid,
            occurred_at timestamptz NOT NULL DEFAULT now(),
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            PRIMARY KEY (id, occurred_at)
        ) PARTITION BY RANGE (occurred_at)
        """
    )
    partition = _current_partition()
    op.execute(
        f"""
        CREATE TABLE events.audit_events_{partition} PARTITION OF events.audit_events
        FOR VALUES FROM (date_trunc('month', now())::date)
                       TO (date_trunc('month', now())::date + interval '1 month')
        """
    )
    op.execute(
        f"CREATE INDEX ix_audit_{partition}_correlation "
        f"ON events.audit_events_{partition} (correlation_id)"
    )
    op.execute(
        f"CREATE INDEX ix_audit_{partition}_occurred "
        f"ON events.audit_events_{partition} (occurred_at DESC)"
    )
    op.execute(_CREATE_PARTITION_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER audit_events_partition_trg
        BEFORE INSERT ON events.audit_events
        FOR EACH ROW EXECUTE FUNCTION events.create_partition_if_missing()
        """
    )
    op.execute(
        """
        CREATE TABLE config.app_config (
            key text PRIMARY KEY,
            value jsonb NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS config.app_config")
    op.execute("DROP TABLE IF EXISTS identity.api_keys")
    op.execute("DROP TABLE IF EXISTS identity.users")
    op.execute("DROP TRIGGER IF EXISTS audit_events_partition_trg ON events.audit_events")
    op.execute("DROP FUNCTION IF EXISTS events.create_partition_if_missing()")
    op.execute("DROP TABLE IF EXISTS events.audit_events CASCADE")
    op.execute("DROP SCHEMA IF EXISTS config CASCADE")
    op.execute("DROP SCHEMA IF EXISTS events CASCADE")
    op.execute("DROP SCHEMA IF EXISTS identity CASCADE")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")

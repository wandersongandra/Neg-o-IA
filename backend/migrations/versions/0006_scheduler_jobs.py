"""0006_scheduler_jobs — agendamentos persistentes por usuário."""

from __future__ import annotations

from alembic import op

revision = "0006_scheduler_jobs"
down_revision = "0005_agentic_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS scheduler")
    op.execute(
        """
        CREATE TABLE scheduler.jobs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            name varchar(160) NOT NULL,
            action_tool varchar(128) NOT NULL,
            action_args jsonb NOT NULL DEFAULT '{}'::jsonb,
            run_at timestamptz NOT NULL,
            interval_seconds integer,
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            last_run_at timestamptz,
            next_run_at timestamptz NOT NULL,
            CONSTRAINT ck_scheduler_interval_positive
                CHECK (interval_seconds IS NULL OR interval_seconds >= 60)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_scheduler_jobs_due
        ON scheduler.jobs (enabled, next_run_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_scheduler_jobs_user
        ON scheduler.jobs (user_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS scheduler CASCADE")

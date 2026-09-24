"""0005_agentic_core — regras de automação persistidas e isoladas por usuário."""

from __future__ import annotations

from alembic import op

revision = "0005_agentic_core"
down_revision = "0004_memory_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS automation")
    op.execute(
        """
        CREATE TABLE automation.rules (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            name varchar(160) NOT NULL,
            event_type varchar(128) NOT NULL,
            action_tool varchar(128) NOT NULL,
            action_args jsonb NOT NULL DEFAULT '{}'::jsonb,
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            last_triggered_at timestamptz,
            CONSTRAINT uq_automation_rule_name UNIQUE (user_id, name)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_automation_rules_user_event
        ON automation.rules (user_id, event_type, enabled)
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS automation CASCADE")

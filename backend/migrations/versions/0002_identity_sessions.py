"""0002_identity_sessions — identidade autenticada e sessões revogáveis."""

from __future__ import annotations

from alembic import op

revision = "0002_identity_sessions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE identity.users ADD COLUMN IF NOT EXISTS password_hash text")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS identity.devices (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            device_name text NOT NULL,
            device_type text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            last_seen_at timestamptz NOT NULL DEFAULT now(),
            revoked_at timestamptz
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_devices_user_id ON identity.devices (user_id)")
    op.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_devices_user_name_type
        ON identity.devices (user_id, device_name, device_type)"""
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS identity.sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
            device_id uuid REFERENCES identity.devices(id) ON DELETE SET NULL,
            token_hash varchar(64) NOT NULL UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            last_seen_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON identity.sessions (user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sessions_expires_at ON identity.sessions (expires_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS identity.sessions")
    op.execute("DROP TABLE IF EXISTS identity.devices")
    op.execute("ALTER TABLE identity.users DROP COLUMN IF EXISTS password_hash")

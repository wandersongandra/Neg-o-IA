"""Enforce user ownership for long-term memory and knowledge tables."""

from __future__ import annotations

from alembic import op

revision = "0010_memory_knowledge_rls"
down_revision = "0009_learning_experiences"
branch_labels = None
depends_on = None

_TABLES = (
    "memory.policies",
    "memory.entries",
    "knowledge.documents",
    "knowledge.chunks",
)


def upgrade() -> None:
    for table in _TABLES:
        short_name = table.split(".", 1)[1]
        policy = f"{short_name}_owner_isolation"
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {policy} ON {table}
            USING (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
            WITH CHECK (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
            """
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        short_name = table.split(".", 1)[1]
        policy = f"{short_name}_owner_isolation"
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

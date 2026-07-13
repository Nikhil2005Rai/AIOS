"""add agent name to tool call audit log

Revision ID: 0003_tool_calls_agent_name
Revises: 0002_tool_calls
Create Date: 2026-07-12 00:02:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_tool_calls_agent_name"
down_revision = "0002_tool_calls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("tool_calls")}
    if "agent_name" in columns:
        return

    op.add_column("tool_calls", sa.Column("agent_name", sa.String(length=80), nullable=True))
    op.execute("UPDATE tool_calls SET agent_name = 'planner' WHERE agent_name IS NULL")
    op.alter_column("tool_calls", "agent_name", nullable=False)


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("tool_calls")}
    if "agent_name" in columns:
        op.drop_column("tool_calls", "agent_name")

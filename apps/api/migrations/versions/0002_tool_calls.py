"""add tool call audit log

Revision ID: 0002_tool_calls
Revises: 0001_initial
Create Date: 2026-07-12 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_tool_calls"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "tool_calls" in existing_tables:
        return

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("arguments", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tool_calls_conversation_id"), "tool_calls", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_tool_calls_message_id"), "tool_calls", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_calls_message_id"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_conversation_id"), table_name="tool_calls")
    op.drop_table("tool_calls")

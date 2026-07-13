"""add user api keys

Revision ID: 0004_user_api_keys
Revises: 0003_tool_calls_agent_name
Create Date: 2026-07-12 00:03:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_user_api_keys"
down_revision = "0003_tool_calls_agent_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "user_api_keys" in existing_tables:
        return

    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_api_keys_user_provider"),
    )
    op.create_index(op.f("ix_user_api_keys_user_id"), "user_api_keys", ["user_id"], unique=False)


def downgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "user_api_keys" in existing_tables:
        op.drop_index(op.f("ix_user_api_keys_user_id"), table_name="user_api_keys")
        op.drop_table("user_api_keys")

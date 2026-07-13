"""add user preferred provider

Revision ID: 0005_users_preferred_provider
Revises: 0004_user_api_keys
Create Date: 2026-07-12 00:04:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_users_preferred_provider"
down_revision = "0004_user_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "preferred_provider" not in columns:
        op.add_column("users", sa.Column("preferred_provider", sa.String(length=80), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "preferred_provider" in columns:
        op.drop_column("users", "preferred_provider")

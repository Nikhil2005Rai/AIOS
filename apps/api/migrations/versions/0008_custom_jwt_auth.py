"""add_password_hash_to_user

Revision ID: 0008_custom_jwt_auth
Revises: 0007_clerk_migration
Create Date: 2026-07-22 16:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008_custom_jwt_auth'
down_revision: Union[str, None] = '0007_clerk_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use if_not_exists check via inspector or raw sql safely
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('user')]
    if 'password_hash' not in columns:
        op.add_column('user', sa.Column('password_hash', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'password_hash')

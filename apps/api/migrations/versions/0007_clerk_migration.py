"""clerk_migration

Revision ID: 0007_clerk_migration
Revises: 10cffc244899
Create Date: 2026-07-22 14:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007_clerk_migration'
down_revision: Union[str, None] = '10cffc244899'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop obsolete Better-Auth session/account/verification tables if present
    op.execute('DROP TABLE IF EXISTS "session" CASCADE;')
    op.execute('DROP TABLE IF EXISTS "account" CASCADE;')
    op.execute('DROP TABLE IF EXISTS "verification" CASCADE;')

    # Truncate old user table so new Clerk string IDs (user_2...) populate cleanly
    op.execute('TRUNCATE TABLE "user" CASCADE;')


def downgrade() -> None:
    pass

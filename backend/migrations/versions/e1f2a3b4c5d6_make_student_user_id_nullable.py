"""make students.user_id nullable

Revision ID: e1f2a3b4c5d6
Revises: b2d3f5061728
Create Date: 2026-06-27 00:00:00.000000

A student can now be enrolled without a linked user account. Previously the
service forced user_id=1 because the column was NOT NULL; this drops that
constraint so user_id can be left empty until a login account is created.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'b2d3f5061728'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('students', 'user_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    op.alter_column('students', 'user_id', existing_type=sa.Integer(), nullable=False)

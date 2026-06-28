"""fee_records billing period (recurring fees)

Add a ``period`` column to fee_records and switch the per-student uniqueness
from (student_id, fee_structure_id) to (student_id, fee_structure_id, period)
so a student can hold one record per billing month for a recurring fee.

Revision ID: f3a9c1b2d4e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a9c1b2d4e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    # Add the column with a server_default so existing rows are backfilled to
    # "ONCE" (a single one-time charge), then drop the default so the app must
    # supply the period explicitly going forward.
    op.add_column(
        'fee_records',
        sa.Column('period', sa.String(length=10), nullable=False, server_default='ONCE'),
    )
    op.alter_column('fee_records', 'period', server_default=None)

    op.drop_constraint('uq_fee_records_student_fee_structure', 'fee_records', type_='unique')
    op.create_unique_constraint(
        'uq_fee_records_student_structure_period',
        'fee_records',
        ['student_id', 'fee_structure_id', 'period'],
    )


def downgrade():
    op.drop_constraint('uq_fee_records_student_structure_period', 'fee_records', type_='unique')
    op.create_unique_constraint(
        'uq_fee_records_student_fee_structure',
        'fee_records',
        ['student_id', 'fee_structure_id'],
    )
    op.drop_column('fee_records', 'period')

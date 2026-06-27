"""sprint11_perf_indexes

Revision ID: b2d3f5061728
Revises: a1c2e3f40506
Create Date: 2026-06-23 09:30:00.000000

SMS-064 — add a composite index on attendance(section_id, date) to speed up
section-scoped date-range attendance reports. The existing unique constraint
leads with student_id and cannot serve that access pattern efficiently.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'b2d3f5061728'
down_revision = 'a1c2e3f40506'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.create_index('ix_attendance_section_date', ['section_id', 'date'], unique=False)


def downgrade():
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.drop_index('ix_attendance_section_date')

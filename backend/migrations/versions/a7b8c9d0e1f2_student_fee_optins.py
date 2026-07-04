"""student_fee_optins

Creates the ``student_fee_optins`` table — the v2 opt-in list for optional
flat fee structures (SMS-066 v2). The v1 migration (c4d5e6f70819) deliberately
deferred this table per ADR-005; this migration delivers it.

Each row links a student to an optional flat FeeStructure and optionally
carries a per-student ``amount_override`` (e.g. different hostel room rates).
Soft-delete via ``is_active`` preserves the audit trail.

Safe to fan out across every tenant schema via ``db-upgrade-all``
(batch_alter_table keeps index creation SQLite- and Postgres-friendly).

Revision ID: a7b8c9d0e1f2
Revises: c4d5e6f70819
Create Date: 2026-07-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'c4d5e6f70819'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'student_fee_optins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fee_structure_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('amount_override', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('opted_in_by', sa.Integer(), nullable=True),
        sa.Column('opted_in_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            'amount_override IS NULL OR amount_override >= 0',
            name='ck_student_fee_optins_amount_override_nonneg',
        ),
        sa.ForeignKeyConstraint(
            ['fee_structure_id'], ['fee_structures.id'],
            name='fk_student_fee_optins_fee_structure',
        ),
        sa.ForeignKeyConstraint(
            ['student_id'], ['students.id'],
            name='fk_student_fee_optins_student',
        ),
        sa.ForeignKeyConstraint(
            ['opted_in_by'], ['users.id'],
            name='fk_student_fee_optins_user',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'fee_structure_id', 'student_id',
            name='uq_student_fee_optins_structure_student',
        ),
    )
    with op.batch_alter_table('student_fee_optins', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_student_fee_optins_fee_structure_id'),
            ['fee_structure_id'], unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_student_fee_optins_student_id'),
            ['student_id'], unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_student_fee_optins_opted_in_by'),
            ['opted_in_by'], unique=False,
        )


def downgrade():
    with op.batch_alter_table('student_fee_optins', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_student_fee_optins_opted_in_by'))
        batch_op.drop_index(batch_op.f('ix_student_fee_optins_student_id'))
        batch_op.drop_index(batch_op.f('ix_student_fee_optins_fee_structure_id'))

    op.drop_table('student_fee_optins')

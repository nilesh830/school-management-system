"""sprint2_student_photo_status_sections_documents

Revision ID: 6c69af22f07a
Revises: 637672bfdc20
Create Date: 2026-06-09 00:00:00.000000

Schema changes for Sprint 2 — Student Management:

  T-007-01  Add photo_url to students
  T-011-01  Create student_sections table
  T-012-01  Create student_documents table
  T-013-01  Add status + leaving_date to students
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c69af22f07a'
down_revision = '637672bfdc20'
branch_labels = None
depends_on = None


def upgrade():
    # ── T-012-01: student_documents ──────────────────────────────────────────
    op.create_table(
        'student_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('student_documents', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_student_documents_student_id'), ['student_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_student_documents_uploaded_by'), ['uploaded_by'], unique=False
        )

    # ── T-011-01: student_sections ───────────────────────────────────────────
    # NOTE: FK to sections.id is intentional — the sections table will be
    # created in Sprint 3 (Class & Section Management). SQLite does not
    # enforce FK constraints by default (PRAGMA foreign_keys = OFF), so
    # this table can be created now and the constraint will be active once
    # sections exist.
    op.create_table(
        'student_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=9), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('student_sections', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_student_sections_student_id'), ['student_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_student_sections_section_id'), ['section_id'], unique=False
        )

    # ── T-007-01 + T-013-01: alter students ──────────────────────────────────
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.add_column(sa.Column('photo_url', sa.String(length=500), nullable=True))
        batch_op.add_column(
            sa.Column(
                'status',
                sa.Enum(
                    'active', 'alumni', 'transferred', 'expelled',
                    name='student_status',
                ),
                nullable=False,
                server_default='active',
            )
        )
        batch_op.add_column(sa.Column('leaving_date', sa.Date(), nullable=True))


def downgrade():
    # ── Remove students columns ───────────────────────────────────────────────
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.drop_column('leaving_date')
        batch_op.drop_column('status')
        batch_op.drop_column('photo_url')

    # ── Drop student_sections ─────────────────────────────────────────────────
    with op.batch_alter_table('student_sections', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_student_sections_section_id'))
        batch_op.drop_index(batch_op.f('ix_student_sections_student_id'))
    op.drop_table('student_sections')

    # ── Drop student_documents ────────────────────────────────────────────────
    with op.batch_alter_table('student_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_student_documents_uploaded_by'))
        batch_op.drop_index(batch_op.f('ix_student_documents_student_id'))
    op.drop_table('student_documents')

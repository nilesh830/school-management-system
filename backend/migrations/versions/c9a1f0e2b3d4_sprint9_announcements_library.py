"""sprint9_announcements_library

Revision ID: c9a1f0e2b3d4
Revises: 1bfdc13b6db1
Create Date: 2026-06-21 20:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9a1f0e2b3d4'
down_revision = '1bfdc13b6db1'
branch_labels = None
depends_on = None


def upgrade():
    # ### Announcements (SMS-051) ###
    op.create_table('announcements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('target_roles', sa.JSON(), nullable=True),
        sa.Column('target_class_ids', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('draft','published','archived')", name='ck_announcements_status'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_announcements_created_by'), ['created_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_announcements_status'), ['status'], unique=False)

    # ### Library books (SMS-053) ###
    op.create_table('library_books',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('isbn', sa.String(length=20), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=False),
        sa.Column('publisher', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('total_copies', sa.Integer(), nullable=False),
        sa.Column('available_copies', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('isbn')
    )
    with op.batch_alter_table('library_books', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_library_books_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_library_books_isbn'), ['isbn'], unique=False)
        batch_op.create_index(batch_op.f('ix_library_books_title'), ['title'], unique=False)

    # ### Book issues (SMS-054) ###
    op.create_table('book_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('issued_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('returned_date', sa.Date(), nullable=True),
        sa.Column('fine_amount', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('issued_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('issued','returned','overdue')", name='ck_book_issues_status'),
        sa.ForeignKeyConstraint(['book_id'], ['library_books.id'], ),
        sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('book_issues', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_book_issues_book_id'), ['book_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_book_issues_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_book_issues_student_id'), ['student_id'], unique=False)


def downgrade():
    with op.batch_alter_table('book_issues', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_book_issues_student_id'))
        batch_op.drop_index(batch_op.f('ix_book_issues_status'))
        batch_op.drop_index(batch_op.f('ix_book_issues_book_id'))
    op.drop_table('book_issues')

    with op.batch_alter_table('library_books', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_library_books_title'))
        batch_op.drop_index(batch_op.f('ix_library_books_isbn'))
        batch_op.drop_index(batch_op.f('ix_library_books_category'))
    op.drop_table('library_books')

    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_announcements_status'))
        batch_op.drop_index(batch_op.f('ix_announcements_created_by'))
    op.drop_table('announcements')

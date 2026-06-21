"""sprint7_parent_portal

Revision ID: 1bfdc13b6db1
Revises: b7407516626b
Create Date: 2026-06-21 00:00:00.000000

Tables created:
  parents              - Parent/guardian profiles linked to a user account
  student_parent       - M2M association: students <-> parents (with primary-contact flag)
  leave_applications   - Leave requests submitted by parents for their children
  notifications        - In-app notification log per user
  message_threads      - Conversation threads between a parent and a teacher about a student
  parent_messages      - Individual messages within a thread
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1bfdc13b6db1'
down_revision = 'b7407516626b'
branch_labels = None
depends_on = None


def upgrade():
    # parents -----------------------------------------------------------------
    op.create_table(
        'parents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column(
            'relationship_type',
            sa.Enum('Father', 'Mother', 'Guardian', name='relationship_types'),
            nullable=False,
        ),
        sa.Column('phone_primary', sa.String(length=20), nullable=False),
        sa.Column('phone_secondary', sa.String(length=20), nullable=True),
        sa.Column('occupation', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # student_parent (association table) --------------------------------------
    op.create_table(
        'student_parent',
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=False),
        sa.Column('is_primary_contact', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['parents.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('student_id', 'parent_id'),
    )

    # leave_applications ------------------------------------------------------
    op.create_table(
        'leave_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=False),
        sa.Column('from_date', sa.Date(), nullable=False),
        sa.Column('to_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column(
            'leave_type',
            sa.Enum('sick', 'family', 'personal', 'other', name='leave_types'),
            nullable=True,
        ),
        sa.Column(
            'status',
            sa.Enum('pending', 'approved', 'rejected', name='leave_status'),
            nullable=True,
        ),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewer_remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['parents.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('leave_applications', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_leave_applications_parent_id'), ['parent_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_leave_applications_status'), ['status'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_leave_applications_student_id'), ['student_id'], unique=False
        )

    # notifications -----------------------------------------------------------
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column(
            'type',
            sa.Enum(
                'absence', 'low_marks', 'fee_due', 'message', 'announcement',
                'leave_update', 'leave', 'general',
                name='notification_types',
            ),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_notifications_created_at'), ['created_at'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_notifications_is_read'), ['is_read'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False
        )

    # message_threads ---------------------------------------------------------
    op.create_table(
        'message_threads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=False),
        sa.Column('teacher_user_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_message_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['parents.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.ForeignKeyConstraint(['teacher_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('message_threads', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_message_threads_parent_id'), ['parent_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_message_threads_teacher_user_id'), ['teacher_user_id'], unique=False
        )

    # parent_messages ---------------------------------------------------------
    op.create_table(
        'parent_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(length=36), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['thread_id'], ['message_threads.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('parent_messages', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_parent_messages_thread_id'), ['thread_id'], unique=False
        )


def downgrade():
    with op.batch_alter_table('parent_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_parent_messages_thread_id'))
    op.drop_table('parent_messages')

    with op.batch_alter_table('message_threads', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_message_threads_teacher_user_id'))
        batch_op.drop_index(batch_op.f('ix_message_threads_parent_id'))
    op.drop_table('message_threads')

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notifications_user_id'))
        batch_op.drop_index(batch_op.f('ix_notifications_is_read'))
        batch_op.drop_index(batch_op.f('ix_notifications_created_at'))
    op.drop_table('notifications')

    with op.batch_alter_table('leave_applications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_leave_applications_student_id'))
        batch_op.drop_index(batch_op.f('ix_leave_applications_status'))
        batch_op.drop_index(batch_op.f('ix_leave_applications_parent_id'))
    op.drop_table('leave_applications')

    op.drop_table('student_parent')
    op.drop_table('parents')

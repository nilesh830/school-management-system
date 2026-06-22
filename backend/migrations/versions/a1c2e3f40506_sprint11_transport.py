"""sprint11_transport

Revision ID: a1c2e3f40506
Revises: c9a1f0e2b3d4
Create Date: 2026-06-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c2e3f40506'
down_revision = 'c9a1f0e2b3d4'
branch_labels = None
depends_on = None


def upgrade():
    # ### Transport routes (SMS-061) ###
    op.create_table('transport_routes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('stops_json', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # ### Transport vehicles (SMS-061) ###
    op.create_table('transport_vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_no', sa.String(length=20), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('driver_name', sa.String(length=100), nullable=True),
        sa.Column('driver_phone', sa.String(length=20), nullable=True),
        sa.Column('route_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['route_id'], ['transport_routes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('registration_no')
    )
    with op.batch_alter_table('transport_vehicles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_transport_vehicles_registration_no'), ['registration_no'], unique=True)
        batch_op.create_index(batch_op.f('ix_transport_vehicles_route_id'), ['route_id'], unique=False)

    # ### Student transport assignments (SMS-062) ###
    op.create_table('student_transport',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('pickup_stop', sa.String(length=100), nullable=True),
        sa.Column('drop_stop', sa.String(length=100), nullable=True),
        sa.Column('academic_year_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id'], ),
        sa.ForeignKeyConstraint(['route_id'], ['transport_routes.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'academic_year_id', name='uq_student_transport_student_year')
    )
    with op.batch_alter_table('student_transport', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_student_transport_academic_year_id'), ['academic_year_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_student_transport_route_id'), ['route_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_student_transport_student_id'), ['student_id'], unique=False)


def downgrade():
    with op.batch_alter_table('student_transport', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_student_transport_student_id'))
        batch_op.drop_index(batch_op.f('ix_student_transport_route_id'))
        batch_op.drop_index(batch_op.f('ix_student_transport_academic_year_id'))
    op.drop_table('student_transport')

    with op.batch_alter_table('transport_vehicles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_transport_vehicles_route_id'))
        batch_op.drop_index(batch_op.f('ix_transport_vehicles_registration_no'))
    op.drop_table('transport_vehicles')

    op.drop_table('transport_routes')

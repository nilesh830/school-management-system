"""fee applicability + transport optional fees (SMS-066, ADR-005 v1)

Adds the schema layer for optional/opt-in fees, transport-only for v1:

- fee_structures: ``applicability`` (mandatory|optional), ``source_kind``
  (flat|transport) and ``transport_route_id`` FK/index.
- transport_routes: ``fare`` and ``fare_frequency`` so a route carries a
  per-student, per-frequency fare.
- fee_records: ``amount_override`` for an admin-set per-student base amount.

All NOT NULL columns are added WITH a ``server_default`` so existing rows are
backfilled atomically by the DDL (no separate UPDATE pass) — existing rows land
on ``mandatory`` / ``flat`` / ``monthly``, reproducing today's behaviour exactly.
This is what makes the migration safe to fan out across every tenant schema via
``db-upgrade-all`` (batch_alter_table keeps it SQLite- and Postgres-friendly).

The generic ``student_fee_optin`` table is intentionally NOT created here
(deferred to v2 per ADR-005).

Revision ID: c4d5e6f70819
Revises: f3a9c1b2d4e7
Create Date: 2026-06-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d5e6f70819'
down_revision = 'f3a9c1b2d4e7'
branch_labels = None
depends_on = None


def upgrade():
    # ### fee_structures: applicability + source_kind + transport_route_id ###
    with op.batch_alter_table('fee_structures', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('applicability', sa.String(length=20), nullable=False, server_default='mandatory')
        )
        batch_op.add_column(
            sa.Column('source_kind', sa.String(length=20), nullable=False, server_default='flat')
        )
        batch_op.add_column(
            sa.Column('transport_route_id', sa.Integer(), nullable=True)
        )
        batch_op.create_check_constraint(
            'ck_fee_structures_applicability',
            "applicability IN ('mandatory','optional')",
        )
        batch_op.create_check_constraint(
            'ck_fee_structures_source_kind',
            "source_kind IN ('flat','transport')",
        )
        batch_op.create_foreign_key(
            'fk_fee_structures_transport_route',
            'transport_routes',
            ['transport_route_id'],
            ['id'],
        )
        batch_op.create_index(
            batch_op.f('ix_fee_structures_transport_route_id'),
            ['transport_route_id'],
            unique=False,
        )

    # NOTE: the server_default is intentionally KEPT (not dropped). During a
    # production rollout the schema may be migrated while the previous code is
    # still serving requests; without a DB-level default, that old code's INSERTs
    # (which omit these NOT NULL columns) would fail. The model also supplies a
    # Python default, so new code is unaffected. A later cleanup migration may drop
    # these server_defaults once all code is on the new version, if desired.

    # ### transport_routes: fare + fare_frequency ###
    with op.batch_alter_table('transport_routes', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('fare', sa.Numeric(precision=10, scale=2), nullable=True)
        )
        batch_op.add_column(
            sa.Column('fare_frequency', sa.String(length=20), nullable=False, server_default='monthly')
        )
        batch_op.create_check_constraint(
            'ck_transport_routes_fare_nonneg',
            "fare IS NULL OR fare >= 0",
        )
        batch_op.create_check_constraint(
            'ck_transport_routes_fare_frequency',
            "fare_frequency IN ('monthly','quarterly','annual','one_time')",
        )
        # server_default kept for fare_frequency (same rollout-safety reason as above).

    # ### fee_records: amount_override ###
    with op.batch_alter_table('fee_records', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('amount_override', sa.Numeric(precision=10, scale=2), nullable=True)
        )
        batch_op.create_check_constraint(
            'ck_fee_records_amount_override_nonneg',
            "amount_override IS NULL OR amount_override >= 0",
        )


def downgrade():
    # ### fee_records: amount_override ###
    with op.batch_alter_table('fee_records', schema=None) as batch_op:
        batch_op.drop_constraint('ck_fee_records_amount_override_nonneg', type_='check')
        batch_op.drop_column('amount_override')

    # ### transport_routes: fare + fare_frequency ###
    with op.batch_alter_table('transport_routes', schema=None) as batch_op:
        batch_op.drop_constraint('ck_transport_routes_fare_frequency', type_='check')
        batch_op.drop_constraint('ck_transport_routes_fare_nonneg', type_='check')
        batch_op.drop_column('fare_frequency')
        batch_op.drop_column('fare')

    # ### fee_structures: applicability + source_kind + transport_route_id ###
    with op.batch_alter_table('fee_structures', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fee_structures_transport_route_id'))
        batch_op.drop_constraint('fk_fee_structures_transport_route', type_='foreignkey')
        batch_op.drop_constraint('ck_fee_structures_source_kind', type_='check')
        batch_op.drop_constraint('ck_fee_structures_applicability', type_='check')
        batch_op.drop_column('transport_route_id')
        batch_op.drop_column('source_kind')
        batch_op.drop_column('applicability')

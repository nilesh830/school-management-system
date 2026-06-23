"""
ERP-008 — Custom Flask CLI commands for ERP multi-tenancy operations.
Register with register_commands(app) in create_app().
"""

import os
import sys
import click
from flask import current_app
from flask.cli import with_appcontext


def register_commands(app) -> None:
    app.cli.add_command(db_upgrade_all)
    app.cli.add_command(provision_school_cmd)


@click.command("db-upgrade-all")
@with_appcontext
def db_upgrade_all():
    """Run Alembic 'upgrade head' on every active school database."""
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine
    from app.models.master.school import School

    migrations_dir = os.path.abspath(os.path.join(current_app.root_path, "..", "migrations"))
    alembic_ini = os.path.join(migrations_dir, "alembic.ini")

    # Determine head revision once
    _cfg = AlembicConfig()
    _cfg.set_main_option("script_location", migrations_dir)
    head_rev = ScriptDirectory.from_config(_cfg).get_current_head()
    click.echo(f"Alembic head: {head_rev}\n")

    schools = School.query.filter_by(is_active=True).order_by(School.slug).all()
    if not schools:
        click.echo("No active schools found in master.db.")
        return

    errors = []

    for school in schools:
        click.echo(f"[{school.slug}] {school.name}")
        try:
            # Read current revision without running migrations
            engine = create_engine(school.db_url, connect_args={"check_same_thread": False})
            with engine.connect() as conn:
                current_rev = MigrationContext.configure(conn).get_current_revision()
            engine.dispose()

            if current_rev == head_rev:
                click.echo(f"  -> already at head ({(head_rev or '')[:12]})")
                continue

            click.echo(f"  current : {current_rev or 'none'}")
            click.echo(f"  target  : {(head_rev or '')[:12]}...")

            # Run upgrade via modified env.py (target_db_url override)
            cfg = AlembicConfig(alembic_ini)
            cfg.set_main_option("script_location", migrations_dir)
            cfg.attributes["target_db_url"] = school.db_url
            alembic_command.upgrade(cfg, "head")

            click.echo("  -> UPGRADED")

        except Exception as exc:
            msg = f"  -> ERROR: {exc}"
            click.echo(msg)
            errors.append(f"{school.slug}: {exc}")

    click.echo("")
    if errors:
        click.echo(f"Finished with {len(errors)} error(s):", err=True)
        for e in errors:
            click.echo(f"  x {e}", err=True)
        sys.exit(1)
    else:
        click.echo(f"All {len(schools)} school(s) are up to date.")


@click.command("provision-school")
@click.option("--slug", required=True, help="Unique school slug (e.g. greenwood-high)")
@click.option("--name", required=True, help="School display name")
@click.option("--admin-email", required=True, help="First admin user email")
@click.option("--admin-password", required=True, help="First admin user password (min 8 chars)")
@click.option("--address", default=None, help="School address (optional)")
@click.option("--phone", default=None, help="School phone (optional)")
@with_appcontext
def provision_school_cmd(slug, name, admin_email, admin_password, address, phone):
    """Provision a new school DB and seed the first admin user."""
    from app.services.superadmin_service import SuperAdminService

    result, error = SuperAdminService.provision_school(
        {
            "slug": slug,
            "name": name,
            "admin_email": admin_email,
            "admin_password": admin_password,
            "address": address,
            "phone": phone,
        }
    )

    if error:
        click.echo(f"Error ({error.get('status', 500)}): {error['message']}", err=True)
        sys.exit(1)

    # Fetch db_url directly from master DB (not exposed in to_dict for security)
    from app.models.master.school import School

    school_record = School.query.filter_by(slug=result["slug"]).first()
    db_url_display = school_record.db_url if school_record else "N/A"

    click.echo(f"School '{result['slug']}' provisioned.")
    click.echo(f"  DB  : {db_url_display}")
    click.echo(f"  Admin: {admin_email}")

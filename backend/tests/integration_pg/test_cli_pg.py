"""
PostgreSQL CLI tests (ERP-008) — provision-school and db-upgrade-all under the
schema-per-school model. Run against a real PostgreSQL DB.
"""
from app import db as _db


def _schema_for(slug: str) -> str:
    return f"school_{slug}".replace("-", "_")


class TestProvisionSchoolCmdPg:

    def test_provision_school_cmd_creates_schema(self, pg_app, schema_cleanup):
        slug = "pgcli-new"
        schema_cleanup.append(slug)

        runner = pg_app.test_cli_runner()
        result = runner.invoke(args=[
            "provision-school",
            "--slug", slug,
            "--name", "PG CLI New School",
            "--admin-email", "admin@pgcli-new.sms",
            "--admin-password", "CliAdmin@123",
            "--address", "1 CLI Street",
        ])

        assert result.exit_code == 0, result.output
        assert slug in result.output
        assert "provisioned" in result.output.lower()

        with pg_app.app_context():
            from app.models.master.school import School
            school = School.query.filter_by(slug=slug).first()
            assert school is not None
            assert school.name == "PG CLI New School"
            assert school.db_url == _schema_for(slug)  # column holds the schema name

            insp = _db.inspect(_db.engine)
            assert _schema_for(slug) in insp.get_schema_names()


class TestDbUpgradeAllPg:

    def test_upgrade_all_already_at_head(self, pg_app, schema_cleanup):
        """A freshly provisioned school is stamped at head, so db-upgrade-all
        reports it as already current."""
        slug = "pgcli-head"
        schema_cleanup.append(slug)

        runner = pg_app.test_cli_runner()
        prov = runner.invoke(args=[
            "provision-school",
            "--slug", slug,
            "--name", "PG CLI Head School",
            "--admin-email", "admin@pgcli-head.sms",
            "--admin-password", "CliAdmin@123",
        ])
        assert prov.exit_code == 0, prov.output

        result = runner.invoke(args=["db-upgrade-all"])
        assert result.exit_code == 0, result.output
        # The provisioned school's schema should be reported at head
        assert "already at head" in result.output
        assert slug in result.output

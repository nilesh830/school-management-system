"""Tests for ERP-008 CLI commands (db-upgrade-all, provision-school)."""
import pytest


class TestDbUpgradeAll:

    def test_upgrade_all_no_schools(self, app, db):
        """With no active schools, command exits cleanly."""
        # Ensure no active schools exist (clean_db fixture handles this between tests,
        # but test_school autouse fixture creates one with is_active=True — deactivate it)
        from app.models.master.school import School
        School.query.update({'is_active': False})
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(args=['db-upgrade-all'])
        assert result.exit_code == 0, result.output
        assert 'No active schools' in result.output

    def test_upgrade_all_invalid_schema_is_handled(self, app, db):
        """
        On the SQLite test engine the per-schema ``SET search_path`` is not
        supported, so processing any active school errors — the command must
        catch it and never raise an unhandled exception. (The happy-path
        'already at head' / upgrade behaviour is verified against PostgreSQL in
        tests/integration_pg/test_cli_pg.py.)
        """
        from app.models.master.school import School
        School.query.update({'is_active': False})
        school = School(
            name='Schema School',
            slug='cli-schema-test',
            db_url='school_cli_schema_test',
            is_active=True,
        )
        db.session.add(school)
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(args=['db-upgrade-all'])
        # exit_code 0 (nothing to do) or 1 (error logged but handled gracefully)
        assert result.exit_code in (0, 1)
        # Must not contain an unhandled Python traceback
        assert 'Traceback' not in result.output

    def test_upgrade_all_inactive_schools_skipped(self, app, db):
        """Inactive schools are not processed."""
        from app.models.master.school import School
        # Deactivate all schools including the autouse test_school
        School.query.update({'is_active': False})
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(args=['db-upgrade-all'])
        assert result.exit_code == 0, result.output
        assert 'No active schools' in result.output

    def test_upgrade_all_reports_error_count_on_failure(self, app, db):
        """When a school's schema cannot be processed, the error is reported and
        exit_code is 1 (on SQLite, SET search_path always fails — see note in
        test_upgrade_all_invalid_schema_is_handled)."""
        from app.models.master.school import School
        School.query.update({'is_active': False})
        school = School(
            name='Bad DB School',
            slug='cli-bad-db',
            db_url='school_cli_bad_db',
            is_active=True,
        )
        db.session.add(school)
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(args=['db-upgrade-all'])
        assert result.exit_code == 1
        # The slug must appear in the error summary (written to stderr)
        assert 'cli-bad-db' in result.output or 'cli-bad-db' in (result.stderr or '')


class TestProvisionSchoolCmd:

    def test_provision_school_missing_required_options(self, app):
        """Missing --slug exits non-zero (Click enforces required options)."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'provision-school',
            '--name', 'X',
            '--admin-email', 'a@b.com',
            '--admin-password', 'Pass@1234',
        ])
        assert result.exit_code != 0

    def test_provision_school_missing_name(self, app):
        """Missing --name exits non-zero."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'provision-school',
            '--slug', 'test-missing-name',
            '--admin-email', 'a@b.com',
            '--admin-password', 'Pass@1234',
        ])
        assert result.exit_code != 0

    def test_provision_school_missing_admin_email(self, app):
        """Missing --admin-email exits non-zero."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'provision-school',
            '--slug', 'test-missing-email',
            '--name', 'Missing Email School',
            '--admin-password', 'Pass@1234',
        ])
        assert result.exit_code != 0

    def test_provision_school_duplicate_slug(self, app, db):
        """Duplicate slug results in non-zero exit and an error message."""
        from app.models.master.school import School
        existing = School(
            name='Existing School',
            slug='dup-slug-cli',
            db_url='sqlite:///:memory:',
            is_active=True,
        )
        db.session.add(existing)
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'provision-school',
            '--slug', 'dup-slug-cli',
            '--name', 'Duplicate School',
            '--admin-email', 'admin@dup.com',
            '--admin-password', 'Admin@1234',
        ])
        assert result.exit_code != 0
        combined = result.output + (result.stderr or '')
        assert 'already taken' in combined.lower() or 'error' in combined.lower()

    # NOTE: the happy-path provision-school command (which creates a PostgreSQL
    # schema) is verified in tests/integration_pg/test_cli_pg.py.

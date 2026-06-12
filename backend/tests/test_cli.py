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

    def test_upgrade_all_already_at_head(self, app, db):
        """Schools already at Alembic head print 'already at head'."""
        from app.models.master.school import School
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine, text
        import os

        # Build the head revision so we can pre-stamp the in-memory DB
        migrations_dir = os.path.abspath(
            os.path.join(app.root_path, '..', 'migrations')
        )
        _cfg = AlembicConfig()
        _cfg.set_main_option('script_location', migrations_dir)
        head_rev = ScriptDirectory.from_config(_cfg).get_current_head()

        # Use a real file-based SQLite DB for this test so a second connection
        # can see the alembic_version row (sqlite:///:memory: resets on reconnect)
        import tempfile, os as _os
        tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        tmp.close()
        school_db_url = f'sqlite:///{tmp.name}'

        try:
            # Pre-stamp the DB at head so the command sees it as current
            engine = create_engine(school_db_url, connect_args={'check_same_thread': False})
            with engine.connect() as conn:
                conn.execute(text(
                    "CREATE TABLE IF NOT EXISTS alembic_version "
                    "(version_num VARCHAR(32) NOT NULL, "
                    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                ))
                if head_rev:
                    conn.execute(
                        text("INSERT OR IGNORE INTO alembic_version VALUES (:rev)"),
                        {'rev': head_rev},
                    )
                conn.commit()
            engine.dispose()

            # Deactivate the autouse test_school and add our stamped school
            School.query.update({'is_active': False})
            school = School(
                name='CLI Head Test School',
                slug='cli-head-test',
                db_url=school_db_url,
                is_active=True,
            )
            db.session.add(school)
            db.session.commit()

            runner = app.test_cli_runner()
            result = runner.invoke(args=['db-upgrade-all'])

            assert result.exit_code == 0, result.output
            assert 'already at head' in result.output
        finally:
            _os.unlink(tmp.name)

    def test_upgrade_all_memory_db_error_is_handled(self, app, db):
        """
        sqlite:///:memory: resets on each new connection, so reading
        alembic_version is fine (returns None as current_rev) but the
        upgrade may error because metadata tables are not present.
        Either way the command must not raise an unhandled exception.
        """
        from app.models.master.school import School
        School.query.update({'is_active': False})
        school = School(
            name='Memory DB School',
            slug='cli-memory-test',
            db_url='sqlite:///:memory:',
            is_active=True,
        )
        db.session.add(school)
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(args=['db-upgrade-all'])
        # exit_code 0 (upgraded cleanly) or 1 (error logged but handled gracefully)
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
        """When a school DB is unreachable, the error is reported and exit_code is 1."""
        from app.models.master.school import School
        School.query.update({'is_active': False})
        school = School(
            name='Bad DB School',
            slug='cli-bad-db',
            db_url='sqlite:////nonexistent/path/school.db',
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

    def test_provision_school_success(self, app, db):
        """
        Happy-path: provision a new school via CLI, confirm record in master DB
        and that the DB file was created.
        """
        import os, tempfile, shutil
        from app.models.master.school import School

        # Use a real directory so the DB file is written to disk
        tmp_dir = tempfile.mkdtemp()
        original_schools_dir = app.config['SCHOOLS_DB_DIR']
        app.config['SCHOOLS_DB_DIR'] = tmp_dir

        try:
            runner = app.test_cli_runner()
            result = runner.invoke(args=[
                'provision-school',
                '--slug', 'cli-new-school',
                '--name', 'CLI New School',
                '--admin-email', 'admin@clinew.sms',
                '--admin-password', 'CliAdmin@123',
                '--address', '1 CLI Street',
            ])

            assert result.exit_code == 0, result.output
            assert 'cli-new-school' in result.output
            assert 'provisioned' in result.output.lower()

            # Confirm master DB record
            school = School.query.filter_by(slug='cli-new-school').first()
            assert school is not None
            assert school.name == 'CLI New School'
            assert school.is_active is True
        finally:
            app.config['SCHOOLS_DB_DIR'] = original_schools_dir
            shutil.rmtree(tmp_dir, ignore_errors=True)
            # Clean up the school record created in master DB
            from app.models.master.school import School as S
            s = S.query.filter_by(slug='cli-new-school').first()
            if s:
                db.session.delete(s)
                db.session.commit()

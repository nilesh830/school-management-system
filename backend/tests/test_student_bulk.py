"""
Bulk student registration tests.

Covers:
  - generate_temp_password satisfies the password strength rule
  - parse_xlsx round-trips an uploaded workbook
  - /students/bulk/template  → downloadable .xlsx
  - /students/bulk/preview   → validation + duplicate/error flagging (no writes)
  - /students/bulk/commit    → partial success, login accounts, email queued
  - /school/email-config     → GET/PUT (password never exposed)
  - role guard (teacher forbidden)
"""

import io
from datetime import date

import pytest

from app import db as _db
from app.models.student import Student
from app.models.user import User
from app.utils.excel import build_xlsx, parse_xlsx, STUDENT_IMPORT_COLUMNS
from app.utils.validators import generate_temp_password, validate_password


def auth(token):
    return {"Authorization": f"Bearer {token}"}


_KEYS = [c["key"] for c in STUDENT_IMPORT_COLUMNS]
_HEADERS = [c["label"] for c in STUDENT_IMPORT_COLUMNS]


def make_xlsx(rows):
    """Build an .xlsx (in column order) from a list of dicts → BytesIO."""
    data = [[r.get(k, "") for k in _KEYS] for r in rows]
    return io.BytesIO(build_xlsx("Students", _HEADERS, data))


def row(first, last, adm_no, **extra):
    base = {
        "first_name": first,
        "last_name": last,
        "date_of_birth": "2012-05-14",
        "gender": "Male",
        "admission_date": "2024-06-01",
        "admission_no": adm_no,
    }
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Unit — temp password + xlsx parsing
# ---------------------------------------------------------------------------

class TestTempPassword:
    def test_generated_password_passes_strength_rule(self):
        for _ in range(50):
            pw = generate_temp_password()
            assert validate_password(pw) == [], f"weak password generated: {pw}"
            assert len(pw) >= 8

    def test_length_respected(self):
        assert len(generate_temp_password(16)) == 16
        # Never shorter than 8 even if asked.
        assert len(generate_temp_password(4)) == 8


class TestParseXlsx:
    def test_roundtrip(self):
        bio = make_xlsx([row("Alice", "Johnson", "ADM-1", email="alice@x.com", section_id=3)])
        parsed = parse_xlsx(bio)
        assert len(parsed) == 1
        r = parsed[0]
        assert r["first_name"] == "Alice"
        assert r["admission_no"] == "ADM-1"
        assert r["email"] == "alice@x.com"
        assert r["section_id"] == 3
        assert r["_row"] == 2  # header is row 1

    def test_blank_rows_skipped(self):
        bio = make_xlsx([row("A", "B", "ADM-1"), {}, row("C", "D", "ADM-2")])
        parsed = parse_xlsx(bio)
        assert len(parsed) == 2

    def test_empty_workbook_raises(self):
        empty = io.BytesIO(build_xlsx("Students", _HEADERS, []))
        # Only a header row → no data rows → returns empty list (not an error).
        assert parse_xlsx(empty) == []


# ---------------------------------------------------------------------------
# Template download
# ---------------------------------------------------------------------------

class TestTemplate:
    def test_download_template(self, client, admin_token):
        resp = client.get("/api/v1/students/bulk/template", headers=auth(admin_token))
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["Content-Type"]
        assert resp.headers["Content-Disposition"].endswith(".xlsx")
        assert resp.data[:2] == b"PK"  # xlsx is a zip

    def test_template_includes_section_reference(self, client, admin_token, db):
        from app.models.class_ import Class
        from app.models.section import Section
        from openpyxl import load_workbook

        cls = Class(name="Grade 5", grade_level=5)
        db.session.add(cls)
        db.session.flush()
        sec = Section(name="A", class_id=cls.id, capacity=30)
        db.session.add(sec)
        db.session.commit()

        resp = client.get("/api/v1/students/bulk/template", headers=auth(admin_token))
        wb = load_workbook(io.BytesIO(resp.data))
        assert "Sections" in wb.sheetnames
        ref_rows = list(wb["Sections"].iter_rows(values_only=True))
        # header + at least our one section
        assert ref_rows[0] == ("Section ID", "Section", "Class", "Capacity")
        assert any(r[0] == sec.id and r[1] == "Grade 5 — A" for r in ref_rows[1:])


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

class TestPreview:
    def _upload(self, client, token, rows):
        return client.post(
            "/api/v1/students/bulk/preview",
            data={"file": (make_xlsx(rows), "students.xlsx")},
            content_type="multipart/form-data",
            headers=auth(token),
        )

    def test_valid_rows(self, client, admin_token):
        resp = self._upload(client, admin_token, [
            row("Alice", "Johnson", "ADM-P1"),
            row("Bob", "Smith", "ADM-P2"),
        ])
        assert resp.status_code == 200
        summary = resp.get_json()["data"]["summary"]
        assert summary["total"] == 2
        assert summary["valid"] == 2
        assert summary["error"] == 0

    def test_missing_required_field_flagged(self, client, admin_token):
        bad = row("", "NoName", "ADM-P3")  # empty first_name
        resp = self._upload(client, admin_token, [bad])
        data = resp.get_json()["data"]
        assert data["summary"]["error"] == 1
        assert data["rows"][0]["status"] == "error"
        assert "first_name" in data["rows"][0]["errors"]

    def test_in_file_duplicate_admission_flagged(self, client, admin_token):
        resp = self._upload(client, admin_token, [
            row("A", "One", "DUP-1"),
            row("B", "Two", "DUP-1"),
        ])
        data = resp.get_json()["data"]
        assert data["summary"]["valid"] == 1
        assert data["summary"]["duplicate"] == 1

    def test_existing_admission_flagged(self, client, admin_token, db):
        s = Student(admission_no="EXISTS-1", first_name="X", last_name="Y",
                    date_of_birth=date(2010, 1, 1), gender="Male", admission_date=date(2024, 6, 1))
        db.session.add(s)
        db.session.commit()
        resp = self._upload(client, admin_token, [row("A", "B", "EXISTS-1")])
        data = resp.get_json()["data"]
        assert data["summary"]["duplicate"] == 1

    def test_preview_writes_nothing(self, client, admin_token, db):
        self._upload(client, admin_token, [row("Ghost", "Row", "ADM-NOWRITE")])
        assert db.session.query(Student).filter_by(admission_no="ADM-NOWRITE").first() is None

    def test_teacher_forbidden(self, client, teacher_token):
        resp = self._upload(client, teacher_token, [row("A", "B", "ADM-X")])
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

class TestCommit:
    def _commit(self, client, token, rows):
        return client.post(
            "/api/v1/students/bulk/commit",
            json={"rows": rows},
            headers=auth(token),
        )

    def test_commit_creates_students(self, client, admin_token, db):
        resp = self._commit(client, admin_token, [
            row("Alice", "Johnson", "ADM-C1"),
            row("Bob", "Smith", "ADM-C2"),
        ])
        assert resp.status_code == 201
        summary = resp.get_json()["data"]["summary"]
        assert summary["created"] == 2
        assert db.session.query(Student).filter_by(admission_no="ADM-C1").first() is not None
        assert db.session.query(Student).filter_by(admission_no="ADM-C2").first() is not None

    def test_partial_success(self, client, admin_token, db):
        resp = self._commit(client, admin_token, [
            row("Good", "One", "ADM-OK"),
            row("", "Bad", "ADM-BAD"),            # invalid: empty first_name
            row("Good", "Two", "ADM-OK2"),
        ])
        summary = resp.get_json()["data"]["summary"]
        assert summary["created"] == 2
        assert summary["error"] == 1
        # Good rows persisted despite the bad one in the middle.
        assert db.session.query(Student).filter_by(admission_no="ADM-OK").first() is not None
        assert db.session.query(Student).filter_by(admission_no="ADM-OK2").first() is not None
        assert db.session.query(Student).filter_by(admission_no="ADM-BAD").first() is None

    def test_commit_creates_login_and_queues_email(self, client, admin_token, db):
        resp = self._commit(client, admin_token, [
            row("Login", "Kid", "ADM-LOGIN", email="loginkid@example.com"),
            row("NoLogin", "Kid", "ADM-NOLOGIN"),
        ])
        body = resp.get_json()["data"]
        assert body["summary"]["created"] == 2
        # Login account created for the row that supplied an email.
        user = db.session.query(User).filter_by(email="loginkid@example.com").first()
        assert user is not None
        assert user.role == "student"
        student = db.session.query(Student).filter_by(admission_no="ADM-LOGIN").first()
        assert student.user_id == user.id
        # The other student has no login.
        nologin = db.session.query(Student).filter_by(admission_no="ADM-NOLOGIN").first()
        assert nologin.user_id is None
        # One credential email queued.
        assert body["emails"]["with_login"] == 1

    def test_commit_rescreens_duplicates(self, client, admin_token, db):
        # Pre-existing student; client tries to re-import the same admission_no.
        s = Student(admission_no="ADM-RE", first_name="X", last_name="Y",
                    date_of_birth=date(2010, 1, 1), gender="Male", admission_date=date(2024, 6, 1))
        db.session.add(s)
        db.session.commit()
        resp = self._commit(client, admin_token, [row("A", "B", "ADM-RE")])
        summary = resp.get_json()["data"]["summary"]
        assert summary["created"] == 0
        assert summary["duplicate"] == 1

    def test_empty_rows_rejected(self, client, admin_token):
        resp = self._commit(client, admin_token, [])
        assert resp.status_code == 400

    def test_teacher_forbidden(self, client, teacher_token):
        resp = self._commit(client, teacher_token, [row("A", "B", "ADM-Z")])
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Email config settings
# ---------------------------------------------------------------------------

class TestEmailConfig:
    def test_get_when_unset(self, client, admin_token):
        resp = client.get("/api/v1/school/email-config", headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()["data"] is None

    def test_put_then_get(self, client, admin_token):
        put = client.put("/api/v1/school/email-config", headers=auth(admin_token), json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "mailer@example.com",
            "smtp_password": "SuperSecret1!",
            "from_email": "school@example.com",
            "from_name": "Test School",
        })
        assert put.status_code == 200
        # Password must never be echoed back.
        assert "smtp_password" not in put.get_json()["data"]
        assert put.get_json()["data"]["smtp_password_set"] is True

        got = client.get("/api/v1/school/email-config", headers=auth(admin_token)).get_json()["data"]
        assert got["smtp_host"] == "smtp.example.com"
        assert got["from_email"] == "school@example.com"

    def test_put_missing_fields(self, client, admin_token):
        resp = client.put("/api/v1/school/email-config", headers=auth(admin_token), json={
            "smtp_host": "smtp.example.com",
        })
        assert resp.status_code == 422

    def test_teacher_forbidden(self, client, teacher_token):
        resp = client.get("/api/v1/school/email-config", headers=auth(teacher_token))
        assert resp.status_code == 403

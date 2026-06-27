"""
Create a current Academic Year for a school.

The admin UI has no screen to create an academic year, but Fee Structures and
Transport Assignments require one. Run this ONCE per school right after you
provision it, before demoing Fees / Transport.

Usage (from the backend/ directory, with the venv active):
    python database/seeds/seed_academic_year.py <school_slug>
    e.g.  python database/seeds/seed_academic_year.py sunrise

If no slug is given it defaults to 'demo'.
"""
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import create_app  # noqa: E402
from app.models.master.school import School  # noqa: E402
from app.models.academic_year import AcademicYear  # noqa: E402
from app.utils.tenant import _open_tenant_session  # noqa: E402


def seed_academic_year(slug: str = "demo", name: str = "2025-2026"):
    app = create_app()
    with app.app_context():
        school = School.query.filter_by(slug=slug).first()
        if not school:
            print(f"[ERROR] No school found with slug '{slug}'. Provision it first in the Super Admin portal.")
            return

        # school.db_url holds the school's PostgreSQL schema name
        session, connection = _open_tenant_session(school.db_url)
        try:
            existing = session.query(AcademicYear).filter_by(is_current=True).first()
            if existing:
                print(f"[OK] Current academic year already exists for '{slug}': {existing.name} (id={existing.id})")
                return

            ay = AcademicYear(
                name=name,
                start_date=date(2025, 6, 1),
                end_date=date(2026, 5, 31),
                is_current=True,
                is_active=True,
            )
            session.add(ay)
            session.commit()
            print(f"[OK] Created academic year '{name}' (id={ay.id}) for school '{slug}'.")
        finally:
            session.close()
            connection.close()


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "demo"
    seed_academic_year(slug)

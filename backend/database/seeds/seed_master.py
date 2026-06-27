"""
Seed the master tables (public schema) with:
  - One default super admin (superadmin@sms.com / SuperAdmin@1234)
  - One demo school provisioned into its own PostgreSQL schema (school_demo),
    with a first admin user (admin@demo.sms / Admin@1234)

For a full-featured demo, prefer provisioning a FRESH school via the Super Admin
portal (see DEMO_GUIDE.md) — this seed just guarantees a working super admin and
one minimal school so you can log in immediately after migrating.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db, bcrypt
from app.models.master.school import School
from app.models.master.super_admin import SuperAdmin
from app.services.superadmin_service import SuperAdminService


def seed_master():
    app = create_app()
    with app.app_context():
        # Super admin (lives in the public schema alongside the schools registry)
        if not SuperAdmin.query.filter_by(email='superadmin@sms.com').first():
            sa = SuperAdmin(
                email='superadmin@sms.com',
                password_hash=bcrypt.generate_password_hash('SuperAdmin@1234').decode('utf-8'),
                first_name='Super',
                last_name='Admin',
            )
            db.session.add(sa)
            db.session.commit()
            print('Created super admin: superadmin@sms.com / SuperAdmin@1234')
        else:
            print('Super admin already exists, skipping.')

        # Demo school — provisioned into its own schema (school_demo) with an admin
        if not School.query.filter_by(slug='demo').first():
            result, error = SuperAdminService.provision_school({
                'name': 'Demo School',
                'slug': 'demo',
                'email': 'admin@demo.sms',
                'phone': '0000000000',
                'admin_email': 'admin@demo.sms',
                'admin_password': 'Admin@1234',
                'admin_first_name': 'Demo',
                'admin_last_name': 'Admin',
            })
            if error:
                print(f"Failed to provision demo school: {error['message']}")
                sys.exit(1)
            print('Created demo school: slug=demo, schema=school_demo')
            print('  School admin: admin@demo.sms / Admin@1234 (login slug: demo)')
        else:
            print('Demo school already exists, skipping.')

        print('Master DB seeded successfully.')


if __name__ == '__main__':
    seed_master()

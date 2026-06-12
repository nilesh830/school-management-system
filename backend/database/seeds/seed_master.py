"""
Seed the master database with:
  - One default super admin (superadmin@sms.com / SuperAdmin@1234)
  - One demo school pointing to the existing school_demo.db
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db, bcrypt
from app.models.master.school import School
from app.models.master.super_admin import SuperAdmin


def seed_master():
    app = create_app()
    with app.app_context():
        # Super admin
        if not SuperAdmin.query.filter_by(email='superadmin@sms.com').first():
            sa = SuperAdmin(
                email='superadmin@sms.com',
                password_hash=bcrypt.generate_password_hash('SuperAdmin@1234').decode('utf-8'),
                first_name='Super',
                last_name='Admin',
            )
            db.session.add(sa)
            print('Created super admin: superadmin@sms.com / SuperAdmin@1234')
        else:
            print('Super admin already exists, skipping.')

        # Demo school
        schools_dir = app.config['SCHOOLS_DB_DIR']
        demo_db_path = os.path.join(schools_dir, 'school_demo.db').replace(os.sep, '/')
        demo_db_url = f'sqlite:///{demo_db_path}'
        if not School.query.filter_by(slug='demo').first():
            school = School(
                name='Demo School',
                slug='demo',
                db_url=demo_db_url,
                email='admin@demo.sms',
                phone='0000000000',
            )
            db.session.add(school)
            print(f'Created demo school: slug=demo, db_url={demo_db_url}')
        else:
            print('Demo school already exists, skipping.')

        db.session.commit()
        print('Master DB seeded successfully.')


if __name__ == '__main__':
    seed_master()

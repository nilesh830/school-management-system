"""
Seed the database with realistic sample data for development.

Usage (from the backend/ directory):
    python -m database.seeds.seed_all

Or from project root:
    cd backend && python ../database/seeds/seed_all.py
"""
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from datetime import date, timedelta
from app import create_app, db
from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent, student_parent
from app.models.leave_application import LeaveApplication
from app.models.notification import Notification


def seed_users():
    users_data = [
        # Admin
        dict(
            email='admin@school.sms',
            role='admin',
            first_name='Rahul',
            last_name='Verma',
            password='Admin@1234',
        ),
        # Teachers
        dict(
            email='priya.sharma@school.sms',
            role='teacher',
            first_name='Priya',
            last_name='Sharma',
            password='Teacher@123',
        ),
        dict(
            email='amit.singh@school.sms',
            role='teacher',
            first_name='Amit',
            last_name='Singh',
            password='Teacher@123',
        ),
        # Students (users only; full student profiles seeded separately)
        dict(
            email='alice.johnson@school.sms',
            role='student',
            first_name='Alice',
            last_name='Johnson',
            password='Student@123',
        ),
        dict(
            email='bob.williams@school.sms',
            role='student',
            first_name='Bob',
            last_name='Williams',
            password='Student@123',
        ),
        dict(
            email='carol.smith@school.sms',
            role='student',
            first_name='Carol',
            last_name='Smith',
            password='Student@123',
        ),
        # Parents
        dict(
            email='robert.johnson@parents.school.sms',
            role='parent',
            first_name='Robert',
            last_name='Johnson',
            password='Parent@123',
        ),
        dict(
            email='sandra.williams@parents.school.sms',
            role='parent',
            first_name='Sandra',
            last_name='Williams',
            password='Parent@123',
        ),
    ]

    created = {}
    for u in users_data:
        if User.query.filter_by(email=u['email']).first():
            print(f"  [skip] User already exists: {u['email']}")
            created[u['email']] = User.query.filter_by(email=u['email']).first()
            continue
        user = User(
            email=u['email'],
            role=u['role'],
            first_name=u['first_name'],
            last_name=u['last_name'],
        )
        user.set_password(u['password'])
        db.session.add(user)
        db.session.flush()
        created[u['email']] = user
        print(f"  [ok]   Created user: {u['email']} ({u['role']})")

    db.session.flush()
    return created


def seed_students(users):
    students_data = [
        dict(
            email='alice.johnson@school.sms',
            admission_no='ADM2024001',
            first_name='Alice',
            last_name='Johnson',
            date_of_birth=date(2012, 3, 15),
            gender='Female',
            admission_date=date(2024, 6, 1),
            blood_group='A+',
            address='12, MG Road, Mumbai, Maharashtra 400001',
            phone='9876543210',
        ),
        dict(
            email='bob.williams@school.sms',
            admission_no='ADM2024002',
            first_name='Bob',
            last_name='Williams',
            date_of_birth=date(2011, 7, 22),
            gender='Male',
            admission_date=date(2024, 6, 1),
            blood_group='O+',
            address='45, Bandra West, Mumbai, Maharashtra 400050',
            phone='9123456789',
        ),
        dict(
            email='carol.smith@school.sms',
            admission_no='ADM2024003',
            first_name='Carol',
            last_name='Smith',
            date_of_birth=date(2013, 11, 8),
            gender='Female',
            admission_date=date(2024, 6, 1),
            blood_group='B+',
            address='78, Andheri East, Mumbai, Maharashtra 400069',
            phone='9012345678',
        ),
    ]

    created = {}
    for s in students_data:
        user = users.get(s['email'])
        if not user:
            print(f"  [skip] No user for student: {s['email']}")
            continue
        if Student.query.filter_by(admission_no=s['admission_no']).first():
            print(f"  [skip] Student already exists: {s['admission_no']}")
            created[s['admission_no']] = Student.query.filter_by(admission_no=s['admission_no']).first()
            continue
        student = Student(
            user_id=user.id,
            admission_no=s['admission_no'],
            first_name=s['first_name'],
            last_name=s['last_name'],
            date_of_birth=s['date_of_birth'],
            gender=s['gender'],
            admission_date=s['admission_date'],
            blood_group=s.get('blood_group'),
            address=s.get('address'),
            phone=s.get('phone'),
        )
        db.session.add(student)
        db.session.flush()
        created[s['admission_no']] = student
        print(f"  [ok]   Created student: {s['admission_no']} — {s['first_name']} {s['last_name']}")

    db.session.flush()
    return created


def seed_parents(users):
    parents_data = [
        dict(
            email='robert.johnson@parents.school.sms',
            relationship_type='Father',
            phone_primary='+91-9988776655',
            phone_secondary='+91-9900112233',
            occupation='Software Engineer',
            address='12, MG Road, Mumbai, Maharashtra 400001',
        ),
        dict(
            email='sandra.williams@parents.school.sms',
            relationship_type='Mother',
            phone_primary='+91-9776655443',
            occupation='Nurse',
            address='45, Bandra West, Mumbai, Maharashtra 400050',
        ),
    ]

    created = {}
    for p in parents_data:
        user = users.get(p['email'])
        if not user:
            print(f"  [skip] No user for parent: {p['email']}")
            continue
        if Parent.query.filter_by(user_id=user.id).first():
            print(f"  [skip] Parent profile already exists for: {p['email']}")
            created[p['email']] = Parent.query.filter_by(user_id=user.id).first()
            continue
        parent = Parent(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            relationship_type=p['relationship_type'],
            phone_primary=p['phone_primary'],
            phone_secondary=p.get('phone_secondary'),
            occupation=p.get('occupation'),
            address=p.get('address'),
        )
        db.session.add(parent)
        db.session.flush()
        created[p['email']] = parent
        print(f"  [ok]   Created parent: {user.first_name} {user.last_name} ({p['relationship_type']})")

    db.session.flush()
    return created


def seed_parent_links(students, parents):
    """Link parents to their children via student_parent association."""
    links = [
        # Robert Johnson is Alice's father
        dict(student_no='ADM2024001', parent_email='robert.johnson@parents.school.sms', is_primary=True),
        # Sandra Williams is Bob's mother
        dict(student_no='ADM2024002', parent_email='sandra.williams@parents.school.sms', is_primary=True),
        # Carol has no parent in the system yet (intentional — edge case)
    ]

    for link in links:
        student = students.get(link['student_no'])
        parent = parents.get(link['parent_email'])
        if not student or not parent:
            print(f"  [skip] Missing student or parent for link: {link}")
            continue

        existing = db.session.execute(
            student_parent.select().where(
                (student_parent.c.student_id == student.id) &
                (student_parent.c.parent_id == parent.id)
            )
        ).first()

        if existing:
            print(f"  [skip] Link already exists: {link['student_no']} <-> {link['parent_email']}")
            continue

        db.session.execute(
            student_parent.insert().values(
                student_id=student.id,
                parent_id=parent.id,
                is_primary_contact=link['is_primary'],
            )
        )
        print(f"  [ok]   Linked student {link['student_no']} to parent {link['parent_email']}")


def seed_leave_applications(students, users):
    """Seed a couple of leave applications for realistic demo data."""
    alice = students.get('ADM2024001')
    bob = students.get('ADM2024002')

    parent_alice = users.get('robert.johnson@parents.school.sms')
    parent_bob = users.get('sandra.williams@parents.school.sms')

    if not alice or not parent_alice:
        return

    parent_alice_profile = Parent.query.filter_by(user_id=parent_alice.id).first()
    parent_bob_profile = Parent.query.filter_by(user_id=parent_bob.id).first() if parent_bob else None

    today = date.today()
    leaves = []

    if alice and parent_alice_profile:
        leaves.append(LeaveApplication(
            student_id=alice.id,
            parent_id=parent_alice_profile.id,
            from_date=today + timedelta(days=7),
            to_date=today + timedelta(days=7),
            leave_type='sick',
            reason='Doctor appointment for annual check-up',
            status='pending',
        ))

    if bob and parent_bob_profile:
        leaves.append(LeaveApplication(
            student_id=bob.id,
            parent_id=parent_bob_profile.id,
            from_date=today - timedelta(days=3),
            to_date=today - timedelta(days=2),
            leave_type='family',
            reason='Family wedding ceremony out of town',
            status='approved',
        ))

    for leave in leaves:
        if not LeaveApplication.query.filter_by(
            student_id=leave.student_id,
            from_date=leave.from_date
        ).first():
            db.session.add(leave)
            print(f"  [ok]   Created leave application: student_id={leave.student_id} ({leave.leave_type})")
        else:
            print(f"  [skip] Leave application already exists for student_id={leave.student_id}")


def seed_notifications(users):
    """Seed sample notifications."""
    parent_alice = users.get('robert.johnson@parents.school.sms')
    if not parent_alice:
        return

    if Notification.query.filter_by(user_id=parent_alice.id).first():
        print(f"  [skip] Notifications already exist for: {parent_alice.email}")
        return

    notifications = [
        Notification(
            user_id=parent_alice.id,
            type='announcement',
            title='School Annual Day 2024',
            body='Annual Day function scheduled on 25th December. All parents are invited.',
            is_read=False,
        ),
        Notification(
            user_id=parent_alice.id,
            type='fee_due',
            title='Term 2 Fees Reminder',
            body='Term 2 fees of ₹15,000 are due by 15th July 2024. Please pay to avoid late charges.',
            is_read=True,
        ),
    ]
    for n in notifications:
        db.session.add(n)
    print(f"  [ok]   Created {len(notifications)} notifications for {parent_alice.email}")


def run():
    app = create_app('development')
    with app.app_context():
        print("\n=== SMS Seed Data ===\n")

        print("[1/6] Seeding users...")
        users = seed_users()

        print("\n[2/6] Seeding student profiles...")
        students = seed_students(users)

        print("\n[3/6] Seeding parent profiles...")
        parents = seed_parents(users)

        print("\n[4/6] Linking parents to students...")
        seed_parent_links(students, parents)

        print("\n[5/6] Seeding leave applications...")
        seed_leave_applications(students, users)

        print("\n[6/6] Seeding notifications...")
        seed_notifications(users)

        db.session.commit()
        print("\n=== Seed complete! ===\n")
        print("Test credentials:")
        print("  Admin:   admin@school.sms       / Admin@1234")
        print("  Teacher: priya.sharma@school.sms / Teacher@123")
        print("  Student: alice.johnson@school.sms / Student@123")
        print("  Parent:  robert.johnson@parents.school.sms / Parent@123")


if __name__ == '__main__':
    run()

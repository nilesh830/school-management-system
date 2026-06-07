import pytest
from datetime import date
from app import create_app, db as _db
from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent, student_parent


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='session')
def db(app):
    return _db


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function', autouse=True)
def clean_db(db):
    """Wipe all rows between tests while keeping schema intact."""
    yield
    db.session.remove()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


# ── Reusable user factory fixtures ──────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    u = User(email='admin@test.sms', role='admin', first_name='Admin', last_name='Test')
    u.set_password('Admin@1234')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def teacher_user(db):
    u = User(email='teacher@test.sms', role='teacher', first_name='Priya', last_name='Sharma')
    u.set_password('Teacher@123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def student_user(db):
    u = User(email='alice@test.sms', role='student', first_name='Alice', last_name='Johnson')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def parent_user(db, student_user):
    u = User(email='robert@test.sms', role='parent', first_name='Robert', last_name='Johnson')
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()

    parent = Parent(
        user_id=u.id,
        first_name='Robert',
        last_name='Johnson',
        relationship_type='Father',
        phone_primary='+91-9988776655',
    )
    db.session.add(parent)
    db.session.flush()

    student = Student(
        user_id=student_user.id,
        admission_no='ADM-TEST-001',
        first_name='Alice',
        last_name='Johnson',
        date_of_birth=date(2012, 3, 15),
        gender='Female',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(student)
    db.session.flush()

    db.session.execute(
        student_parent.insert().values(
            student_id=student.id,
            parent_id=parent.id,
            is_primary_contact=True,
        )
    )
    db.session.commit()
    return u


# ── Auth token helpers ───────────────────────────────────────────────────────

def _login(client, email, password):
    resp = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    return resp.get_json()['data']


@pytest.fixture
def admin_token(client, admin_user):
    return _login(client, 'admin@test.sms', 'Admin@1234')['access_token']


@pytest.fixture
def teacher_token(client, teacher_user):
    return _login(client, 'teacher@test.sms', 'Teacher@123')['access_token']


@pytest.fixture
def parent_token(client, parent_user):
    return _login(client, 'robert@test.sms', 'Parent@123')['access_token']


@pytest.fixture
def refresh_token_for_admin(client, admin_user):
    return _login(client, 'admin@test.sms', 'Admin@1234')['refresh_token']

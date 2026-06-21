"""
Sprint 9 — Library Management
Covers:
  - SMS-053: book catalog (create, list+search, update, delete-blocked)
  - SMS-054: issue & return (issue, return on time, return late w/ fine, no copies 409)
  - SMS-055: overdue fines (mark overdue, fine per day, overdue endpoint)
"""
from datetime import date, timedelta

from app.models.user import User
from app.models.student import Student


_counter = 0


def _uid():
    global _counter
    _counter += 1
    return _counter


def _h(token):
    return {'Authorization': f'Bearer {token}'}


def make_student(db):
    uid = _uid()
    u = User(email=f'lib_stu_{uid}@test.sms', role='student',
             first_name=f'LStu{uid}', last_name='T')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(user_id=u.id, admission_no=f'LIB-ADM-{uid:05d}',
                first_name=f'LStu{uid}', last_name='T',
                date_of_birth=date(2012, 1, 1), gender='Male',
                admission_date=date(2024, 6, 1))
    db.session.add(s)
    db.session.commit()
    return s


def _add_book(client, admin_token, **kw):
    body = {
        'title': kw.get('title', 'Clean Code'),
        'author': kw.get('author', 'Robert Martin'),
        'total_copies': kw.get('total_copies', 3),
    }
    for k in ('isbn', 'publisher', 'category'):
        if k in kw:
            body[k] = kw[k]
    return client.post('/api/v1/library/books', json=body, headers=_h(admin_token))


# ===========================================================================
# SMS-053 — catalog
# ===========================================================================

def test_create_book(client, admin_token):
    resp = _add_book(client, admin_token, isbn='978-1', category='Programming')
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['available_copies'] == 3
    assert data['total_copies'] == 3


def test_create_book_requires_admin(client, teacher_token):
    resp = _add_book(client, teacher_token)
    assert resp.status_code == 403


def test_create_book_duplicate_isbn(client, admin_token):
    _add_book(client, admin_token, isbn='978-DUP')
    resp = _add_book(client, admin_token, isbn='978-DUP', title='Other')
    assert resp.status_code == 409


def test_create_book_invalid_copies(client, admin_token):
    resp = _add_book(client, admin_token, total_copies=0)
    assert resp.status_code == 422


def test_list_and_search_books(client, admin_token, teacher_token):
    _add_book(client, admin_token, title='Pythonic Patterns', author='A')
    _add_book(client, admin_token, title='Java Basics', author='B')
    resp = client.get('/api/v1/library/books?search=python', headers=_h(teacher_token))
    assert resp.status_code == 200
    titles = [b['title'] for b in resp.get_json()['data']['books']]
    assert any('Python' in t for t in titles)
    assert all('Java' not in t for t in titles)


def test_update_book(client, admin_token):
    bid = _add_book(client, admin_token, total_copies=3).get_json()['data']['id']
    resp = client.put(f'/api/v1/library/books/{bid}',
                      json={'total_copies': 5}, headers=_h(admin_token))
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['total_copies'] == 5
    assert data['available_copies'] == 5  # delta applied


def test_delete_book_blocked_with_active_issue(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=1).get_json()['data']['id']
    student = make_student(db)
    due = (date.today() + timedelta(days=7)).isoformat()
    client.post('/api/v1/library/issue',
                json={'book_id': bid, 'student_id': student.id, 'due_date': due},
                headers=_h(admin_token))
    resp = client.delete(f'/api/v1/library/books/{bid}', headers=_h(admin_token))
    assert resp.status_code == 409


def test_delete_book_ok(client, admin_token):
    bid = _add_book(client, admin_token).get_json()['data']['id']
    resp = client.delete(f'/api/v1/library/books/{bid}', headers=_h(admin_token))
    assert resp.status_code == 200


# ===========================================================================
# SMS-054 — issue & return
# ===========================================================================

def test_issue_decrements_available(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=2).get_json()['data']['id']
    student = make_student(db)
    due = (date.today() + timedelta(days=7)).isoformat()
    resp = client.post('/api/v1/library/issue',
                       json={'book_id': bid, 'student_id': student.id, 'due_date': due},
                       headers=_h(admin_token))
    assert resp.status_code == 201
    book = client.get(f'/api/v1/library/books/{bid}', headers=_h(admin_token)).get_json()['data']
    assert book['available_copies'] == 1


def test_return_on_time_no_fine(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=1).get_json()['data']['id']
    student = make_student(db)
    due = (date.today() + timedelta(days=7)).isoformat()
    iid = client.post('/api/v1/library/issue',
                      json={'book_id': bid, 'student_id': student.id, 'due_date': due},
                      headers=_h(admin_token)).get_json()['data']['id']
    resp = client.put(f'/api/v1/library/issue/{iid}/return',
                      json={'returned_date': date.today().isoformat()},
                      headers=_h(admin_token))
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['fine_amount'] == 0
    assert data['status'] == 'returned'
    # available copies restored
    book = client.get(f'/api/v1/library/books/{bid}', headers=_h(admin_token)).get_json()['data']
    assert book['available_copies'] == 1


def test_return_late_charges_fine(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=1).get_json()['data']['id']
    student = make_student(db)
    due = (date.today() - timedelta(days=4)).isoformat()    # already overdue
    iid = client.post('/api/v1/library/issue',
                      json={'book_id': bid, 'student_id': student.id, 'due_date': due},
                      headers=_h(admin_token)).get_json()['data']['id']
    resp = client.put(f'/api/v1/library/issue/{iid}/return',
                      json={'returned_date': date.today().isoformat()},
                      headers=_h(admin_token))
    assert resp.status_code == 200
    # 4 days * ₹5 = ₹20
    assert resp.get_json()['data']['fine_amount'] == 20.0


def test_issue_no_copies_available(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=1).get_json()['data']['id']
    s1 = make_student(db)
    s2 = make_student(db)
    due = (date.today() + timedelta(days=7)).isoformat()
    client.post('/api/v1/library/issue',
                json={'book_id': bid, 'student_id': s1.id, 'due_date': due},
                headers=_h(admin_token))
    resp = client.post('/api/v1/library/issue',
                       json={'book_id': bid, 'student_id': s2.id, 'due_date': due},
                       headers=_h(admin_token))
    assert resp.status_code == 409


def test_return_twice_conflicts(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=1).get_json()['data']['id']
    student = make_student(db)
    due = (date.today() + timedelta(days=7)).isoformat()
    iid = client.post('/api/v1/library/issue',
                      json={'book_id': bid, 'student_id': student.id, 'due_date': due},
                      headers=_h(admin_token)).get_json()['data']['id']
    client.put(f'/api/v1/library/issue/{iid}/return', json={}, headers=_h(admin_token))
    resp = client.put(f'/api/v1/library/issue/{iid}/return', json={}, headers=_h(admin_token))
    assert resp.status_code == 409


# ===========================================================================
# SMS-055 — overdue
# ===========================================================================

def test_overdue_endpoint_flags_and_fines(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=1).get_json()['data']['id']
    student = make_student(db)
    due = (date.today() - timedelta(days=3)).isoformat()
    client.post('/api/v1/library/issue',
                json={'book_id': bid, 'student_id': student.id, 'due_date': due},
                headers=_h(admin_token))
    resp = client.get('/api/v1/library/overdue', headers=_h(admin_token))
    assert resp.status_code == 200
    overdue = resp.get_json()['data']['overdue']
    assert len(overdue) == 1
    assert overdue[0]['days_overdue'] == 3
    assert overdue[0]['fine_amount'] == 15.0   # 3 * ₹5
    assert overdue[0]['status'] == 'overdue'


def test_overdue_excludes_current_loans(client, db, admin_token):
    bid = _add_book(client, admin_token, total_copies=1).get_json()['data']['id']
    student = make_student(db)
    due = (date.today() + timedelta(days=5)).isoformat()
    client.post('/api/v1/library/issue',
                json={'book_id': bid, 'student_id': student.id, 'due_date': due},
                headers=_h(admin_token))
    resp = client.get('/api/v1/library/overdue', headers=_h(admin_token))
    assert resp.get_json()['data']['overdue'] == []

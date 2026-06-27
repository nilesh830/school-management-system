"""
SMS-057 / SMS-058 / SMS-059 — Reports & Analytics.

Attendance report: date-range filter, section filter, class-average correctness,
empty range.
Grades report: multi-student, empty exam, grade-distribution counts.
Fees report: class filter, collection totals, defaulters present.
"""
from datetime import date, timedelta

from app.models.user import User
from app.models.student import Student
from app.models.class_ import Class
from app.models.section import Section
from app.models.academic_year import AcademicYear
from app.models.attendance import Attendance
from app.models.student_section import StudentSection
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.subject import Subject
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment


_counter = 0


def _uid():
    global _counter
    _counter += 1
    return _counter


# ---------------------------------------------------------------------------
# Shared factories
# ---------------------------------------------------------------------------

def make_class(db, grade_level=1):
    uid = _uid()
    c = Class(name=f'Grade {uid}', grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id):
    uid = _uid()
    sec = Section(name=chr(64 + (uid % 26) + 1), class_id=class_id)
    db.session.add(sec)
    db.session.commit()
    return sec


def make_academic_year(db):
    uid = _uid()
    ay = AcademicYear(name=f'AY-{uid}', start_date=date(2024, 6, 1),
                      end_date=date(2025, 5, 31), is_current=True, is_active=True)
    db.session.add(ay)
    db.session.commit()
    return ay


def make_student(db):
    uid = _uid()
    u = User(email=f'rstu_{uid}@test.sms', role='student',
             first_name=f'Stu{uid}', last_name='Rep')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(user_id=u.id, admission_no=f'ADM-REP-{uid:05d}',
                first_name=f'Stu{uid}', last_name='Rep',
                date_of_birth=date(2011, 1, 1), gender='Male',
                admission_date=date(2024, 6, 1))
    db.session.add(s)
    db.session.commit()
    return s


def enroll(db, student_id, section_id):
    db.session.add(StudentSection(
        student_id=student_id, section_id=section_id,
        academic_year='2024-2025', start_date=date(2024, 6, 1), is_current=True,
    ))
    db.session.commit()


def make_subject(db, max_marks=100):
    uid = _uid()
    sub = Subject(name=f'Subject {uid}', code=f'SUB{uid:04d}', max_marks=max_marks)
    db.session.add(sub)
    db.session.commit()
    return sub


def make_exam(db, section_id, academic_year_id):
    uid = _uid()
    e = Exam(name=f'Exam {uid}', term='Term 1', exam_type='midterm',
             section_id=section_id, academic_year_id=academic_year_id, is_active=True)
    db.session.add(e)
    db.session.commit()
    return e


def add_result(db, exam_id, student_id, subject_id, marks, grade, gpa):
    db.session.add(ExamResult(
        exam_id=exam_id, student_id=student_id, subject_id=subject_id,
        marks_obtained=marks, grade=grade, gpa=gpa, status='finalized',
    ))
    db.session.commit()


# ===========================================================================
# SMS-057 — Attendance report
# ===========================================================================

class TestAttendanceReport:

    def test_class_average_and_per_student(self, client, admin_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        s1 = make_student(db)
        s2 = make_student(db)

        base = date(2025, 1, 6)
        # s1: 3 present / 1 absent = 75% — NOT below, fine for average
        for i, st in enumerate(['present', 'present', 'present', 'absent']):
            db.session.add(Attendance(student_id=s1.id, section_id=sec.id,
                                      date=base + timedelta(days=i), status=st))
        # s2: 1 present / 3 absent = 25%
        for i, st in enumerate(['present', 'absent', 'absent', 'absent']):
            db.session.add(Attendance(student_id=s2.id, section_id=sec.id,
                                      date=base + timedelta(days=i), status=st))
        db.session.commit()

        resp = client.get(
            f'/api/v1/reports/attendance?section_id={sec.id}'
            f'&from_date=2025-01-01&to_date=2025-01-31',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['student_count'] == 2
        by_id = {s['student_id']: s for s in data['students']}
        assert by_id[s1.id]['percentage'] == 75.0
        assert by_id[s1.id]['present'] == 3
        assert by_id[s1.id]['total'] == 4
        assert by_id[s2.id]['percentage'] == 25.0
        # class average = (75 + 25) / 2 = 50
        assert data['class_average'] == 50.0

    def test_date_range_filter_excludes_outside(self, client, admin_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        s1 = make_student(db)
        # In range
        db.session.add(Attendance(student_id=s1.id, section_id=sec.id,
                                  date=date(2025, 2, 10), status='present'))
        # Out of range
        db.session.add(Attendance(student_id=s1.id, section_id=sec.id,
                                  date=date(2025, 3, 10), status='absent'))
        db.session.commit()

        resp = client.get(
            f'/api/v1/reports/attendance?section_id={sec.id}'
            f'&from_date=2025-02-01&to_date=2025-02-28',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        data = resp.get_json()['data']
        entry = data['students'][0]
        assert entry['total'] == 1
        assert entry['present'] == 1
        assert entry['percentage'] == 100.0

    def test_section_filter_isolation(self, client, admin_token, db):
        cls = make_class(db)
        sec_a = make_section(db, cls.id)
        sec_b = make_section(db, cls.id)
        sa = make_student(db)
        sb = make_student(db)
        db.session.add(Attendance(student_id=sa.id, section_id=sec_a.id,
                                  date=date(2025, 1, 10), status='present'))
        db.session.add(Attendance(student_id=sb.id, section_id=sec_b.id,
                                  date=date(2025, 1, 10), status='present'))
        db.session.commit()

        resp = client.get(
            f'/api/v1/reports/attendance?section_id={sec_a.id}'
            f'&from_date=2025-01-01&to_date=2025-01-31',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        ids = [s['student_id'] for s in resp.get_json()['data']['students']]
        assert sa.id in ids
        assert sb.id not in ids

    def test_empty_range_zero_average(self, client, admin_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        resp = client.get(
            f'/api/v1/reports/attendance?section_id={sec.id}'
            f'&from_date=2025-01-01&to_date=2025-01-31',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['students'] == []
        assert data['class_average'] == 0.0

    def test_bad_date_400(self, client, admin_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        resp = client.get(
            f'/api/v1/reports/attendance?section_id={sec.id}'
            f'&from_date=not-a-date&to_date=2025-01-31',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400

    def test_missing_section_404(self, client, admin_token, db):
        resp = client.get(
            '/api/v1/reports/attendance?section_id=999999'
            '&from_date=2025-01-01&to_date=2025-01-31',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 404

    def test_missing_params_400(self, client, admin_token):
        resp = client.get('/api/v1/reports/attendance',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_teacher_allowed(self, client, teacher_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        resp = client.get(
            f'/api/v1/reports/attendance?section_id={sec.id}'
            f'&from_date=2025-01-01&to_date=2025-01-31',
            headers={'Authorization': f'Bearer {teacher_token}'},
        )
        assert resp.status_code == 200

    def test_parent_forbidden(self, client, parent_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        resp = client.get(
            f'/api/v1/reports/attendance?section_id={sec.id}'
            f'&from_date=2025-01-01&to_date=2025-01-31',
            headers={'Authorization': f'Bearer {parent_token}'},
        )
        assert resp.status_code == 403


# ===========================================================================
# SMS-058 — Grades report
# ===========================================================================

class TestGradesReport:

    def test_multi_student_with_distribution(self, client, admin_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        ay = make_academic_year(db)
        exam = make_exam(db, sec.id, ay.id)
        sub = make_subject(db, max_marks=100)

        s1 = make_student(db)
        s2 = make_student(db)
        # s1: 95 -> A+ ; s2: 55 -> D
        add_result(db, exam.id, s1.id, sub.id, 95, 'A+', 4.0)
        add_result(db, exam.id, s2.id, sub.id, 55, 'D', 1.7)

        resp = client.get(
            f'/api/v1/reports/grades?exam_id={exam.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['student_count'] == 2
        by_id = {s['student_id']: s for s in data['students']}
        assert by_id[s1.id]['overall_percentage'] == 95.0
        assert by_id[s1.id]['overall_grade'] == 'A+'
        assert by_id[s2.id]['overall_grade'] == 'D'
        # grade distribution
        assert data['grade_distribution'].get('A+') == 1
        assert data['grade_distribution'].get('D') == 1

    def test_multi_subject_overall(self, client, admin_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        ay = make_academic_year(db)
        exam = make_exam(db, sec.id, ay.id)
        sub1 = make_subject(db, max_marks=100)
        sub2 = make_subject(db, max_marks=100)
        s1 = make_student(db)
        add_result(db, exam.id, s1.id, sub1.id, 80, 'A', 3.7)
        add_result(db, exam.id, s1.id, sub2.id, 60, 'C', 2.3)

        resp = client.get(
            f'/api/v1/reports/grades?exam_id={exam.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        data = resp.get_json()['data']
        entry = data['students'][0]
        # (80 + 60) / 200 = 70%
        assert entry['overall_percentage'] == 70.0
        assert len(entry['subjects']) == 2

    def test_section_filter(self, client, admin_token, db):
        cls = make_class(db)
        sec_a = make_section(db, cls.id)
        ay = make_academic_year(db)
        exam = make_exam(db, sec_a.id, ay.id)
        sub = make_subject(db)
        s_in = make_student(db)
        s_out = make_student(db)
        enroll(db, s_in.id, sec_a.id)  # only s_in enrolled in sec_a
        add_result(db, exam.id, s_in.id, sub.id, 90, 'A+', 4.0)
        add_result(db, exam.id, s_out.id, sub.id, 50, 'D', 1.7)

        resp = client.get(
            f'/api/v1/reports/grades?exam_id={exam.id}&section_id={sec_a.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        data = resp.get_json()['data']
        ids = [s['student_id'] for s in data['students']]
        assert s_in.id in ids
        assert s_out.id not in ids

    def test_empty_exam(self, client, admin_token, db):
        cls = make_class(db)
        sec = make_section(db, cls.id)
        ay = make_academic_year(db)
        exam = make_exam(db, sec.id, ay.id)
        resp = client.get(
            f'/api/v1/reports/grades?exam_id={exam.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['students'] == []
        assert data['student_count'] == 0
        assert data['grade_distribution'] == {}

    def test_missing_exam_404(self, client, admin_token):
        resp = client.get('/api/v1/reports/grades?exam_id=999999',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404

    def test_missing_exam_id_400(self, client, admin_token):
        resp = client.get('/api/v1/reports/grades',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_parent_forbidden(self, client, parent_token):
        resp = client.get('/api/v1/reports/grades?exam_id=1',
                          headers={'Authorization': f'Bearer {parent_token}'})
        assert resp.status_code == 403


# ===========================================================================
# SMS-059 — Fees report
# ===========================================================================

class TestFeesReport:

    def test_collection_totals_and_pending(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        student = make_student(db)

        fs = FeeStructure(class_id=cls.id, academic_year_id=ay.id,
                          fee_type='Tuition', amount=5000.00,
                          is_recurring=False, frequency='one_time')
        db.session.add(fs)
        db.session.commit()
        fr = FeeRecord(student_id=student.id, fee_structure_id=fs.id,
                       amount=5000.00, discount=0, net_amount=5000.00,
                       due_date=date.today() - timedelta(days=2), status='partial')
        db.session.add(fr)
        db.session.commit()
        # paid 2000 -> collected 2000, pending 3000
        db.session.add(FeePayment(fee_record_id=fr.id, amount_paid=2000.00,
                                  payment_method='cash', payment_date=date.today(),
                                  receipt_no=f'REC-RP-{_uid():06d}'))
        db.session.commit()

        resp = client.get('/api/v1/reports/fees',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['totals']['collected'] == 2000.0
        assert data['totals']['pending'] == 3000.0
        by_type = {b['fee_type']: b for b in data['by_fee_type']}
        assert by_type['Tuition']['collected'] == 2000.0
        assert by_type['Tuition']['pending'] == 3000.0

    def test_defaulters_present(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        student = make_student(db)
        fs = FeeStructure(class_id=cls.id, academic_year_id=ay.id,
                          fee_type='Bus', amount=1000.00,
                          is_recurring=False, frequency='one_time')
        db.session.add(fs)
        db.session.commit()
        fr = FeeRecord(student_id=student.id, fee_structure_id=fs.id,
                       amount=1000.00, discount=0, net_amount=1000.00,
                       due_date=date.today() - timedelta(days=5), status='pending')
        db.session.add(fr)
        db.session.commit()

        resp = client.get('/api/v1/reports/fees',
                          headers={'Authorization': f'Bearer {admin_token}'})
        data = resp.get_json()['data']
        assert data['defaulters_count'] >= 1
        ids = [d['student_id'] for d in data['defaulters']]
        assert student.id in ids

    def test_class_filter(self, client, admin_token, db):
        ay = make_academic_year(db)
        cls_a = make_class(db)
        cls_b = make_class(db)
        s_a = make_student(db)
        s_b = make_student(db)

        fs_a = FeeStructure(class_id=cls_a.id, academic_year_id=ay.id,
                            fee_type='TuitionA', amount=4000.00,
                            is_recurring=False, frequency='one_time')
        fs_b = FeeStructure(class_id=cls_b.id, academic_year_id=ay.id,
                            fee_type='TuitionB', amount=4000.00,
                            is_recurring=False, frequency='one_time')
        db.session.add_all([fs_a, fs_b])
        db.session.commit()
        db.session.add(FeeRecord(student_id=s_a.id, fee_structure_id=fs_a.id,
                                 amount=4000.00, discount=0, net_amount=4000.00,
                                 due_date=date.today() - timedelta(days=3),
                                 status='pending'))
        db.session.add(FeeRecord(student_id=s_b.id, fee_structure_id=fs_b.id,
                                 amount=4000.00, discount=0, net_amount=4000.00,
                                 due_date=date.today() - timedelta(days=3),
                                 status='pending'))
        db.session.commit()

        resp = client.get(f'/api/v1/reports/fees?class_id={cls_a.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        data = resp.get_json()['data']
        fee_types = {b['fee_type'] for b in data['by_fee_type']}
        assert 'TuitionA' in fee_types
        assert 'TuitionB' not in fee_types
        # defaulters also filtered by class
        ids = [d['student_id'] for d in data['defaulters']]
        assert s_a.id in ids
        assert s_b.id not in ids

    def test_empty_state(self, client, admin_token):
        resp = client.get('/api/v1/reports/fees',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['totals'] == {'collected': 0.0, 'pending': 0.0}
        assert data['by_fee_type'] == []
        assert data['defaulters'] == []

    def test_teacher_forbidden(self, client, teacher_token):
        resp = client.get('/api/v1/reports/fees',
                          headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403

"""
SMS-066 — Fee Applicability (transport-only optional fees, v1)
ADR-005. Tests for FeeService generation branching, skip counters, idempotency,
and the per-student amount_override path.
"""
import pytest
from datetime import date
from app.services.fee_service import FeeService
from app.models.user import User
from app.models.student import Student
from app.models.class_ import Class
from app.models.section import Section
from app.models.student_section import StudentSection
from app.models.academic_year import AcademicYear
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.transport_route import TransportRoute
from app.models.student_transport import StudentTransport


# ---------------------------------------------------------------------------
# Helpers (mirror test_fee_records.py)
# ---------------------------------------------------------------------------

def make_class(db, name='Grade 1', grade_level=1):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_academic_year(db, name='2024-2025'):
    ay = AcademicYear(
        name=name,
        start_date=date(2024, 6, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        is_active=True,
    )
    db.session.add(ay)
    db.session.commit()
    return ay


def make_section(db, class_id, name='A'):
    s = Section(name=name, class_id=class_id)
    db.session.add(s)
    db.session.commit()
    return s


_seq = {'n': 0}


def make_student_user(db, admission_no, admission_date=date(2024, 6, 1)):
    _seq['n'] += 1
    email = f'fa_student_{_seq["n"]}@test.sms'
    u = User(email=email, role='student', first_name='Test', last_name='Student')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=admission_no,
        first_name='Test',
        last_name='Student',
        date_of_birth=date(2012, 1, 1),
        gender='Female',
        admission_date=admission_date,
        is_active=True,
    )
    db.session.add(s)
    db.session.commit()
    return s


def enroll(db, student_id, section_id, is_current=True):
    ss = StudentSection(
        student_id=student_id,
        section_id=section_id,
        academic_year='2024-2025',
        start_date=date(2024, 6, 1),
        is_current=is_current,
    )
    db.session.add(ss)
    db.session.commit()
    return ss


def make_route(db, name='Route 1', fare=None, fare_frequency='monthly'):
    r = TransportRoute(name=name, fare=fare, fare_frequency=fare_frequency)
    db.session.add(r)
    db.session.commit()
    return r


def assign_transport(db, student_id, route_id, academic_year_id, is_active=True):
    st = StudentTransport(
        student_id=student_id,
        route_id=route_id,
        academic_year_id=academic_year_id,
        is_active=is_active,
    )
    db.session.add(st)
    db.session.commit()
    return st


def make_fee_structure(db, class_id, academic_year_id, **kwargs):
    defaults = dict(
        fee_type='Tuition Fee',
        amount=5000.00,
        is_recurring=False,
        frequency='one_time',
        due_date=date(2024, 7, 31),
        applicability='mandatory',
        source_kind='flat',
        transport_route_id=None,
    )
    defaults.update(kwargs)
    fs = FeeStructure(class_id=class_id, academic_year_id=academic_year_id, **defaults)
    db.session.add(fs)
    db.session.commit()
    return fs


# A fixed as_of so monthly period counts are deterministic.
AS_OF = date(2024, 6, 15)


# ---------------------------------------------------------------------------
# 1. Mandatory/flat generation unchanged (regression)
# ---------------------------------------------------------------------------

class TestMandatoryFlatUnchanged:

    def test_mandatory_flat_bills_all_enrolled(self, app, db):
        with app.app_context():
            cls = make_class(db)
            ay = make_academic_year(db)
            section = make_section(db, cls.id)
            fs = make_fee_structure(db, cls.id, ay.id, fee_type='Tuition',
                                    amount=5000.00, frequency='one_time',
                                    due_date=date(2024, 7, 31))
            sa = make_student_user(db, 'ADM-FA-001')
            sb = make_student_user(db, 'ADM-FA-002')
            enroll(db, sa.id, section.id)
            enroll(db, sb.id, section.id)

            result, err = FeeService.generate_records_for_class(fs.id, as_of=AS_OF)

            assert err is None
            assert result['generated'] == 2
            assert result['skipped'] == 0
            assert result['skipped_no_fare'] == 0
            assert result['skipped_no_optin'] == 0
            assert result['total_students'] == 2

            recs = db.session.query(FeeRecord).filter_by(fee_structure_id=fs.id).all()
            assert all(float(r.amount) == 5000.00 for r in recs)
            assert all(float(r.net_amount) == 5000.00 for r in recs)


# ---------------------------------------------------------------------------
# 2. Transport generation: only opted-in students, at their route fare;
#    route filter excludes students on other routes.
# ---------------------------------------------------------------------------

class TestTransportGeneration:

    def test_bills_only_opted_in_at_route_fare(self, app, db):
        with app.app_context():
            cls = make_class(db)
            ay = make_academic_year(db)
            section = make_section(db, cls.id)
            route = make_route(db, name='R-North', fare=800.00, fare_frequency='one_time')

            rider = make_student_user(db, 'ADM-FA-010')
            non_rider = make_student_user(db, 'ADM-FA-011')
            enroll(db, rider.id, section.id)
            enroll(db, non_rider.id, section.id)
            assign_transport(db, rider.id, route.id, ay.id)

            fs = make_fee_structure(db, cls.id, ay.id, fee_type='Transport',
                                    amount=0, source_kind='transport',
                                    applicability='optional', frequency='one_time',
                                    due_date=None)

            result, err = FeeService.generate_records_for_class(fs.id, as_of=AS_OF)

            assert err is None
            # only the rider is billed
            assert result['generated'] == 1
            assert result['total_students'] == 1
            recs = db.session.query(FeeRecord).filter_by(fee_structure_id=fs.id).all()
            assert len(recs) == 1
            assert recs[0].student_id == rider.id
            assert float(recs[0].amount) == 800.00

    def test_route_filter_excludes_other_routes(self, app, db):
        with app.app_context():
            cls = make_class(db)
            ay = make_academic_year(db)
            section = make_section(db, cls.id)
            route_a = make_route(db, name='R-A', fare=500.00, fare_frequency='one_time')
            route_b = make_route(db, name='R-B', fare=700.00, fare_frequency='one_time')

            s_a = make_student_user(db, 'ADM-FA-020')
            s_b = make_student_user(db, 'ADM-FA-021')
            enroll(db, s_a.id, section.id)
            enroll(db, s_b.id, section.id)
            assign_transport(db, s_a.id, route_a.id, ay.id)
            assign_transport(db, s_b.id, route_b.id, ay.id)

            # Structure scoped to route_a only.
            fs = make_fee_structure(db, cls.id, ay.id, fee_type='Transport A',
                                    amount=0, source_kind='transport',
                                    applicability='optional', frequency='one_time',
                                    due_date=None, transport_route_id=route_a.id)

            result, err = FeeService.generate_records_for_class(fs.id, as_of=AS_OF)

            assert err is None
            assert result['generated'] == 1
            assert result['total_students'] == 1
            recs = db.session.query(FeeRecord).filter_by(fee_structure_id=fs.id).all()
            assert len(recs) == 1
            assert recs[0].student_id == s_a.id
            assert float(recs[0].amount) == 500.00


# ---------------------------------------------------------------------------
# 3. skipped_no_fare: billed student whose route has NULL fare -> no record
# ---------------------------------------------------------------------------

class TestSkippedNoFare:

    def test_null_fare_skips_and_counts(self, app, db):
        with app.app_context():
            cls = make_class(db)
            ay = make_academic_year(db)
            section = make_section(db, cls.id)
            route_paid = make_route(db, name='R-Paid', fare=600.00, fare_frequency='one_time')
            route_unset = make_route(db, name='R-Unset', fare=None, fare_frequency='one_time')

            paid = make_student_user(db, 'ADM-FA-030')
            unset = make_student_user(db, 'ADM-FA-031')
            enroll(db, paid.id, section.id)
            enroll(db, unset.id, section.id)
            assign_transport(db, paid.id, route_paid.id, ay.id)
            assign_transport(db, unset.id, route_unset.id, ay.id)

            fs = make_fee_structure(db, cls.id, ay.id, fee_type='Transport',
                                    amount=0, source_kind='transport',
                                    applicability='optional', frequency='one_time',
                                    due_date=None)

            result, err = FeeService.generate_records_for_class(fs.id, as_of=AS_OF)

            assert err is None
            assert result['generated'] == 1
            assert result['skipped_no_fare'] == 1
            assert result['total_students'] == 2  # both opted-in count
            recs = db.session.query(FeeRecord).filter_by(fee_structure_id=fs.id).all()
            assert len(recs) == 1
            assert recs[0].student_id == paid.id


# ---------------------------------------------------------------------------
# 4. Optional + flat with no opt-in source bills nobody (skipped_no_optin)
# ---------------------------------------------------------------------------

class TestOptionalFlatBillsNobody:

    def test_optional_flat_no_optin(self, app, db):
        with app.app_context():
            cls = make_class(db)
            ay = make_academic_year(db)
            section = make_section(db, cls.id)
            sa = make_student_user(db, 'ADM-FA-040')
            sb = make_student_user(db, 'ADM-FA-041')
            enroll(db, sa.id, section.id)
            enroll(db, sb.id, section.id)

            fs = make_fee_structure(db, cls.id, ay.id, fee_type='Hostel',
                                    amount=3000.00, source_kind='flat',
                                    applicability='optional', frequency='one_time',
                                    due_date=date(2024, 7, 31))

            result, err = FeeService.generate_records_for_class(fs.id, as_of=AS_OF)

            assert err is None
            assert result['generated'] == 0
            assert result['skipped_no_optin'] == 2
            assert result['total_students'] == 0
            recs = db.session.query(FeeRecord).filter_by(fee_structure_id=fs.id).all()
            assert recs == []


# ---------------------------------------------------------------------------
# 5. Idempotent re-run creates no duplicates (transport)
# ---------------------------------------------------------------------------

class TestIdempotentTransport:

    def test_rerun_no_duplicates(self, app, db):
        with app.app_context():
            cls = make_class(db)
            ay = make_academic_year(db)
            section = make_section(db, cls.id)
            route = make_route(db, name='R-Idem', fare=900.00, fare_frequency='monthly')
            rider = make_student_user(db, 'ADM-FA-050', admission_date=date(2024, 5, 1))
            enroll(db, rider.id, section.id)
            assign_transport(db, rider.id, route.id, ay.id)

            fs = make_fee_structure(db, cls.id, ay.id, fee_type='Transport',
                                    amount=0, source_kind='transport',
                                    applicability='optional', frequency='monthly',
                                    due_date=None)

            r1, _ = FeeService.generate_records_for_class(fs.id, as_of=AS_OF)
            assert r1['generated'] == 2  # May + June 2024 (admission 2024-05-01)
            assert r1['skipped'] == 0

            r2, _ = FeeService.generate_records_for_class(fs.id, as_of=AS_OF)
            assert r2['generated'] == 0
            assert r2['skipped'] == 2

            recs = db.session.query(FeeRecord).filter_by(fee_structure_id=fs.id).all()
            assert len(recs) == 2
            assert {r.period for r in recs} == {'2024-05', '2024-06'}


# ---------------------------------------------------------------------------
# 6. run_recurring_catchup picks up transport structures
# ---------------------------------------------------------------------------

class TestRecurringCatchupTransport:

    def test_transport_structure_included(self, app, db):
        with app.app_context():
            cls = make_class(db)
            ay = make_academic_year(db)
            section = make_section(db, cls.id)
            route = make_route(db, name='R-Catch', fare=400.00, fare_frequency='monthly')
            rider = make_student_user(db, 'ADM-FA-060', admission_date=date(2024, 6, 1))
            enroll(db, rider.id, section.id)
            assign_transport(db, rider.id, route.id, ay.id)

            # frequency='one_time' on the structure itself — catch-up must still
            # include it because source_kind='transport'.
            make_fee_structure(db, cls.id, ay.id, fee_type='Transport',
                               amount=0, source_kind='transport',
                               applicability='optional', frequency='one_time',
                               due_date=None)

            generated = FeeService.run_recurring_catchup(as_of=AS_OF)
            assert generated == 1  # June 2024
            recs = db.session.query(FeeRecord).all()
            assert len(recs) == 1
            assert float(recs[0].amount) == 400.00


# ---------------------------------------------------------------------------
# 7. amount_override PATCH recomputes net_amount (set + clear)
# ---------------------------------------------------------------------------

class TestAmountOverride:

    def _setup_record(self, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        section = make_section(db, cls.id)
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Tuition',
                                amount=5000.00, frequency='one_time',
                                due_date=date(2024, 7, 31))
        student = make_student_user(db, 'ADM-FA-070')
        enroll(db, student.id, section.id)
        FeeService.generate_records_for_class(fs.id, as_of=AS_OF)
        rec = db.session.query(FeeRecord).filter_by(fee_structure_id=fs.id).first()
        return rec

    def test_set_override_recomputes_net(self, app, db):
        with app.app_context():
            rec = self._setup_record(db)
            result, err = FeeService.set_amount_override(rec.id, 4500.00)
            assert err is None
            assert result['amount_override'] == 4500.00
            assert result['amount'] == 4500.00
            assert result['net_amount'] == 4500.00

    def test_clear_override_reverts_to_computed(self, app, db):
        with app.app_context():
            rec = self._setup_record(db)
            FeeService.set_amount_override(rec.id, 4500.00)
            result, err = FeeService.set_amount_override(rec.id, None)
            assert err is None
            assert result['amount_override'] is None
            assert result['amount'] == 5000.00
            assert result['net_amount'] == 5000.00

    def test_override_via_patch_endpoint(self, app, client, admin_token, db):
        with app.app_context():
            rec = self._setup_record(db)
            rec_id = rec.id
        resp = client.patch(
            f'/api/v1/fees/records/{rec_id}/amount',
            json={'amount_override': 4200.00},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['amount'] == 4200.00
        assert body['data']['net_amount'] == 4200.00
        assert body['data']['amount_override'] == 4200.00

from app import db
from app.models.student import Student
from sqlalchemy import or_


class StudentService:

    @staticmethod
    def get_all(page=1, per_page=20, search=''):
        query = Student.query.filter_by(is_active=True)
        if search:
            query = query.filter(
                or_(
                    Student.first_name.ilike(f'%{search}%'),
                    Student.last_name.ilike(f'%{search}%'),
                    Student.admission_no.ilike(f'%{search}%'),
                )
            )
        pagination = query.order_by(Student.admission_no).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return {
            'students': [s.to_dict() for s in pagination.items],
            'meta': {
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages,
            }
        }

    @staticmethod
    def get_by_id(student_id):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        return student.to_dict() if student else None

    @staticmethod
    def create(data):
        if Student.query.filter_by(admission_no=data.get('admission_no')).first():
            return None, {'message': 'Admission number already exists', 'status': 409}

        required = ['first_name', 'last_name', 'date_of_birth', 'gender', 'admission_date', 'admission_no']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return None, {'message': 'Missing required fields', 'errors': {f: 'required' for f in missing}, 'status': 422}

        from datetime import date
        student = Student(
            admission_no=data['admission_no'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            date_of_birth=date.fromisoformat(data['date_of_birth']),
            gender=data['gender'],
            admission_date=date.fromisoformat(data['admission_date']),
            blood_group=data.get('blood_group'),
            address=data.get('address'),
            phone=data.get('phone'),
            user_id=data.get('user_id', 1),
        )
        db.session.add(student)
        db.session.commit()
        return student.to_dict(), None

    @staticmethod
    def update(student_id, data):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}

        updatable = ['first_name', 'last_name', 'blood_group', 'address', 'phone']
        for field in updatable:
            if field in data:
                setattr(student, field, data[field])

        db.session.commit()
        return student.to_dict(), None

    @staticmethod
    def delete(student_id):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return False, {'message': 'Student not found', 'status': 404}
        student.is_active = False
        db.session.commit()
        return True, None

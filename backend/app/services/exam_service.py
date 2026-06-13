from app.utils.tenant import get_db
from app.models.exam import Exam
from app.models.section import Section
from app.models.academic_year import AcademicYear

VALID_EXAM_TYPES = ('midterm', 'final', 'unit_test', 'practical')


class ExamService:

    @staticmethod
    def create_exam(data: dict, created_by: int):
        """
        Create a new exam definition.

        Returns (exam_dict, None) on success or (None, error_dict) on failure.
        error_dict always contains 'message' and 'status' keys.
        """
        exam_type = data.get('exam_type')
        if exam_type not in VALID_EXAM_TYPES:
            return None, {
                'message': f"Invalid exam_type '{exam_type}'. Must be one of: {', '.join(VALID_EXAM_TYPES)}",
                'status': 422,
            }

        section_id = data.get('section_id')
        section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
        if not section:
            return None, {
                'message': f'Section {section_id} not found or is inactive',
                'status': 404,
            }

        academic_year_id = data.get('academic_year_id')
        academic_year = get_db().query(AcademicYear).filter_by(id=academic_year_id).first()
        if not academic_year:
            return None, {
                'message': f'AcademicYear {academic_year_id} not found',
                'status': 404,
            }

        name = data.get('name')
        duplicate = (
            get_db()
            .query(Exam)
            .filter_by(
                name=name,
                section_id=section_id,
                academic_year_id=academic_year_id,
            )
            .first()
        )
        if duplicate:
            return None, {
                'message': (
                    f"Exam '{name}' already exists for section {section_id} "
                    f"in academic year {academic_year_id}"
                ),
                'status': 409,
            }

        exam = Exam(
            name=name,
            term=data.get('term'),
            exam_type=exam_type,
            section_id=section_id,
            academic_year_id=academic_year_id,
            conducted_date=data.get('conducted_date'),
            is_active=data.get('is_active', True),
            created_by=created_by,
        )
        get_db().add(exam)
        get_db().commit()
        return exam.to_dict(), None

    @staticmethod
    def get_exams(section_id=None, academic_year_id=None, is_active=None):
        """
        Return a list of exam dicts, optionally filtered.
        """
        query = get_db().query(Exam)
        if section_id is not None:
            query = query.filter_by(section_id=section_id)
        if academic_year_id is not None:
            query = query.filter_by(academic_year_id=academic_year_id)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        exams = query.order_by(Exam.created_at.desc()).all()
        return [e.to_dict() for e in exams]

    @staticmethod
    def get_exam(exam_id: int):
        """
        Fetch a single exam by id.

        Returns (exam_dict, None) or (None, {'message': ..., 'status': 404}).
        """
        exam = get_db().query(Exam).filter_by(id=exam_id).first()
        if not exam:
            return None, {'message': f'Exam {exam_id} not found', 'status': 404}
        return exam.to_dict(), None

    @staticmethod
    def update_exam(exam_id: int, data: dict):
        """
        Update mutable fields of an exam.

        Allowed fields: name, term, exam_type, conducted_date, is_active.
        Returns (exam_dict, None) or (None, error_dict).
        """
        exam = get_db().query(Exam).filter_by(id=exam_id).first()
        if not exam:
            return None, {'message': f'Exam {exam_id} not found', 'status': 404}

        if 'exam_type' in data and data['exam_type'] is not None:
            if data['exam_type'] not in VALID_EXAM_TYPES:
                return None, {
                    'message': (
                        f"Invalid exam_type '{data['exam_type']}'. "
                        f"Must be one of: {', '.join(VALID_EXAM_TYPES)}"
                    ),
                    'status': 422,
                }
            exam.exam_type = data['exam_type']

        if 'name' in data and data['name'] is not None:
            exam.name = data['name']
        if 'term' in data and data['term'] is not None:
            exam.term = data['term']
        if 'conducted_date' in data:
            exam.conducted_date = data['conducted_date']
        if 'is_active' in data and data['is_active'] is not None:
            exam.is_active = data['is_active']

        get_db().commit()
        return exam.to_dict(), None

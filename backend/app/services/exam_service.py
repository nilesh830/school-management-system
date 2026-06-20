from app.utils.tenant import get_db
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
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

    # -----------------------------------------------------------------------
    # T-030-02: Grade calculator
    # -----------------------------------------------------------------------

    @staticmethod
    def calculate_grade(marks_obtained: float, max_marks: float) -> tuple[str, float]:
        """
        Return (grade, gpa) from a percentage-based scale.

        Edge case: max_marks == 0 is treated as F / 0.0 to avoid division by zero.
        """
        if max_marks == 0:
            return 'F', 0.0

        pct = (marks_obtained / max_marks) * 100

        if pct >= 90:
            return 'A+', 4.0
        elif pct >= 80:
            return 'A', 3.7
        elif pct >= 70:
            return 'B', 3.0
        elif pct >= 60:
            return 'C', 2.3
        elif pct >= 50:
            return 'D', 1.7
        elif pct >= 40:
            return 'E', 1.0
        else:
            return 'F', 0.0

    # -----------------------------------------------------------------------
    # T-030-03: Bulk marks entry with upsert
    # -----------------------------------------------------------------------

    @staticmethod
    def enter_marks(
        exam_id: int,
        subject_id: int,
        section_id: int,
        marks_list: list,
        created_by_user_id: int,
        role: str,
    ) -> tuple[dict | None, dict | None]:
        """
        Upsert marks for a list of students for a given exam + subject.

        Returns (result_dict, None) on success or (None, error_dict) on failure.
        error_dict always contains 'message' and 'status' keys.
        """
        session = get_db()

        # 1. Exam must exist and be active
        exam = session.query(Exam).filter_by(id=exam_id, is_active=True).first()
        if not exam:
            return None, {
                'message': f'Exam {exam_id} not found or is inactive',
                'status': 404,
            }

        # 2. Subject must exist
        subject = session.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            return None, {
                'message': f'Subject {subject_id} not found',
                'status': 404,
            }

        # 3. Teacher authorisation: must be assigned to this subject
        if role == 'teacher':
            teacher = session.query(Teacher).filter_by(
                user_id=created_by_user_id
            ).first()
            if not teacher:
                return None, {
                    'message': 'Teacher profile not found for this user',
                    'status': 403,
                }
            assignment = session.query(TeacherSubject).filter_by(
                teacher_id=teacher.id,
                subject_id=subject_id,
            ).first()
            if not assignment:
                return None, {
                    'message': 'You are not assigned to teach this subject',
                    'status': 403,
                }

        # 4. Validate all marks_obtained <= subject.max_marks
        max_marks = float(subject.max_marks)
        invalid = [
            entry['student_id']
            for entry in marks_list
            if float(entry['marks_obtained']) > max_marks
        ]
        if invalid:
            return None, {
                'message': (
                    f'marks_obtained exceeds max_marks ({max_marks}) '
                    f'for student_id(s): {invalid}'
                ),
                'status': 422,
            }

        # 5. Reject if any result for this batch is already finalised
        student_ids = [e['student_id'] for e in marks_list]
        finalized = (
            session.query(ExamResult)
            .filter(
                ExamResult.exam_id == exam_id,
                ExamResult.subject_id == subject_id,
                ExamResult.student_id.in_(student_ids),
                ExamResult.status == 'finalized',
            )
            .first()
        )
        if finalized:
            return None, {
                'message': 'Marks are finalized and cannot be edited',
                'status': 409,
            }

        # 6. Upsert each entry
        saved = 0
        for entry in marks_list:
            sid = entry['student_id']
            mo = float(entry['marks_obtained'])
            grade, gpa = ExamService.calculate_grade(mo, max_marks)

            existing = (
                session.query(ExamResult)
                .filter_by(
                    exam_id=exam_id,
                    student_id=sid,
                    subject_id=subject_id,
                )
                .first()
            )
            if existing:
                existing.marks_obtained = mo
                existing.grade = grade
                existing.gpa = gpa
                existing.created_by = created_by_user_id
            else:
                result = ExamResult(
                    exam_id=exam_id,
                    student_id=sid,
                    subject_id=subject_id,
                    marks_obtained=mo,
                    grade=grade,
                    gpa=gpa,
                    status='draft',
                    created_by=created_by_user_id,
                )
                session.add(result)
            saved += 1

        session.commit()

        return {
            'saved': saved,
            'exam_id': exam_id,
            'subject_id': subject_id,
        }, None

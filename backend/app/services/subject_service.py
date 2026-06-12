from app.utils.tenant import get_db
from app.models.subject import Subject
from app.models.teacher_subject import TeacherSubject


def _paginate(query, page: int, per_page: int) -> tuple:
    """Returns (items_list, total_count)."""
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, total


class SubjectService:

    @staticmethod
    def get_all(page=1, per_page=20, search=''):
        query = get_db().query(Subject).filter_by(is_active=True)
        if search:
            query = query.filter(
                Subject.name.ilike(f'%{search}%') | Subject.code.ilike(f'%{search}%')
            )
        query = query.order_by(Subject.code)
        items, total = _paginate(query, page, per_page)
        pages = (total + per_page - 1) // per_page
        return {
            'subjects': [s.to_dict() for s in items],
            'meta': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages,
            },
        }

    @staticmethod
    def get_by_id(subject_id: int):
        subject = get_db().query(Subject).filter_by(id=subject_id, is_active=True).first()
        return subject.to_dict() if subject else None

    @staticmethod
    def create(data: dict):
        """
        Create a new subject. Code is uppercased automatically.
        Returns (subject_dict, None) or (None, error_dict).
        """
        name = data.get('name', '').strip()
        if not name:
            return None, {'message': 'Name is required', 'status': 400}

        code = data.get('code', '').strip().upper()
        if not code:
            return None, {'message': 'Code is required', 'status': 400}

        # Duplicate code check
        if get_db().query(Subject).filter_by(code=code).first():
            return None, {'message': f'Subject with code "{code}" already exists', 'status': 409}

        max_marks = data.get('max_marks', 100)
        pass_marks = data.get('pass_marks', 35)

        if not isinstance(max_marks, int) or max_marks <= 0:
            return None, {'message': 'max_marks must be a positive integer', 'status': 400}
        if not isinstance(pass_marks, int) or pass_marks < 0:
            return None, {'message': 'pass_marks must be a non-negative integer', 'status': 400}
        if pass_marks >= max_marks:
            return None, {'message': 'pass_marks must be less than max_marks', 'status': 400}

        subject = Subject(
            name=name,
            code=code,
            description=data.get('description'),
            max_marks=max_marks,
            pass_marks=pass_marks,
            is_active=bool(data.get('is_active', True)),
        )
        get_db().add(subject)
        get_db().commit()
        return subject.to_dict(), None

    @staticmethod
    def update(subject_id: int, data: dict):
        """Returns (subject_dict, None) or (None, error_dict)."""
        subject = get_db().query(Subject).filter_by(id=subject_id, is_active=True).first()
        if not subject:
            return None, {'message': 'Subject not found', 'status': 404}

        if 'name' in data:
            subject.name = data['name'].strip()

        if 'code' in data:
            code = data['code'].strip().upper()
            duplicate = get_db().query(Subject).filter_by(code=code).first()
            if duplicate and duplicate.id != subject_id:
                return None, {'message': f'Subject with code "{code}" already exists', 'status': 409}
            subject.code = code

        if 'description' in data:
            subject.description = data['description']

        if 'max_marks' in data:
            subject.max_marks = data['max_marks']

        if 'pass_marks' in data:
            subject.pass_marks = data['pass_marks']

        if subject.pass_marks >= subject.max_marks:
            return None, {'message': 'pass_marks must be less than max_marks', 'status': 400}

        if 'is_active' in data:
            subject.is_active = bool(data['is_active'])

        get_db().commit()
        return subject.to_dict(), None

    @staticmethod
    def delete(subject_id: int):
        """Soft delete. Returns (True, None) or (False, error_dict)."""
        subject = get_db().query(Subject).filter_by(id=subject_id, is_active=True).first()
        if not subject:
            return False, {'message': 'Subject not found', 'status': 404}

        # Block if there are active TeacherSubject assignments
        assignment_count = (
            get_db()
            .query(TeacherSubject)
            .filter_by(subject_id=subject_id)
            .count()
        )
        if assignment_count > 0:
            return False, {
                'message': (
                    f'Cannot delete subject: {assignment_count} teacher assignment(s) exist. '
                    'Remove assignments first.'
                ),
                'status': 409,
            }

        subject.is_active = False
        get_db().commit()
        return True, None

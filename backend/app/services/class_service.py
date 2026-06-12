from app.utils.tenant import get_db
from app.models.class_ import Class
from app.models.section import Section


def _paginate(query, page: int, per_page: int) -> tuple:
    """Returns (items_list, total_count)."""
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, total


class ClassService:

    @staticmethod
    def get_all(page=1, per_page=20, search='', academic_year_id=None):
        query = get_db().query(Class).filter_by(is_active=True)

        if search:
            query = query.filter(Class.name.ilike(f'%{search}%'))

        if academic_year_id:
            query = query.filter_by(academic_year_id=academic_year_id)

        query = query.order_by(Class.grade_level, Class.name)
        items, total = _paginate(query, page, per_page)
        pages = (total + per_page - 1) // per_page
        return {
            'classes': [c.to_dict() for c in items],
            'meta': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages,
            },
        }

    @staticmethod
    def get_by_id(class_id: int):
        """Return class dict with sections list, or None."""
        cls = get_db().query(Class).filter_by(id=class_id, is_active=True).first()
        if not cls:
            return None
        return cls.to_dict(include_sections=True)

    @staticmethod
    def create(data: dict):
        """
        Create a new class.
        Returns (class_dict, None) or (None, error_dict).
        """
        name = data.get('name', '').strip()
        if not name:
            return None, {'message': 'Name is required', 'status': 400}

        grade_level = data.get('grade_level')
        if grade_level is None:
            return None, {'message': 'grade_level is required', 'status': 400}
        try:
            grade_level = int(grade_level)
        except (TypeError, ValueError):
            return None, {'message': 'grade_level must be an integer', 'status': 400}

        cls = Class(
            name=name,
            grade_level=grade_level,
            description=data.get('description'),
            academic_year_id=data.get('academic_year_id'),
            is_active=bool(data.get('is_active', True)),
        )
        get_db().add(cls)
        get_db().commit()
        return cls.to_dict(), None

    @staticmethod
    def update(class_id: int, data: dict):
        """Returns (class_dict, None) or (None, error_dict)."""
        cls = get_db().query(Class).filter_by(id=class_id, is_active=True).first()
        if not cls:
            return None, {'message': 'Class not found', 'status': 404}

        if 'name' in data:
            cls.name = data['name'].strip()

        if 'grade_level' in data:
            try:
                cls.grade_level = int(data['grade_level'])
            except (TypeError, ValueError):
                return None, {'message': 'grade_level must be an integer', 'status': 400}

        if 'description' in data:
            cls.description = data['description']

        if 'academic_year_id' in data:
            cls.academic_year_id = data['academic_year_id']

        if 'is_active' in data:
            cls.is_active = bool(data['is_active'])

        get_db().commit()
        return cls.to_dict(), None

    @staticmethod
    def delete(class_id: int):
        """Soft delete. Blocked if active sections exist."""
        cls = get_db().query(Class).filter_by(id=class_id, is_active=True).first()
        if not cls:
            return False, {'message': 'Class not found', 'status': 404}

        active_sections = (
            get_db()
            .query(Section)
            .filter_by(class_id=class_id, is_active=True)
            .count()
        )
        if active_sections > 0:
            return False, {
                'message': (
                    f'Cannot delete class: {active_sections} active section(s) exist. '
                    'Delete or deactivate all sections first.'
                ),
                'status': 409,
            }

        cls.is_active = False
        get_db().commit()
        return True, None

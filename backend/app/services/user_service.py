from flask import abort
from app import db
from app.models.user import User
from app.models.parent import Parent
from app.utils.validators import validate_password, validate_email


VALID_ROLES = {'admin', 'teacher', 'student', 'parent'}

PARENT_REQUIRED_FIELDS = {'relationship_type', 'phone_primary'}
VALID_RELATIONSHIP_TYPES = {'Father', 'Mother', 'Guardian'}


class UserService:

    @staticmethod
    def get_all(page=1, per_page=20, role=None, search=None, is_active=None):
        query = User.query

        if role:
            if role not in VALID_ROLES:
                abort(400, description=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
            query = query.filter_by(role=role)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        if search:
            term = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.email.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                )
            )

        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            'data': [u.to_dict() for u in pagination.items],
            'meta': {
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages,
            },
        }

    @staticmethod
    def get_by_id(user_id):
        user = db.session.get(User, user_id)
        if not user:
            abort(404, description="User not found")
        return user

    @staticmethod
    def create_user(data):
        required = {'email', 'password', 'role', 'first_name', 'last_name'}
        missing = required - set(data.keys())
        if missing:
            abort(400, description=f"Missing required fields: {', '.join(missing)}")

        email = data['email'].lower().strip()
        if not validate_email(email):
            abort(422, description="Invalid email format")

        if User.query.filter_by(email=email).first():
            abort(409, description="A user with this email already exists")

        role = data['role']
        if role not in VALID_ROLES:
            abort(400, description=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

        pw_errors = validate_password(data['password'])
        if pw_errors:
            abort(422, description=' | '.join(pw_errors))

        user = User(
            email=email,
            role=role,
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush()  # get user.id before commit

        if role == 'parent':
            missing_parent = PARENT_REQUIRED_FIELDS - set(data.keys())
            if missing_parent:
                db.session.rollback()
                abort(400, description=f"Parent role requires: {', '.join(missing_parent)}")

            rel_type = data['relationship_type']
            if rel_type not in VALID_RELATIONSHIP_TYPES:
                db.session.rollback()
                abort(422, description=f"relationship_type must be one of: {', '.join(VALID_RELATIONSHIP_TYPES)}")

            parent = Parent(
                user_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                relationship_type=rel_type,
                phone_primary=data['phone_primary'].strip(),
                phone_secondary=data.get('phone_secondary', '').strip() or None,
                occupation=data.get('occupation', '').strip() or None,
                address=data.get('address', '').strip() or None,
            )
            db.session.add(parent)

        db.session.commit()
        return user

    @staticmethod
    def deactivate(user_id, requesting_user_id):
        if user_id == requesting_user_id:
            abort(400, description="Cannot deactivate your own account")

        user = db.session.get(User, user_id)
        if not user:
            abort(404, description="User not found")
        if not user.is_active:
            abort(400, description="User is already inactive")

        user.is_active = False
        db.session.commit()
        return user

import os
import secrets

from flask import current_app
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app import db
from app.models.student import Student
from app.models.student_section import StudentSection
from app.models.student_document import StudentDocument
from app.models.parent import Parent, student_parent

ALLOWED_DOC_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
MAX_DOC_BYTES = 5 * 1024 * 1024  # 5 MB


def _allowed_doc(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS
    )


class StudentService:

    # -------------------------------------------------------------------------
    # SMS-008 — Student list
    # -------------------------------------------------------------------------

    @staticmethod
    def get_all(page=1, per_page=20, search='', section_id=None):
        # class_id filter deferred to Sprint 3 when Class model is available.
        query = Student.query.filter_by(is_active=True)

        if search:
            query = query.filter(
                or_(
                    Student.first_name.ilike(f'%{search}%'),
                    Student.last_name.ilike(f'%{search}%'),
                    Student.admission_no.ilike(f'%{search}%'),
                )
            )

        if section_id:
            query = query.join(
                StudentSection,
                (StudentSection.student_id == Student.id)
                & (StudentSection.section_id == section_id)
                & (StudentSection.is_current.is_(True)),
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
            },
        }

    # -------------------------------------------------------------------------
    # SMS-009 — Student profile
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_id(student_id):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None
        result = student.to_dict()
        # Attach current section info
        current_section = (
            StudentSection.query.filter_by(student_id=student_id, is_current=True).first()
        )
        result['current_section'] = current_section.to_dict() if current_section else None
        return result

    # -------------------------------------------------------------------------
    # SMS-007 — Student enrollment (T-007-02 / T-007-03)
    # -------------------------------------------------------------------------

    @staticmethod
    def create(data: dict):
        """
        Create a new student record.

        Raises 409 if admission_no is already taken.
        Expects pre-validated data (dates already parsed to date objects by Marshmallow).
        Returns (student_dict, None) on success or (None, error_dict) on failure.
        """
        if Student.query.filter_by(admission_no=data.get('admission_no')).first():
            return None, {
                'message': 'Admission number already exists',
                'status': 409,
            }

        student = Student(
            admission_no=data['admission_no'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            date_of_birth=data['date_of_birth'],
            gender=data['gender'],
            admission_date=data['admission_date'],
            blood_group=data.get('blood_group'),
            address=data.get('address'),
            phone=data.get('phone'),
            photo_url=data.get('photo_url'),
            user_id=data.get('user_id') or 1,
        )
        db.session.add(student)
        db.session.commit()
        return student.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-009 — Student update
    # -------------------------------------------------------------------------

    @staticmethod
    def update(student_id: int, data: dict, role: str = 'admin'):
        """
        Update student record.

        Admin can update any allowed field.
        Students can only update phone and address on their own record.
        Returns (student_dict, None) or (None, error_dict).
        """
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}

        if role == 'admin':
            allowed = [
                'first_name', 'last_name', 'date_of_birth', 'gender',
                'blood_group', 'address', 'phone', 'photo_url',
            ]
        else:
            # student self-service
            allowed = ['phone', 'address']

        for field in allowed:
            if field in data:
                setattr(student, field, data[field])

        db.session.commit()
        return student.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-013 — Soft delete
    # -------------------------------------------------------------------------

    @staticmethod
    def delete(student_id: int):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return False, {'message': 'Student not found', 'status': 404}
        student.is_active = False
        db.session.commit()
        return True, None

    # -------------------------------------------------------------------------
    # SMS-013 — Status / leaving date update
    # -------------------------------------------------------------------------

    @staticmethod
    def update_status(student_id: int, data: dict):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}
        student.status = data['status']
        if data.get('leaving_date'):
            student.leaving_date = data['leaving_date']
        db.session.commit()
        return student.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-010 — Parent linking
    # -------------------------------------------------------------------------

    @staticmethod
    def link_parent(student_id: int, parent_id: int, is_primary: bool):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}

        parent = Parent.query.filter_by(id=parent_id, is_active=True).first()
        if not parent:
            return None, {'message': 'Parent not found', 'status': 404}

        # Check if already linked
        existing = db.session.execute(
            db.select(student_parent).where(
                student_parent.c.student_id == student_id,
                student_parent.c.parent_id == parent_id,
            )
        ).first()
        if existing:
            return None, {'message': 'Parent already linked to this student', 'status': 409}

        db.session.execute(
            student_parent.insert().values(
                student_id=student_id,
                parent_id=parent_id,
                is_primary_contact=is_primary,
            )
        )
        db.session.commit()
        return parent.to_dict(), None

    @staticmethod
    def unlink_parent(student_id: int, parent_id: int):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return False, {'message': 'Student not found', 'status': 404}

        result = db.session.execute(
            student_parent.delete().where(
                student_parent.c.student_id == student_id,
                student_parent.c.parent_id == parent_id,
            )
        )
        if result.rowcount == 0:
            return False, {'message': 'Parent-student link not found', 'status': 404}

        db.session.commit()
        return True, None

    @staticmethod
    def get_parents(student_id: int):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}

        rows = db.session.execute(
            db.select(Parent, student_parent.c.is_primary_contact)
            .join(student_parent, Parent.id == student_parent.c.parent_id)
            .where(student_parent.c.student_id == student_id)
        ).all()

        result = []
        for parent, is_primary in rows:
            d = parent.to_dict()
            d['is_primary_contact'] = is_primary
            result.append(d)

        return result, None

    # -------------------------------------------------------------------------
    # SMS-011 — Student transfer
    # -------------------------------------------------------------------------

    @staticmethod
    def transfer(student_id: int, data: dict):
        """
        Transfer student to a new section.

        Closes the current StudentSection row and opens a new one.
        data keys: new_section_id (int), effective_date (date), reason (str).
        """
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}

        effective_date = data['effective_date']
        new_section_id = data['new_section_id']

        # Close current enrollment
        current = StudentSection.query.filter_by(
            student_id=student_id, is_current=True
        ).first()
        if current:
            current.is_current = False
            current.end_date = effective_date

        # Determine academic year from effective_date
        year = effective_date.year
        month = effective_date.month
        academic_year = f'{year}-{year + 1}' if month >= 6 else f'{year - 1}-{year}'

        new_enrollment = StudentSection(
            student_id=student_id,
            section_id=new_section_id,
            academic_year=academic_year,
            start_date=effective_date,
            is_current=True,
        )
        db.session.add(new_enrollment)
        db.session.commit()
        return new_enrollment.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-012 — Document upload
    # -------------------------------------------------------------------------

    @staticmethod
    def upload_document(student_id: int, document_type: str, file, uploaded_by: int):
        """
        Save uploaded document to disk and create StudentDocument record.

        Returns (doc_dict, None) or (None, error_dict).
        """
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}

        if not file or not file.filename:
            return None, {'message': 'No file provided', 'status': 400}

        if not _allowed_doc(file.filename):
            return None, {
                'message': 'Invalid file type. Allowed: PDF, JPG, JPEG, PNG',
                'status': 400,
            }

        # Read content once to check size (werkzeug stream)
        content = file.read()
        if len(content) > MAX_DOC_BYTES:
            return None, {'message': 'File exceeds maximum size of 5 MB', 'status': 400}

        upload_dir = os.path.join(
            current_app.config['UPLOAD_FOLDER'], 'students', str(student_id)
        )
        os.makedirs(upload_dir, exist_ok=True)

        ext = file.filename.rsplit('.', 1)[1].lower()
        safe_name = secure_filename(
            f"{document_type}_{secrets.token_hex(8)}.{ext}"
        )
        abs_path = os.path.join(upload_dir, safe_name)
        with open(abs_path, 'wb') as fh:
            fh.write(content)

        rel_path = os.path.join('students', str(student_id), safe_name)

        doc = StudentDocument(
            student_id=student_id,
            document_type=document_type,
            file_name=safe_name,
            file_path=rel_path,
            uploaded_by=uploaded_by,
            is_active=True,
        )
        db.session.add(doc)
        db.session.commit()
        return doc.to_dict(), None

    @staticmethod
    def list_documents(student_id: int):
        student = Student.query.filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': 'Student not found', 'status': 404}

        docs = StudentDocument.query.filter_by(
            student_id=student_id, is_active=True
        ).order_by(StudentDocument.created_at.desc()).all()
        return [d.to_dict() for d in docs], None

    @staticmethod
    def delete_document(student_id: int, doc_id: int):
        doc = StudentDocument.query.filter_by(
            id=doc_id, student_id=student_id, is_active=True
        ).first()
        if not doc:
            return False, {'message': 'Document not found', 'status': 404}
        doc.is_active = False
        db.session.commit()
        return True, None

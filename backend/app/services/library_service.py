from datetime import date

from sqlalchemy import or_

from app.utils.tenant import get_db
from app.models.library_book import LibraryBook
from app.models.book_issue import BookIssue
from app.models.student import Student

FINE_PER_DAY = 5  # ₹ per day overdue (configurable)
_ACTIVE_ISSUE_STATUSES = ('issued', 'overdue')


class LibraryService:

    # ----------------------------------------------------------- book CRUD

    @classmethod
    def create_book(cls, data: dict):
        db = get_db()
        isbn = data.get('isbn')
        if isbn:
            existing = db.query(LibraryBook).filter_by(isbn=isbn).first()
            if existing:
                return None, {'message': f'A book with ISBN {isbn} already exists', 'status': 409}

        total = data['total_copies']
        book = LibraryBook(
            isbn=isbn,
            title=data['title'],
            author=data['author'],
            publisher=data.get('publisher'),
            category=data.get('category'),
            total_copies=total,
            available_copies=total,
        )
        db.add(book)
        db.commit()
        return book.to_dict(), None

    @classmethod
    def get_books(cls, search=None, include_inactive=False):
        db = get_db()
        query = db.query(LibraryBook)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        if search:
            like = f'%{search}%'
            query = query.filter(or_(
                LibraryBook.title.ilike(like),
                LibraryBook.author.ilike(like),
                LibraryBook.isbn.ilike(like),
                LibraryBook.category.ilike(like),
            ))
        rows = query.order_by(LibraryBook.title.asc()).all()
        return [b.to_dict() for b in rows]

    @classmethod
    def get_book(cls, book_id: int):
        db = get_db()
        book = db.query(LibraryBook).filter_by(id=book_id).first()
        if not book:
            return None, {'message': f'Book {book_id} not found', 'status': 404}
        return book.to_dict(), None

    @classmethod
    def update_book(cls, book_id: int, data: dict):
        db = get_db()
        book = db.query(LibraryBook).filter_by(id=book_id).first()
        if not book:
            return None, {'message': f'Book {book_id} not found', 'status': 404}

        if data.get('isbn') is not None and data['isbn'] != book.isbn:
            clash = db.query(LibraryBook).filter(
                LibraryBook.isbn == data['isbn'], LibraryBook.id != book_id
            ).first()
            if clash:
                return None, {'message': f"ISBN {data['isbn']} already in use", 'status': 409}
            book.isbn = data['isbn']
        if data.get('title') is not None:
            book.title = data['title']
        if data.get('author') is not None:
            book.author = data['author']
        if 'publisher' in data:
            book.publisher = data['publisher']
        if 'category' in data:
            book.category = data['category']
        if data.get('total_copies') is not None:
            # Adjust availability by the delta so outstanding loans stay consistent.
            delta = data['total_copies'] - book.total_copies
            book.total_copies = data['total_copies']
            book.available_copies = max(0, book.available_copies + delta)
        if data.get('is_active') is not None:
            book.is_active = data['is_active']

        db.commit()
        return book.to_dict(), None

    @classmethod
    def delete_book(cls, book_id: int):
        db = get_db()
        book = db.query(LibraryBook).filter_by(id=book_id).first()
        if not book:
            return None, {'message': f'Book {book_id} not found', 'status': 404}

        active = db.query(BookIssue).filter(
            BookIssue.book_id == book_id,
            BookIssue.status.in_(_ACTIVE_ISSUE_STATUSES),
        ).count()
        if active:
            return None, {
                'message': 'Cannot delete a book with active issues',
                'status': 409,
            }

        book.is_active = False
        db.commit()
        return {'id': book_id, 'deleted': True}, None

    # ----------------------------------------------------- issue / return

    @classmethod
    def issue_book(cls, book_id: int, student_id: int, due_date, issued_by: int):
        db = get_db()
        book = db.query(LibraryBook).filter_by(id=book_id, is_active=True).first()
        if not book:
            return None, {'message': f'Book {book_id} not found', 'status': 404}

        student = db.query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {'message': f'Student {student_id} not found', 'status': 404}

        if book.available_copies < 1:
            return None, {'message': 'No copies available for this book', 'status': 409}

        issue = BookIssue(
            book_id=book_id,
            student_id=student_id,
            issued_date=date.today(),
            due_date=due_date,
            status='issued',
            fine_amount=0,
            issued_by=issued_by,
        )
        book.available_copies -= 1
        db.add(issue)
        db.commit()
        return issue.to_dict(), None

    @classmethod
    def return_book(cls, issue_id: int, returned_date=None):
        db = get_db()
        issue = db.query(BookIssue).filter_by(id=issue_id).first()
        if not issue:
            return None, {'message': f'Issue {issue_id} not found', 'status': 404}
        if issue.status == 'returned':
            return None, {'message': 'Book already returned', 'status': 409}

        returned_date = returned_date or date.today()
        issue.returned_date = returned_date
        issue.fine_amount = cls._calculate_fine(issue.due_date, returned_date)
        issue.status = 'returned'

        book = db.query(LibraryBook).filter_by(id=issue.book_id).first()
        if book:
            book.available_copies = min(book.total_copies, book.available_copies + 1)

        db.commit()
        return issue.to_dict(), None

    # ----------------------------------------------------- overdue (SMS-055)

    @classmethod
    def mark_overdue(cls, as_of=None):
        """Flag all still-out issues past their due date as 'overdue' and compute
        the running fine. Returns the number of issues updated."""
        db = get_db()
        as_of = as_of or date.today()
        rows = db.query(BookIssue).filter(
            BookIssue.status == 'issued',
            BookIssue.due_date < as_of,
        ).all()
        for issue in rows:
            issue.status = 'overdue'
            issue.fine_amount = cls._calculate_fine(issue.due_date, as_of)
        db.commit()
        return len(rows)

    @classmethod
    def get_overdue(cls, as_of=None):
        """Return all currently-overdue issues with up-to-date running fines."""
        db = get_db()
        as_of = as_of or date.today()
        rows = db.query(BookIssue).filter(
            BookIssue.status.in_(_ACTIVE_ISSUE_STATUSES),
            BookIssue.due_date < as_of,
            BookIssue.returned_date.is_(None),
        ).order_by(BookIssue.due_date.asc()).all()

        result = []
        for issue in rows:
            d = issue.to_dict()
            d['fine_amount'] = float(cls._calculate_fine(issue.due_date, as_of))
            d['days_overdue'] = (as_of - issue.due_date).days
            result.append(d)
        return result

    # ----------------------------------------------------- internal helpers

    @staticmethod
    def _calculate_fine(due_date, returned_date):
        if returned_date and due_date and returned_date > due_date:
            return (returned_date - due_date).days * FINE_PER_DAY
        return 0

from io import BytesIO
from datetime import date, datetime

from app.utils.tenant import get_db
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment
from app.models.discount import Discount
from app.models.student import Student
from app.models.student_section import StudentSection
from app.models.section import Section


class FeeService:

    @classmethod
    def generate_records_for_class(cls, fee_structure_id: int):
        """
        Generate FeeRecord rows for every active student currently enrolled
        in the class linked to the given FeeStructure.

        Returns:
            (result_dict, None)   on success — result_dict has keys:
                                  generated, skipped, total_students
            (None, error_dict)    on failure — error_dict has keys:
                                  message, status
        """
        db = get_db()

        # 1. Load the fee structure
        fs = db.query(FeeStructure).filter_by(id=fee_structure_id).first()
        if not fs:
            return None, {
                'message': f'FeeStructure {fee_structure_id} not found',
                'status': 404,
            }

        # 2. Find all active students currently enrolled in the class.
        #    Join: StudentSection → Section (class_id match) → Student (is_active)
        active_students = (
            db.query(Student)
            .join(StudentSection, StudentSection.student_id == Student.id)
            .join(Section, Section.id == StudentSection.section_id)
            .filter(
                StudentSection.is_current == True,  # noqa: E712
                Section.class_id == fs.class_id,
                Student.is_active == True,           # noqa: E712
            )
            .all()
        )

        # 3. Fetch the set of student_ids that already have a record for this
        #    fee structure so we can skip them without a per-student query.
        existing_student_ids = {
            row.student_id
            for row in db.query(FeeRecord.student_id).filter_by(
                fee_structure_id=fee_structure_id
            ).all()
        }

        generated = 0
        skipped = 0

        for student in active_students:
            if student.id in existing_student_ids:
                skipped += 1
                continue

            record = FeeRecord(
                student_id=student.id,
                fee_structure_id=fee_structure_id,
                amount=fs.amount,
                discount=0,
                net_amount=fs.amount,
                due_date=fs.due_date,
                status='pending',
            )
            db.add(record)
            generated += 1

        # 4. Single commit for all new rows
        if generated > 0:
            db.commit()

        return {
            'generated': generated,
            'skipped': skipped,
            'total_students': generated + skipped,
        }, None

    @classmethod
    def record_payment(cls, data: dict) -> tuple:
        """
        Record a payment against a FeeRecord.

        Returns:
            (result_dict, None)  on success
            (None, error_dict)   on failure — error_dict has keys: message, status
        """
        db = get_db()

        # 1. Load the fee record
        fee_record = db.query(FeeRecord).filter_by(id=data['fee_record_id']).first()
        if not fee_record:
            return None, {
                'message': f"FeeRecord {data['fee_record_id']} not found",
                'status': 404,
            }

        # 2. Reject waived records
        if fee_record.status == 'waived':
            return None, {
                'message': 'Cannot record payment against a waived fee record',
                'status': 422,
            }

        # 3. Sum all existing payments for this fee record
        existing_payments = db.query(FeePayment).filter_by(
            fee_record_id=fee_record.id
        ).all()
        total_already_paid = sum(p.amount_paid for p in existing_payments)

        # 4. Check for overpayment
        amount_paid = data['amount_paid']
        if total_already_paid + amount_paid > fee_record.net_amount:
            return None, {
                'message': 'Amount exceeds balance due',
                'status': 422,
            }

        # 5. Generate receipt number: REC-{year}-{seq:04d}
        payment_year = data['payment_date'].year
        year_count = (
            db.query(FeePayment)
            .filter(FeePayment.receipt_no.like(f'REC-{payment_year}-%'))
            .count()
        )
        receipt_no = f'REC-{payment_year}-{year_count + 1:04d}'

        # 6. Create FeePayment
        payment = FeePayment(
            fee_record_id=fee_record.id,
            amount_paid=amount_paid,
            payment_method=data['payment_method'],
            payment_date=data['payment_date'],
            receipt_no=receipt_no,
            transaction_reference=data.get('transaction_reference'),
            remarks=data.get('remarks'),
            collected_by=data.get('collected_by'),
        )
        db.add(payment)

        # 7. Update fee record status
        total_now = total_already_paid + amount_paid
        if total_now >= fee_record.net_amount:
            fee_record.status = 'paid'
        else:
            fee_record.status = 'partial'

        # 8. Commit
        db.commit()

        # 9. Return result
        balance_due = float(fee_record.net_amount - total_now)
        return {
            'payment_id': payment.id,
            'receipt_no': receipt_no,
            'amount_paid': float(payment.amount_paid),
            'balance_due': balance_due,
        }, None

    @classmethod
    def get_fee_records(cls, student_id: int) -> list:
        """
        Return all FeeRecord rows for a student with embedded payments.
        """
        db = get_db()
        records = db.query(FeeRecord).filter_by(student_id=student_id).all()
        return [
            {
                **record.to_dict(),
                'payments': [p.to_dict() for p in record.payments],
            }
            for record in records
        ]

    @classmethod
    def get_defaulters(cls, class_id: int = None) -> list:
        """
        Return overdue fee records — FeeRecords with status 'pending' or
        'partial' whose due_date is strictly before today.

        Args:
            class_id: Optional filter; when provided, only records whose
                      FeeStructure belongs to this class are returned.

        Returns:
            List of dicts with keys:
                student_id, student_name, roll_number,
                fee_record_id, fee_type, due_date, net_amount,
                total_paid, balance_due, days_overdue
        """
        db = get_db()
        today = date.today()

        query = (
            db.query(FeeRecord, FeeStructure, Student)
            .join(FeeStructure, FeeStructure.id == FeeRecord.fee_structure_id)
            .join(Student, Student.id == FeeRecord.student_id)
            .filter(
                FeeRecord.status.in_(['pending', 'partial']),
                FeeRecord.due_date < today,
            )
        )

        if class_id is not None:
            query = query.filter(FeeStructure.class_id == class_id)

        rows = query.all()

        result = []
        for fee_record, fee_structure, student in rows:
            # Sum all payments recorded against this fee record
            payments = db.query(FeePayment).filter_by(
                fee_record_id=fee_record.id
            ).all()
            total_paid = sum(float(p.amount_paid) for p in payments)
            net_amount = float(fee_record.net_amount)
            balance_due = round(net_amount - total_paid, 2)
            days_overdue = (today - fee_record.due_date).days

            result.append({
                'student_id': student.id,
                'student_name': f'{student.first_name} {student.last_name}',
                'roll_number': getattr(student, 'roll_number', None),
                'fee_record_id': fee_record.id,
                'fee_type': fee_structure.fee_type,
                'due_date': fee_record.due_date.isoformat(),
                'net_amount': net_amount,
                'total_paid': round(total_paid, 2),
                'balance_due': balance_due,
                'days_overdue': days_overdue,
            })

        return result

    @classmethod
    def apply_discount(cls, fee_record_id: int, discount_data: dict, approved_by_user_id: int) -> tuple:
        """
        Apply a discount to a fee record.

        - Raises 404 if fee_record not found.
        - Raises 422 if record status is 'paid' or 'waived'.
        - Creates a Discount row linked to the fee_record.
        - Recalculates fee_record.net_amount = max(0, amount_due - sum of all discounts).
        - If net_amount <= total amount already paid, flips status to 'paid'.
        - Commits and returns (discount_dict, None) on success.
        - Returns (None, error_dict) on failure.
        """
        db = get_db()

        fee_record = db.query(FeeRecord).filter_by(id=fee_record_id).first()
        if not fee_record:
            return None, {
                'message': f'FeeRecord {fee_record_id} not found',
                'status': 404,
            }

        if fee_record.status in ('paid', 'waived'):
            return None, {
                'message': f'Cannot apply discount to a fee record with status "{fee_record.status}"',
                'status': 422,
            }

        discount = Discount(
            fee_record_id=fee_record_id,
            student_id=fee_record.student_id,
            discount_type=discount_data['discount_type'],
            amount=discount_data['amount'],
            reason=discount_data.get('reason'),
            approved_by=approved_by_user_id,
            approved_at=datetime.utcnow(),
        )
        db.add(discount)
        db.flush()  # assigns discount.id without committing

        # Recalculate net_amount: original amount_due minus sum of ALL discounts for this record
        all_discounts = db.query(Discount).filter_by(fee_record_id=fee_record_id).all()
        total_discounts = sum(float(d.amount) for d in all_discounts)
        new_net = max(0.0, float(fee_record.amount) - total_discounts)
        fee_record.net_amount = new_net

        # If fully covered by discounts + any prior payments, mark paid
        existing_payments = db.query(FeePayment).filter_by(fee_record_id=fee_record_id).all()
        total_paid = sum(float(p.amount_paid) for p in existing_payments)
        if new_net <= total_paid:
            fee_record.status = 'paid'

        db.commit()
        return discount.to_dict(), None

    @classmethod
    def get_fee_record(cls, fee_record_id: int) -> tuple:
        """
        Return a single FeeRecord with its discounts list embedded.

        Returns (result_dict, None) on success or (None, error_dict) on failure.
        """
        db = get_db()

        fee_record = db.query(FeeRecord).filter_by(id=fee_record_id).first()
        if not fee_record:
            return None, {
                'message': f'FeeRecord {fee_record_id} not found',
                'status': 404,
            }

        discounts = db.query(Discount).filter_by(fee_record_id=fee_record_id).all()
        result = {
            **fee_record.to_dict(),
            'discounts': [d.to_dict() for d in discounts],
        }
        return result, None

    @classmethod
    def generate_receipt_pdf(cls, payment_id: int) -> tuple:
        """
        Render fee_receipt.html and convert to PDF bytes via xhtml2pdf.

        Returns (pdf_bytes, None) on success or (None, error_dict) on failure.
        error_dict has keys: message, status
        """
        from datetime import date
        from flask import render_template
        from xhtml2pdf import pisa

        db = get_db()

        # 1. Load FeePayment
        payment = db.query(FeePayment).filter_by(id=payment_id).first()
        if not payment:
            return None, {
                'message': f'FeePayment {payment_id} not found',
                'status': 404,
            }

        # 2. Load FeeRecord
        fee_record = db.query(FeeRecord).filter_by(id=payment.fee_record_id).first()
        if not fee_record:
            return None, {
                'message': f'FeeRecord {payment.fee_record_id} not found',
                'status': 404,
            }

        # 3. Load FeeStructure
        fee_structure = db.query(FeeStructure).filter_by(
            id=fee_record.fee_structure_id
        ).first()
        if not fee_structure:
            return None, {
                'message': f'FeeStructure {fee_record.fee_structure_id} not found',
                'status': 404,
            }

        # 4. Load Student
        student = db.query(Student).filter_by(id=fee_record.student_id).first()
        if not student:
            return None, {
                'message': f'Student {fee_record.student_id} not found',
                'status': 404,
            }

        # 5. Calculate balance due
        all_payments = db.query(FeePayment).filter_by(
            fee_record_id=fee_record.id
        ).all()
        total_paid = sum(float(p.amount_paid) for p in all_payments)
        balance_due = float(fee_record.net_amount) - total_paid

        # 6. Render template
        try:
            html = render_template(
                'fee_receipt.html',
                payment=payment,
                fee_record=fee_record,
                fee_structure=fee_structure,
                student=student,
                balance_due=balance_due,
                generated_date=date.today().isoformat(),
            )
        except Exception as exc:
            return None, {
                'message': f'Template rendering failed: {exc}',
                'status': 500,
            }

        # 7. Convert HTML to PDF bytes
        try:
            buffer = BytesIO()
            pisa_result = pisa.CreatePDF(html, dest=buffer)
            if pisa_result.err:
                return None, {
                    'message': 'PDF generation failed',
                    'status': 500,
                }
            return buffer.getvalue(), None
        except Exception as exc:
            return None, {
                'message': f'PDF generation error: {exc}',
                'status': 500,
            }

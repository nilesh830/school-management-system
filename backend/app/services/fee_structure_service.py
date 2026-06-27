from app.utils.tenant import get_db
from app.models.fee_structure import FeeStructure
from app.models.class_ import Class
from app.models.academic_year import AcademicYear


class FeeStructureService:

    @classmethod
    def create_fee_structure(cls, data: dict):
        """
        Create a new fee structure entry.

        Returns (fee_structure_dict, None) on success or (None, error_dict) on failure.
        error_dict always contains 'message' and 'status' keys.
        """
        db = get_db()

        class_ = db.query(Class).filter_by(id=data["class_id"]).first()
        if not class_:
            return None, {"message": f"Class {data['class_id']} not found", "status": 404}

        academic_year = db.query(AcademicYear).filter_by(id=data["academic_year_id"]).first()
        if not academic_year:
            return None, {
                "message": f"AcademicYear {data['academic_year_id']} not found",
                "status": 404,
            }

        fs = FeeStructure(
            class_id=data["class_id"],
            academic_year_id=data["academic_year_id"],
            fee_type=data["fee_type"],
            amount=data["amount"],
            due_date=data.get("due_date"),
            is_recurring=data.get("is_recurring", False),
            frequency=data.get("frequency", "one_time"),
        )
        db.add(fs)
        db.commit()
        return fs.to_dict(), None

    @classmethod
    def get_fee_structures(cls, class_id=None, academic_year_id=None):
        """
        Return a list of active fee structure dicts, optionally filtered.
        """
        db = get_db()
        query = db.query(FeeStructure).filter_by(is_active=True)
        if class_id is not None:
            query = query.filter_by(class_id=class_id)
        if academic_year_id is not None:
            query = query.filter_by(academic_year_id=academic_year_id)
        results = query.order_by(FeeStructure.created_at.desc()).all()
        return [fs.to_dict() for fs in results]

    @classmethod
    def get_fee_structure(cls, fee_structure_id: int):
        """
        Fetch a single fee structure by id.

        Returns (fs_dict, None) or (None, {'message': ..., 'status': 404}).
        """
        db = get_db()
        fs = db.query(FeeStructure).filter_by(id=fee_structure_id).first()
        if not fs:
            return None, {
                "message": f"FeeStructure {fee_structure_id} not found",
                "status": 404,
            }
        return fs.to_dict(), None

    @classmethod
    def update_fee_structure(cls, fee_structure_id: int, data: dict):
        """
        Update mutable fields of a fee structure.

        Only fields explicitly present with non-None values are updated.
        Returns (fs_dict, None) or (None, error_dict).
        """
        db = get_db()
        fs = db.query(FeeStructure).filter_by(id=fee_structure_id).first()
        if not fs:
            return None, {
                "message": f"FeeStructure {fee_structure_id} not found",
                "status": 404,
            }

        if data.get("fee_type") is not None:
            fs.fee_type = data["fee_type"]
        if data.get("amount") is not None:
            fs.amount = data["amount"]
        # due_date may legitimately be set to None (clear it), so check key presence
        if "due_date" in data:
            fs.due_date = data["due_date"]
        if data.get("is_recurring") is not None:
            fs.is_recurring = data["is_recurring"]
        if data.get("frequency") is not None:
            fs.frequency = data["frequency"]
        if data.get("is_active") is not None:
            fs.is_active = data["is_active"]

        db.commit()
        return fs.to_dict(), None

    @classmethod
    def delete_fee_structure(cls, fee_structure_id: int):
        """
        Soft-delete a fee structure by setting is_active=False.

        Returns ({'id': ..., 'deleted': True}, None) or (None, error_dict).
        """
        db = get_db()
        fs = db.query(FeeStructure).filter_by(id=fee_structure_id).first()
        if not fs:
            return None, {
                "message": f"FeeStructure {fee_structure_id} not found",
                "status": 404,
            }

        fs.is_active = False
        db.commit()
        return {"id": fee_structure_id, "deleted": True}, None

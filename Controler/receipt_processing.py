from flask import request
from db_connection import SessionLocal
from Service.receipt_service import ReceiptService

class ReceiptController:

    def upload_receipt(self):
        receipt_file = request.files.get("receipt")
        if receipt_file is None:
            receipt_list = request.files.getlist("receipt")
            if receipt_list:
                receipt_file = receipt_list[0]
        if receipt_file is None and request.files:
            receipt_file = next(iter(request.files.values()))

        if receipt_file is None:
            return {"error": "No receipt file provided", "request_files": list(request.files.keys())}, 400

        user_id = request.form.get("user_id") or request.args.get("user_id")
        if not user_id:
            return {"error": "user_id is required"}, 400

        try:
            user_id = int(user_id)
        except ValueError:
            return {"error": "user_id must be an integer"}, 400

        session = SessionLocal()
        service = ReceiptService(session)
        try:
            result = service.process_receipt(receipt_file, user_id)
            return result
        except ValueError as exc:
            session.rollback()
            return {"error": str(exc)}, 400
        except Exception as exc:
            session.rollback()
            return {"error": str(exc)}, 500
        finally:
            session.close()
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from werkzeug.datastructures import FileStorage
from Service.receipt_service import ReceiptService
from models.receipts import Receipt
from models.Reception_products import ReceptionProducts
from models.Products import Product
import io
import os

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)
Session = sessionmaker(bind=engine)

receipt_bp = Blueprint('receipts', __name__, url_prefix='/receipts')

# -----------------------------
# CREATE RECEIPT
# -----------------------------
@receipt_bp.route('', methods=['POST'])
def create():
    session = Session()
    try:
        data = request.get_json()
        if not data or "user_id" not in data:
            return jsonify({"error": "user_id is required"}), 400

        user_id = data["user_id"]
        service = ReceiptService(session)
        receipt_id = service.create_receipt(user_id=user_id)
        return jsonify({"id": receipt_id})
    finally:
        session.close()

@receipt_bp.route('/upload', methods=['POST'])
def upload():
    session = Session()
    try:
        receipt_file = request.files.get("receipt")
        receipt_path = request.form.get("receipt") if not receipt_file else None
        user_id = request.form.get("user_id") or request.args.get("user_id")

        if receipt_file is None:
            if receipt_path:
                receipt_path = receipt_path.strip()
                try:
                    with open(receipt_path, 'rb') as f:
                        raw_bytes = f.read()
                    receipt_file = FileStorage(
                        stream=io.BytesIO(raw_bytes),
                        filename=os.path.basename(receipt_path),
                        content_type='application/octet-stream'
                    )
                except Exception as exc:
                    return jsonify({
                        "error": "No receipt file provided and fallback path failed",
                        "receipt_path": receipt_path,
                        "exception": str(exc),
                        "content_type": request.content_type,
                        "request_form": list(request.form.keys()),
                        "request_files": list(request.files.keys()),
                        "request_values": list(request.values.keys())
                    }), 400

        if receipt_file is None:
            return jsonify({
                "error": "No receipt file provided",
                "content_type": request.content_type,
                "request_form": list(request.form.keys()),
                "request_files": list(request.files.keys()),
                "request_values": list(request.values.keys()),
                "receipt_filename": getattr(receipt_file, "filename", None)
            }), 400
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"error": "user_id must be an integer"}), 400

        service = ReceiptService(session)
        result = service.process_receipt(receipt_file, user_id)
        return jsonify(result)
    except ValueError as exc:
        session.rollback()
        try:
            receipt_file.stream.seek(0)
            raw_bytes = receipt_file.read()
            content_length = len(raw_bytes or b"")
        except Exception:
            content_length = None
        return jsonify({
            "error": str(exc),
            "receipt_meta": {
                "filename": receipt_file.filename,
                "content_type": receipt_file.content_type,
                "content_length": content_length
            }
        }), 400
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()

# -----------------------------
# UPDATE RECEIPT
# -----------------------------
@receipt_bp.route('/<int:receipt_id>', methods=['PATCH'])
def update_receipt(receipt_id):
    session = Session()
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")

        if user_id is None:
            return jsonify({"error": "Nothing to update"}), 400

        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"error": "user_id must be an integer"}), 400

        service = ReceiptService(session)
        result = service.update_receipt(receipt_id, user_id=user_id)
        return jsonify(result)
    except ValueError as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()

# -----------------------------
# UPDATE RECEIPT PRODUCT
# -----------------------------
@receipt_bp.route('/<int:receipt_id>/products/<int:item_id>', methods=['PATCH'])
def update_receipt_product(receipt_id, item_id):
    session = Session()
    try:
        data = request.get_json() or {}
        product_id = data.get("product_id")
        amount = data.get("amount")

        item = session.query(ReceptionProducts).get(item_id)
        if not item or item.receipts_id != receipt_id:
            return jsonify({"error": "Receipt product item not found"}), 404

        if product_id is not None:
            try:
                product_id = int(product_id)
            except ValueError:
                return jsonify({"error": "product_id must be an integer"}), 400

        if amount is not None:
            try:
                amount = int(amount)
            except ValueError:
                return jsonify({"error": "amount must be an integer"}), 400

        service = ReceiptService(session)
        result = service.update_reception_product(item_id, product_id=product_id, amount=amount)
        return jsonify(result)
    except ValueError as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()

# -----------------------------
# PROCESS RECEIPT + PRODUCTS
# -----------------------------
@receipt_bp.route('/process/<int:receipt_id>', methods=['POST'])
def process_receipt(receipt_id):
    session = Session()
    try:
        data = request.json
        products = data.get("products", [])

        service = ReceiptService(session)
        result = service.save_receipt_products(receipt_id, products)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        session.close()

# -----------------------------
# GET BY USER ID
# -----------------------------
@receipt_bp.route('/user/<int:user_id>', methods=['GET'])
def get_by_user_id(user_id):
    session = Session()
    try:
        items = session.query(Receipt).filter(Receipt.user_id == user_id).all()
        if not items:
            return jsonify({"error": "not found"}), 404

        return jsonify([
            {
                "id": item.id,
                "user_id": item.user_id
            } for item in items
        ])
    finally:
        session.close()

# -----------------------------
# DELETE RECEIPT
# -----------------------------
@receipt_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()
    try:
        item = session.query(Receipt).filter(Receipt.id == id).first()
        if not item:
            return jsonify({"error": "not found"}), 404

        session.delete(item)
        session.commit()
        return jsonify({"message": "deleted"})
    finally:
        session.close()

# -----------------------------
# GET PRODUCTS BY RECEIPT ID
# -----------------------------
@receipt_bp.route('/<int:receipt_id>/products', methods=['GET'])
def get_products_by_receipt(receipt_id):
    session = Session()
    try:
        items = session.query(
            ReceptionProducts,
            Product
        ).join(
            Product,
            ReceptionProducts.products_id == Product.id
        ).filter(
            ReceptionProducts.receipts_id == receipt_id
        ).all()

        return jsonify([
            {
                "id": reception.id,
                "receipt_id": reception.receipts_id,
                "product_id": product.code if product and product.code else product.id,
                "product_code": product.code,
                "product_name": product.name,
                "volume_ml": product.volume_ml,
                "amount": reception.amount
            }
            for reception, product in items
        ])
    finally:
        session.close()

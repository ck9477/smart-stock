from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from Service.receipt import ReceiptService
from models.receipts import Receipt

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
        data = request.get_json()  # מבטיח שמקבלים JSON

        # בדיקה אם user_id קיים
        if not data or "user_id" not in data:
            return jsonify({"error": "user_id is required"}), 400

        user_id = data["user_id"]
        service = ReceiptService(session)
        receipt_id = service.create_receipt(user_id=user_id)

        return jsonify({"id": receipt_id})

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
        result = service.process_receipt(receipt_id, products)

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
from models.Reception_products import ReceptionProducts


from models.Products import Product
from models.Reception_products import ReceptionProducts


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
                "product_id": product.id,
                "product_name": product.name,
                "volume_ml": product.volume_ml,
                "amount": reception.amount
            }
            for reception, product in items
        ])

    finally:
        session.close()
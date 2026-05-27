from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.receipts import Receipt

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)

Session = sessionmaker(bind=engine)

receipt_bp = Blueprint('receipts', __name__, url_prefix='/receipts')


# CREATE
@receipt_bp.route('', methods=['POST'])
def create():
    session = Session()
    data = request.json

    obj = Receipt(user_id=data["user_id"])
    session.add(obj)
    session.commit()
    session.refresh(obj)
    session.close()

    return jsonify({"id": obj.id})


# GET ALL
@receipt_bp.route('', methods=['GET'])
def get_all():
    session = Session()
    items = session.query(Receipt).all()
    session.close()

    return jsonify([
        {"id": i.id, "user_id": i.user_id}
        for i in items
    ])


# GET BY ID
@receipt_bp.route('/<int:id>', methods=['GET'])
def get_by_id(id):
    session = Session()

    item = session.query(Receipt).filter(Receipt.id == id).first()
    session.close()

    if not item:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": item.id,
        "user_id": item.user_id
    })


# UPDATE
@receipt_bp.route('/<int:id>', methods=['PUT'])
def update(id):
    session = Session()
    data = request.json

    item = session.query(Receipt).filter(Receipt.id == id).first()

    if not item:
        session.close()
        return jsonify({"error": "not found"}), 404

    item.user_id = data.get("user_id", item.user_id)

    session.commit()
    session.close()

    return jsonify({"message": "updated"})


# DELETE
@receipt_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()

    item = session.query(Receipt).filter(Receipt.id == id).first()

    if not item:
        session.close()
        return jsonify({"error": "not found"}), 404

    session.delete(item)
    session.commit()
    session.close()

    return jsonify({"message": "deleted"})
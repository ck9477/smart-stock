from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.Reception_products import ReceptionProducts

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)

Session = sessionmaker(bind=engine)

reception_bp = Blueprint(
    'reception_products',
    __name__,
    url_prefix='/reception-products'
)


# CREATE
@reception_bp.route('', methods=['POST'])
def create():
    session = Session()
    data = request.json

    obj = ReceptionProducts(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    session.close()

    return jsonify({"id": obj.id})


# GET ALL
@reception_bp.route('', methods=['GET'])
def get_all():
    session = Session()
    items = session.query(ReceptionProducts).all()
    session.close()

    return jsonify([
        {
            "id": i.id,
            "receipts_id": i.receipts_id,
            "products_id": i.products_id,
            "amount": i.amount
        }
        for i in items
    ])


# GET BY ID
@reception_bp.route('/<int:id>', methods=['GET'])
def get_by_id(id):
    session = Session()

    item = session.query(ReceptionProducts)\
        .filter(ReceptionProducts.id == id)\
        .first()

    session.close()

    if not item:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": item.id,
        "receipts_id": item.receipts_id,
        "products_id": item.products_id,
        "amount": item.amount
    })


# DELETE
@reception_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()

    item = session.query(ReceptionProducts)\
        .filter(ReceptionProducts.id == id)\
        .first()

    if not item:
        session.close()
        return jsonify({"error": "not found"}), 404

    session.delete(item)
    session.commit()
    session.close()

    return jsonify({"message": "deleted"})
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.shopping_list import ShoppingList

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)
Session = sessionmaker(bind=engine)

shopping_bp = Blueprint('shopping', __name__, url_prefix='/shopping')


# CREATE
@shopping_bp.route('', methods=['POST'])
def create():
    session = Session()
    data = request.json

    obj = ShoppingList(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    session.close()

    return jsonify({"id": obj.id})


# GET ALL
@shopping_bp.route('', methods=['GET'])
def get_all():
    session = Session()
    items = session.query(ShoppingList).all()
    session.close()

    return jsonify([
        {
            "id": i.id,
            "product_id": i.product_id,
            "amount": i.amount,
            "range_enum": i.range_enum
        }
        for i in items
    ])


# GET BY ID
@shopping_bp.route('/<int:id>', methods=['GET'])
def get_by_id(id):
    session = Session()
    item = session.query(ShoppingList).filter(ShoppingList.id == id).first()
    session.close()

    if not item:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": item.id,
        "product_id": item.product_id,
        "amount": item.amount,
        "range_enum": item.range_enum
    })


# UPDATE
@shopping_bp.route('/<int:id>', methods=['PUT'])
def update(id):
    session = Session()
    data = request.json

    item = session.query(ShoppingList).filter(ShoppingList.id == id).first()

    if not item:
        session.close()
        return jsonify({"error": "not found"}), 404

    item.product_id = data.get("product_id", item.product_id)
    item.amount = data.get("amount", item.amount)
    item.range_enum = data.get("range_enum", item.range_enum)

    session.commit()
    session.close()

    return jsonify({"message": "updated"})


# DELETE
@shopping_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()

    item = session.query(ShoppingList).filter(ShoppingList.id == id).first()

    if not item:
        session.close()
        return jsonify({"error": "not found"}), 404

    session.delete(item)
    session.commit()
    session.close()

    return jsonify({"message": "deleted"})
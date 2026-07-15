from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.Products import Product

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)

Session = sessionmaker(bind=engine)

product_bp = Blueprint('products', __name__, url_prefix='/products')


# -------------------------------
# CREATE
# -------------------------------
@product_bp.route('', methods=['POST'])
def create():
    session = Session()
    data = request.json

    obj = Product(
        name=data["name"],
        category_id=data["category_id"],
        volume_ml=data.get("volume_ml"),
        code=data.get("barcode")
    )

    session.add(obj)
    session.commit()
    session.refresh(obj)

    response = {
        "id": obj.id,
        "name": obj.name,
        "barcode": obj.code,
        "category_id": obj.category_id,
        "volume_ml": obj.volume_ml
    }

    session.close()

    return jsonify(response)


# -------------------------------
# GET ALL
# -------------------------------
@product_bp.route('', methods=['GET'])
def get_all():
    session = Session()

    items = session.query(Product).all()

    response = [
    {
        "id": i.id,
        "name": i.name,
        "barcode": i.code,
        "category": i.category.name if i.category else None,
        "volume_ml": i.volume_ml
    }
    for i in items
]

    session.close()

    return jsonify(response)


# -------------------------------
# GET BY ID
# -------------------------------
@product_bp.route('/<int:id>', methods=['GET'])
def get_by_id(id):
    session = Session()

    obj = session.query(Product).filter(Product.id == id).first()

    if not obj:
        session.close()
        return jsonify({"error": "not found"}), 404

    response = {
        "id": obj.id,
        "name": obj.name,
        "barcode": obj.code,
        "category_id": obj.category_id,
        "volume_ml": obj.volume_ml
    }

    session.close()

    return jsonify(response)


# -------------------------------
# UPDATE
# -------------------------------
@product_bp.route('/<int:id>', methods=['PUT'])
def update(id):
    session = Session()

    data = request.json

    obj = session.query(Product).filter(Product.id == id).first()

    if not obj:
        session.close()
        return jsonify({"error": "not found"}), 404

    obj.name = data.get("name", obj.name)
    obj.category_id = data.get("category_id", obj.category_id)
    obj.volume_ml = data.get("volume_ml", obj.volume_ml)
    obj.code = data.get("barcode", obj.code)

    session.commit()

    response = {
        "id": obj.id,
        "name": obj.name,
        "barcode": obj.code,
        "category_id": obj.category_id,
        "volume_ml": obj.volume_ml
    }

    session.close()

    return jsonify(response)


# -------------------------------
# DELETE
# -------------------------------
@product_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()

    obj = session.query(Product).filter(Product.id == id).first()

    if not obj:
        session.close()
        return jsonify({"error": "not found"}), 404

    session.delete(obj)
    session.commit()

    session.close()

    return jsonify({"message": "deleted"})
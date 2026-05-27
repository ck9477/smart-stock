from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.Products import Product

engine = create_engine('mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server')
Session = sessionmaker(bind=engine)

product_bp = Blueprint('products', __name__, url_prefix='/products')


@product_bp.route('', methods=['POST'])
def create():
    session = Session()
    data = request.json

    obj = Product(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    session.close()

    return jsonify({"id": obj.id})


@product_bp.route('', methods=['GET'])
def get_all():
    session = Session()
    items = session.query(Product).all()
    session.close()

    return jsonify([{"id": i.id, "name": i.name, "category_id": i.category_id} for i in items])


@product_bp.route('/<int:id>', methods=['GET'])
def get_by_id(id):
    session = Session()
    obj = session.query(Product).filter(Product.id == id).first()
    session.close()

    if not obj:
        return jsonify({"error": "not found"}), 404

    return jsonify({"id": obj.id, "name": obj.name, "category_id": obj.category_id})


@product_bp.route('/<int:id>', methods=['PUT'])
def update(id):
    session = Session()
    data = request.json

    obj = session.query(Product).filter(Product.id == id).first()
    if not obj:
        return jsonify({"error": "not found"}), 404

    obj.name = data.get("name", obj.name)
    obj.category_id = data.get("category_id", obj.category_id)

    session.commit()
    session.close()

    return jsonify({"message": "updated"})


@product_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()

    obj = session.query(Product).filter(Product.id == id).first()
    if not obj:
        return jsonify({"error": "not found"}), 404

    session.delete(obj)
    session.commit()
    session.close()

    return jsonify({"message": "deleted"})
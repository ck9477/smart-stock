from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.category import Category
from config import get_sqlalchemy_connection_string

engine = create_engine(get_sqlalchemy_connection_string())
Session = sessionmaker(bind=engine)

category_bp = Blueprint('category', __name__, url_prefix='/category')


# CREATE
@category_bp.route('', methods=['POST'])
def create_category():
    session = Session()
    data = request.json

    obj = Category(
        name=data["name"],
        Range_id=data["range_id"]
    )

    session.add(obj)
    session.commit()
    session.refresh(obj)

    session.close()
    return jsonify({"id": obj.id})


# GET ALL
@category_bp.route('', methods=['GET'])
def get_categories():
    session = Session()
    items = session.query(Category).all()
    session.close()

    return jsonify([
        {"id": c.id, "name": c.name, "range_id": c.Range_id}
        for c in items
    ])


# GET BY ID
@category_bp.route('/<int:id>', methods=['GET'])
def get_category(id):
    session = Session()
    obj = session.query(Category).filter(Category.id == id).first()
    session.close()

    if not obj:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": obj.id,
        "name": obj.name,
        "range_id": obj.Range_id
    })


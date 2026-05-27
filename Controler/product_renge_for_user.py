from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.Product_range_for_the_user import ProductRangeForTheUser

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)

Session = sessionmaker(bind=engine)

product_range_bp = Blueprint(
    'product_range_for_user',
    __name__,
    url_prefix='/product-range-for-user'
)


# CREATE
@product_range_bp.route('', methods=['POST'])
def create_product_range():
    session = Session()
    data = request.json

    try:
        if not data:
            return jsonify({"error": "no json body"}), 400

        if not data.get("user_id") or not data.get("Products_id") or not data.get("Range_id"):
            return jsonify({"error": "missing required fields"}), 400

        item = ProductRangeForTheUser(
            user_id=data.get("user_id"),
            Products_id=data.get("Products_id"),
            Range_id=data.get("Range_id")
        )

        session.add(item)
        session.commit()
        session.refresh(item)

        return jsonify({"id": item.id})

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        session.close()


# GET ALL
@product_range_bp.route('', methods=['GET'])
def get_product_ranges():
    session = Session()

    try:
        items = session.query(ProductRangeForTheUser).all()

        return jsonify([
            {
                "id": i.id,
                "user_id": i.user_id,
                "Products_id": i.Products_id,
                "Range_id": i.Range_id
            }
            for i in items
        ])

    finally:
        session.close()


# GET BY ID
@product_range_bp.route('/<int:id>', methods=['GET'])
def get_product_range(id):
    session = Session()

    try:
        item = session.query(ProductRangeForTheUser).filter(
            ProductRangeForTheUser.id == id
        ).first()

        if not item:
            return jsonify({"error": "not found"}), 404

        return jsonify({
            "id": item.id,
            "user_id": item.user_id,
            "Products_id": item.Products_id,
            "Range_id": item.Range_id
        })

    finally:
        session.close()


# UPDATE
@product_range_bp.route('/<int:id>', methods=['PUT'])
def update_product_range(id):
    session = Session()
    data = request.json

    try:
        item = session.query(ProductRangeForTheUser).filter(
            ProductRangeForTheUser.id == id
        ).first()

        if not item:
            return jsonify({"error": "not found"}), 404

        item.user_id = data.get("user_id", item.user_id)
        item.Products_id = data.get("Products_id", item.Products_id)
        item.Range_id = data.get("Range_id", item.Range_id)

        session.commit()

        return jsonify({"message": "updated"})

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        session.close()


# DELETE
@product_range_bp.route('/<int:id>', methods=['DELETE'])
def delete_product_range(id):
    session = Session()

    try:
        item = session.query(ProductRangeForTheUser).filter(
            ProductRangeForTheUser.id == id
        ).first()

        if not item:
            return jsonify({"error": "not found"}), 404

        session.delete(item)
        session.commit()

        return jsonify({"message": "deleted"})

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        session.close()
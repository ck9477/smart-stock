from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from models.shopping_list import ShoppingList
from Service.shopping_service import generate_shopping_list

# -----------------------------
# DB Engine
# -----------------------------
engine = create_engine(
    "mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server"
)

Session = sessionmaker(bind=engine)

# -----------------------------
# Blueprint
# -----------------------------
shopping_bp = Blueprint("shopping", __name__, url_prefix="/shopping")

# -----------------------------
# CREATE
# -----------------------------
@shopping_bp.route("", methods=["POST"])
def create():
    session = Session()

    try:
        data = request.json

        obj = ShoppingList(
            user_id=data["user_id"],
            product_id=data["product_id"],
            amount=data.get("amount", 1),
            range_enum=data.get("range_enum"),
        )

        session.add(obj)
        session.commit()
        session.refresh(obj)

        return jsonify({"id": obj.id})

    finally:
        session.close()


# -----------------------------
# GET ALL BY USER ID
# -----------------------------
@shopping_bp.route("/user/<int:user_id>", methods=["GET"])
def get_all_by_user(user_id):
    session = Session()

    try:
        items = (
            session.query(ShoppingList)
            .filter(ShoppingList.user_id == user_id)
            .all()
        )

        if not items:
            return jsonify({"error": "not found"}), 404

        return jsonify(
            [
                {
                    "id": i.id,
                    "product_id": i.product_id,
                    "amount": i.amount,
                    "range_enum": i.range_enum,
                }
                for i in items
            ]
        )

    finally:
        session.close()


# -----------------------------
# GET BY ID
# -----------------------------
@shopping_bp.route("/<int:id>", methods=["GET"])
def get_by_id(id):
    session = Session()

    try:
        item = (
            session.query(ShoppingList)
            .filter(ShoppingList.id == id)
            .first()
        )

        if not item:
            return jsonify({"error": "not found"}), 404

        return jsonify(
            {
                "id": item.id,
                "product_id": item.product_id,
                "amount": item.amount,
                "range_enum": item.range_enum,
            }
        )

    finally:
        session.close()


# -----------------------------
# UPDATE
# -----------------------------
@shopping_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    session = Session()

    try:
        data = request.json

        item = (
            session.query(ShoppingList)
            .filter(ShoppingList.id == id)
            .first()
        )

        if not item:
            return jsonify({"error": "not found"}), 404

        item.product_id = data.get("product_id", item.product_id)
        item.amount = data.get("amount", item.amount)
        item.range_enum = data.get("range_enum", item.range_enum)

        session.commit()

        return jsonify({"message": "updated"})

    finally:
        session.close()


# -----------------------------
# DELETE
# -----------------------------
@shopping_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    session = Session()

    try:
        item = (
            session.query(ShoppingList)
            .filter(ShoppingList.id == id)
            .first()
        )

        if not item:
            return jsonify({"error": "not found"}), 404

        session.delete(item)
        session.commit()

        return jsonify({"message": "deleted"})

    finally:
        session.close()


# -----------------------------
# GENERATE SHOPPING LIST
# -----------------------------
@shopping_bp.route("/generate/<int:user_id>", methods=["POST"])
def generate(user_id):
    session = Session()

    try:
        result = generate_shopping_list(session, user_id)
        return jsonify(result)

    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()
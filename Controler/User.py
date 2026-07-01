from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from models.users import User

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)

Session = sessionmaker(bind=engine)

user_bp = Blueprint('users', __name__, url_prefix='/users')


# CREATE USER
@user_bp.route('', methods=['POST'])
def create_user():
    session = Session()
    try:
        data = request.json

        user = User(
            name=data["name"],
            email=data["email"],
            password_hash=generate_password_hash(data["password"])
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        return jsonify({"id": user.id})

    finally:
        session.close()


# GET ALL USERS
@user_bp.route('', methods=['GET'])
def get_users():
    session = Session()
    try:
        users = session.query(User).all()

        return jsonify([
            {"id": u.id, "name": u.name, "email": u.email}
            for u in users
        ])

    finally:
        session.close()


# GET USER BY ID
@user_bp.route('/<int:id>', methods=['GET'])
def get_user(id):
    session = Session()
    try:
        user = session.query(User).filter(User.id == id).first()

        if not user:
            return jsonify({"error": "user not found"}), 404

        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email
        })

    finally:
        session.close()


# UPDATE USER
@user_bp.route('/<int:id>', methods=['PUT'])
def update_user(id):
    session = Session()
    try:
        data = request.json

        user = session.query(User).filter(User.id == id).first()

        if not user:
            return jsonify({"error": "user not found"}), 404

        user.name = data.get("name", user.name)
        user.email = data.get("email", user.email)

        session.commit()

        return jsonify({"message": "updated"})

    finally:
        session.close()


# DELETE USER
@user_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    session = Session()
    try:
        user = session.query(User).filter(User.id == id).first()

        if not user:
            return jsonify({"error": "user not found"}), 404

        session.delete(user)
        session.commit()

        return jsonify({"message": "deleted"})

    finally:
        session.close()


# LOGIN
@user_bp.route('/login', methods=['POST'])
def login():
    session = Session()
    try:
        data = request.json

        user = session.query(User).filter(User.email == data["email"]).first()

        if not user or not check_password_hash(user.password_hash, data["password"]):
            return jsonify({"error": "invalid credentials"}), 401

        return jsonify({
            "message": "login success",
            "user_id": user.id
        })

    finally:
        session.close()


# GET BY EMAIL
@user_bp.route('/by-email/<email>', methods=['GET'])
def get_user_by_email(email):
    session = Session()
    try:
        user = session.query(User).filter(User.email == email).first()

        if not user:
            return jsonify({"error": "user not found"}), 404

        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email
        })

    finally:
        session.close()


# SEARCH BY NAME
@user_bp.route('/search', methods=['GET'])
def search_users():
    name = request.args.get("name", "")

    session = Session()
    try:
        users = session.query(User).filter(User.name.like(f"%{name}%")).all()

        return jsonify([
            {"id": u.id, "name": u.name, "email": u.email}
            for u in users
        ])

    finally:
        session.close()


# COUNT USERS
@user_bp.route('/count', methods=['GET'])
def count_users():
    session = Session()
    try:
        count = session.query(User).count()
        return jsonify({"count": count})

    finally:
        session.close()


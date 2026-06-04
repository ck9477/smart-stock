from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.users import User

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)

Session = sessionmaker(bind=engine)

user_bp = Blueprint('users', __name__, url_prefix='/users')


# CREATE
@user_bp.route('', methods=['POST'])
def create_user():
    session = Session()
    data = request.json

    user = User(
        name=data["name"],
        email=data["email"],
        password_hash=data["password"]
    )

    session.add(user)
    session.commit()
    session.refresh(user)  # מבטיח שה-ID נטען מהDB

    user_id = user.id

    session.close()

    return jsonify({"id": user_id})

# GET ALL
@user_bp.route('', methods=['GET'])
def get_users():
    session = Session()
    users = session.query(User).all()

    session.close()

    return jsonify([
        {"id": u.id, "name": u.name, "email": u.email}
        for u in users
    ])


# GET BY ID
@user_bp.route('/<int:id>', methods=['GET'])
def get_user(id):
    session = Session()
    user = session.query(User).filter(User.id == id).first()
    session.close()

    return jsonify({"id": user.id, "name": user.name, "email": user.email})


# UPDATE
@user_bp.route('/<int:id>', methods=['PUT'])
def update_user(id):
    session = Session()
    data = request.json

    user = session.query(User).filter(User.id == id).first()

    user.name = data.get("name", user.name)
    user.email = data.get("email", user.email)

    session.commit()
    session.close()

    return jsonify({"message": "updated"})


# DELETE
@user_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    session = Session()

    user = session.query(User).filter(User.id == id).first()

    session.delete(user)
    session.commit()
    session.close()

    return jsonify({"message": "deleted"})
# GET BY EMAIL
@user_bp.route('/by-email/<email>', methods=['GET'])
def get_user_by_email(email):
    session = Session()
    user = session.query(User).filter(User.email == email).first()
    session.close()

    if not user:
        return jsonify({"error": "user not found"}), 404

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email
    })


# SEARCH BY NAME
@user_bp.route('/search', methods=['GET'])
def search_users():
    name = request.args.get("name", "")

    session = Session()
    users = session.query(User).filter(User.name.like(f"%{name}%")).all()
    session.close()

    return jsonify([
        {"id": u.id, "name": u.name, "email": u.email}
        for u in users
    ])


# COUNT USERS
@user_bp.route('/count', methods=['GET'])
def count_users():
    session = Session()
    count = session.query(User).count()
    session.close()

    return jsonify({"count": count})


# LOGIN
@user_bp.route('/login', methods=['POST'])
def login():
    session = Session()
    data = request.json

    user = session.query(User).filter(
        User.email == data["email"],
        User.password_hash == data["password"]
    ).first()

    session.close()

    if not user:
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({
        "message": "login success",
        "user_id": user.id
    })


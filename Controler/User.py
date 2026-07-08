from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from models.users import User
from Middleware.auth import create_access_token, create_refresh_token, login_required, decode_token, require_permission, require_role, csrf_required
from Middleware.sanitize import sanitize_dict

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
        data = sanitize_dict(request.json)

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


# GET ALL USERS (admin only)
@user_bp.route('', methods=['GET'])
@login_required
@require_permission('view_all_users')
def get_users(user_id):
    session = Session()
    try:
        users = session.query(User).all()

        return jsonify([
            {"id": u.id, "name": u.name, "email": u.email}
            for u in users
        ])

    finally:
        session.close()


# GET CURRENT USER (authenticated)
@user_bp.route('/me', methods=['GET'])
@login_required
def get_me(user_id):
    """מחזיר את פרטי המשתמש המחובר — דורש JWT תקף."""
    session = Session()
    try:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            return jsonify({"error": "user not found"}), 404

        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email
        })

    finally:
        session.close()


# GET USER BY ID (authenticated)
@user_bp.route('/<int:id>', methods=['GET'])
@login_required
def get_user(user_id, id):
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


# UPDATE USER (authenticated — can only update self)
@user_bp.route('/<int:id>', methods=['PUT'])
@login_required
@csrf_required
def update_user(user_id, id):
    # Only self or admin
    if user_id != id:
        # Check if admin
        from Middleware.auth import get_user_permissions
        perm_session = Session()
        try:
            perms = get_user_permissions(user_id, perm_session)
        finally:
            perm_session.close()
        if 'manage_users' not in perms:
            return jsonify({"error": "Can only update your own profile"}), 403

    session = Session()
    try:
        data = sanitize_dict(request.json)

        user = session.query(User).filter(User.id == id).first()

        if not user:
            return jsonify({"error": "user not found"}), 404

        user.name = data.get("name", user.name)
        user.email = data.get("email", user.email)

        session.commit()

        return jsonify({"message": "updated"})

    finally:
        session.close()


# DELETE USER (admin only)
@user_bp.route('/<int:id>', methods=['DELETE'])
@login_required
@require_permission('manage_users')
@csrf_required
def delete_user(user_id, id):
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

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return jsonify({
            "message": "login success",
            "user_id": user.id,
            "access_token": access_token,
            "refresh_token": refresh_token,
        })

    finally:
        session.close()


# REFRESH TOKEN
@user_bp.route('/refresh', methods=['POST'])
def refresh_token():
    data = request.json
    token = data.get("refresh_token", "")

    try:
        payload = decode_token(token)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    if payload.get("type") != "refresh":
        return jsonify({"error": "Invalid token type"}), 401

    new_access = create_access_token(int(payload["sub"]))
    return jsonify({"access_token": new_access})


# GET BY EMAIL (authenticated)
@user_bp.route('/by-email/<email>', methods=['GET'])
@login_required
def get_user_by_email(user_id, email):
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


# SEARCH BY NAME (authenticated)
@user_bp.route('/search', methods=['GET'])
@login_required
def search_users(user_id):
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


# COUNT USERS (authenticated)
@user_bp.route('/count', methods=['GET'])
@login_required
def count_users(user_id):
    session = Session()
    try:
        count = session.query(User).count()
        return jsonify({"count": count})

    finally:
        session.close()


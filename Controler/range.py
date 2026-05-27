from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.Range import Range

engine = create_engine('mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server')
Session = sessionmaker(bind=engine)

range_bp = Blueprint('range', __name__, url_prefix='/range')


@range_bp.route('', methods=['POST'])
def create():
    session = Session()
    data = request.json

    obj = Range(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    session.close()

    return jsonify({"id": obj.id})


@range_bp.route('', methods=['GET'])
def get_all():
    session = Session()
    items = session.query(Range).all()
    session.close()

    return jsonify([{"id": i.id, "range_name": i.range_name, "Number_of_days": i.Number_of_days} for i in items])


@range_bp.route('/<int:id>', methods=['GET'])
def get_by_id(id):
    session = Session()
    obj = session.query(Range).filter(Range.id == id).first()
    session.close()

    if not obj:
        return jsonify({"error": "not found"}), 404

    return jsonify({"id": obj.id, "range_name": obj.range_name, "Number_of_days": obj.Number_of_days})


@range_bp.route('/<int:id>', methods=['PUT'])
def update(id):
    session = Session()
    data = request.json

    obj = session.query(Range).filter(Range.id == id).first()
    if not obj:
        return jsonify({"error": "not found"}), 404

    obj.range_name = data.get("range_name", obj.range_name)
    obj.Number_of_days = data.get("Number_of_days", obj.Number_of_days)

    session.commit()
    session.close()

    return jsonify({"message": "updated"})


@range_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()

    obj = session.query(Range).filter(Range.id == id).first()
    if not obj:
        return jsonify({"error": "not found"}), 404

    session.delete(obj)
    session.commit()
    session.close()

    return jsonify({"message": "deleted"})

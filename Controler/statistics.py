"""
Statistics & Weekly Shopping List — Controller
"""

from flask import Blueprint, request, jsonify
from db_connection import SessionLocal
from Service.weekly_shopping_list import WeeklyShoppingList
from Middleware.auth import login_required

statistics_bp = Blueprint("statistics", __name__, url_prefix="/statistics")


@statistics_bp.route("/weekly-list", methods=["GET"])
@login_required
def weekly_list(user_id: int):
    """
    GET /statistics/weekly-list
    Returns the user's recommended shopping list for the coming week.
    """
    session = SessionLocal()
    try:
        service = WeeklyShoppingList(session)
        items = service.generate(user_id)

        return jsonify({
            "user_id": user_id,
            "count": len(items),
            "items": items,
        })

    finally:
        session.close()

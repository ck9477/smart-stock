"""
Weekly Shopping List Generator — generates a list of products to buy this week.

Logic: a product enters the list if it's expected to run out within 7 days.
The goal is to consolidate shopping into one weekly trip — if the user is
going to the store now, they should buy everything that won't last until
next week's trip.
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from Service.statistics_engine import StatisticsEngine

logger = logging.getLogger(__name__)


class WeeklyShoppingList:
    """
    Generates weekly shopping based on personal purchase history.

    A product is included if days_until_empty <= 7 — i.e. it won't last
    until the next weekly shopping trip.

    Then classified:
      - "דחוף"   : already past its cycle (days_until_empty <= 0)
      - "השבוע"  : will run out this week (0 < days_until_empty <= 7)

    Products with days_until_empty > 7 are excluded entirely —
    the user can buy them next week.

    Usage:
        service = WeeklyShoppingList(db_session)
        items = service.generate(user_id=50)
        # [{"product_name": "חלב 3%", "recommended_quantity": 2, "urgency": "דחוף"}, ...]
    """

    PREDICTION_WINDOW = 7  # products running out within 7 days are included

    def __init__(self, session: Session):
        self.engine = StatisticsEngine(session)

    def generate(self, user_id: int) -> list[dict]:
        """
        Return the shopping list for this week — only products
        expected to run out within the next 7 days.
        """
        recs = self.engine.get_recommendations(user_id)

        items = []
        for r in recs:
            # Only include if it'll run out within the weekly window
            if r["days_until_empty"] > self.PREDICTION_WINDOW:
                continue

            urgency = "דחוף" if r["days_until_empty"] <= 0 else "השבוע"

            items.append({
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "recommended_quantity": r["recommended_quantity"],
                "urgency": urgency,
                "avg_cycle_days": r["avg_cycle_days"],
                "days_since_last": r["days_since_last"],
                "days_until_empty": r["days_until_empty"],
            })

        # Sort: urgent first, then by days_until_empty ascending
        items.sort(key=lambda i: i["days_until_empty"])
        return items

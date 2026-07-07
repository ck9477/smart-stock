"""
Quick test: new user with no history should get starter pack.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import SessionLocal
from Service.weekly_shopping_list import WeeklyShoppingList


def test():
    session = SessionLocal()
    service = WeeklyShoppingList(session)

    # Try a user ID that definitely has no purchase history
    new_user_id = 99999

    print(f"=== Starter pack test for new user {new_user_id} ===")
    items = service.generate(new_user_id)

    if not items:
        print("(empty — this should NOT happen)")
    else:
        for item in items:
            print(f"  {item['product_name']} — {item['recommended_quantity']} units ({item['urgency']})")

    print(f"\nTotal: {len(items)} items")
    session.close()


if __name__ == "__main__":
    test()

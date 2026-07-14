"""
Test the StatisticsEngine and WeeklyShoppingList.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import SessionLocal
from Service.weekly_shopping_list import WeeklyShoppingList


def test():
    session = SessionLocal()
    service = WeeklyShoppingList(session)

    # Test with a known user ID that has purchase history
    user_id = 50

    print("=" * 60)
    print(f"Weekly Shopping List for user {user_id}")
    print("=" * 60)

    items = service.generate(user_id)

    if not items:
        print(f"\nNo recommendations — user {user_id} has no purchase history yet.")
        print("(This is expected if the user hasn't uploaded receipts.)")
    else:
        for item in items:
            urgency_mark = "!!" if item["urgency"] == "דחוף" else ""
            print(f"\n  {urgency_mark} {item['product_name']}")
            print(f"     Quantity: {item['recommended_quantity']}")
            print(f"     Urgency: {item['urgency']}")
            print(f"     Cycle: {item['avg_cycle_days']} days")
            print(f"     Last purchase: {item['days_since_last']} days ago")
            print(f"     Empty in: {item['days_until_empty']} days")

    # Also show raw stats for debugging
    print(f"\n{'=' * 60}")
    print("Raw Statistics (for debugging)")
    print("=" * 60)

    from Service.statistics_engine import StatisticsEngine
    engine = StatisticsEngine(session)
    recs = engine.get_recommendations(user_id)

    if recs:
        for r in recs:
            print(f"\n  [{r['product_name']}]")
            for k, v in r.items():
                print(f"    {k}: {v}")
    else:
        print("  (no data)")

    session.close()
    print("\nDone.")


if __name__ == "__main__":
    test()

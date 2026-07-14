"""
End-to-end test: Create a user with realistic purchase history,
run the statistics engine, and validate recommendations.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from db_connection import SessionLocal
from Service.statistics_engine import StatisticsEngine
from Service.weekly_shopping_list import WeeklyShoppingList

# ── Define a realistic shopping pattern ─────────────────
# Each product: (product_id, product_name, typical_quantity, cycle_days, start_weeks_ago)
SHOPPING_PATTERN = [
    # Weekly staples — every ~7 days
    (267, "חלב 3%",              2,  7,  10),  # 10 purchases
    (268, "לחם אחיד",            2,  7,  10),
    (269, "ביצים",               1,  7,  10),
    # Bi-weekly
    (270, "עגבניות",             4, 14,  6),
    (271, "מלפפונים L",          3, 14,  6),
    (272, "בצל יבש",             1, 14,  6),
    # Monthly
    (274, "שמן קנולה",           1, 30,  3),
    (277, "קמח לבן",             1, 40,  3),
    (279, "סוכר",                1, 45,  2),
    (273, "מים 1.5 ליטר",        1, 21,  5),
    # Unstable — alternating weeks
    (280, "פסטה יבשה",           2, 14,  2),  # only 2 purchases (every other time)
]


def create_test_user():
    """Create a test user and populate purchase history."""
    session = SessionLocal()
    try:
        # Create user
        from sqlalchemy import text
        result = session.execute(
            text("INSERT INTO users (name, email, password_hash) OUTPUT INSERTED.id VALUES (:name, :email, :hash)"),
            {"name": "test_stats_demo", "email": "test_stats_demo@test.com", "hash": "test_hash_xxx"}
        )
        user_id = result.fetchone()[0]
        session.commit()
        print(f"[OK] Created user {user_id}")

        # Generate receipts and purchase history
        today = date.today()
        receipt_count = 0
        product_count = 0

        for (prod_id, name, qty, cycle_days, num_purchases) in SHOPPING_PATTERN:
            for i in range(num_purchases):
                # Each purchase was (i+1) cycles ago, plus some random jitter
                jitter = (hash(f"{prod_id}_{i}") % 6) - 3  # -3..+2 days jitter
                days_ago = (i * cycle_days) + jitter
                receipt_date = today - timedelta(days=days_ago)

                # For simplicity, each product purchase is its own receipt
                # (real data would have multiple products per receipt)
                result = session.execute(
                    text("INSERT INTO receipts (user_id, receipt_date) OUTPUT INSERTED.id VALUES (:uid, :d)"),
                    {"uid": user_id, "d": receipt_date}
                )
                receipt_id = result.fetchone()[0]

                # Add +/- 1 jitter to quantity sometimes
                qty_jitter = (hash(f"qty_{prod_id}_{i}") % 3) - 1  # -1, 0, +1
                actual_qty = max(1, qty + qty_jitter)

                session.execute(
                    text("INSERT INTO reception_products (receipts_id, Products_id, amount) VALUES (:rid, :pid, :amt)"),
                    {"rid": receipt_id, "pid": prod_id, "amt": actual_qty}
                )
                receipt_count += 1
                product_count += 1

        session.commit()
        print(f"[OK] Created {receipt_count} receipts with {product_count} product entries")
        return user_id

    finally:
        session.close()


def run_stats_engine(user_id):
    """Run the statistics engine and print results neatly."""
    session = SessionLocal()
    try:
        engine = StatisticsEngine(session)
        recs = engine.get_recommendations(user_id)

        if not recs:
            print("\n[FAIL] No recommendations — engine returned nothing!")
            return

        print(f"\n{'='*70}")
        print(f"** Statistics Engine Results — User {user_id}")
        print(f"{'='*70}")

        # Header
        print(f"\n{'מוצר':<20} {'מחזור':>6} {'כמות':>5} {'צריכה/יום':>9} "
              f"{'יציב':>5} {'בטחון':>5} {'קניות':>6} {'קנייה אחרונה':>13} "
              f"{'יתרוקן ב-':>10} {'המלצה':>6}")
        print("-" * 85)

        checks_passed = 0
        checks_total = 0

        for r in sorted(recs, key=lambda x: x["days_until_empty"]):
            name = r["product_name"]
            # Truncate long names
            if len(name) > 18:
                name = name[:17] + "…"

            urgency = "🔴" if r["days_until_empty"] <= 0 else ("🟡" if r["days_until_empty"] <= 7 else "🟢")
            print(f"{urgency}{name:<18} {r['avg_cycle_days']:>5.1f}ד {r['avg_quantity']:>5.2f} "
                  f"{r['daily_consumption']:>8.3f} {r['stability']:>5.2f} {r['confidence']:>5.2f} "
                  f"{r['n_purchases']:>5}  "
                  f"{r['days_since_last']:>4} ימים{' ':<6} "
                  f"{r['days_until_empty']:>5.1f} ימים{' ':<4} "
                  f"{r['recommended_quantity']:>5}")

            # Validation checks
            checks_total += 1
            # Cycle should be positive
            if r["avg_cycle_days"] > 0:
                checks_passed += 1
            # Days since last should match the pattern roughly
            # We'll do smarter checks below

        # ── Validation ──────────────────────────────────
        print(f"\n{'='*70}")
        print("** Validations")
        print(f"{'='*70}")

        validations = []

        # 1. Products we know were bought weekly should have cycle ~7
        weekly = [r for r in recs if r["product_name"] in ["חלב 3%", "לחם אחיד", "ביצים"]]
        for r in weekly:
            ok = 5 <= r["avg_cycle_days"] <= 10
            validations.append((f"מחזור {r['product_name']} ~7 ימים (got {r['avg_cycle_days']})", ok))

        # 2. Monthly products should have cycle ~30+
        monthly = [r for r in recs if r["product_name"] in ["שמן קנולה", "קמח לבן"]]
        for r in monthly:
            ok = r["avg_cycle_days"] >= 20
            validations.append((f"מחזור {r['product_name']} >=20 ימים (got {r['avg_cycle_days']})", ok))

        # 3. Confidence should be higher for more purchases
        for r in recs:
            if r["n_purchases"] >= 8:
                ok = r["confidence"] >= 0.8
                validations.append((f"ביטחון {r['product_name']} >=0.8 ({r['n_purchases']} קניות → {r['confidence']})", ok))

        # 4. Stability of weekly staples should be high
        for r in weekly:
            ok = r["stability"] >= 0.5
            validations.append((f"יציבות {r['product_name']} >=0.5 (got {r['stability']})", ok))

        # 5. recommended_quantity should be close to avg_quantity
        for r in recs:
            ok = abs(r["recommended_quantity"] - r["avg_quantity"]) <= r["avg_quantity"] * 0.7
            validations.append((f"המלצה ~ ממוצע {r['product_name']} ({r['recommended_quantity']} vs avg {r['avg_quantity']:.1f})", ok))

        # 6. Days until empty should be negative for past-due products
        past_due = [r for r in recs if r["days_since_last"] > r["avg_cycle_days"]]
        for r in past_due:
            ok = r["days_until_empty"] < 0
            validations.append((f"התרוקן {r['product_name']} (last={r['days_since_last']}d > cycle={r['avg_cycle_days']}d) → empty={r['days_until_empty']}d", ok))

        # Print validations
        passed = sum(1 for _, ok in validations if ok)
        failed = sum(1 for _, ok in validations if not ok)
        for msg, ok in validations:
            mark = "[OK]" if ok else "[FAIL]"
            print(f"  {mark} {msg}")

        print(f"\n** תוצאה: {passed}[OK] / {failed}[FAIL] (מתוך {len(validations)} בדיקות)")

    finally:
        session.close()


def cleanup(user_id):
    """Remove test data."""
    session = SessionLocal()
    try:
        from sqlalchemy import text
        # Delete reception_products for this user's receipts
        session.execute(
            text("DELETE FROM reception_products WHERE receipts_id IN (SELECT id FROM receipts WHERE user_id = :uid)"),
            {"uid": user_id}
        )
        # Delete receipts
        session.execute(
            text("DELETE FROM receipts WHERE user_id = :uid"),
            {"uid": user_id}
        )
        # Delete user
        session.execute(
            text("DELETE FROM users WHERE id = :uid"),
            {"uid": user_id}
        )
        session.commit()
        print(f"\n** Cleaned up user {user_id}")
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="Keep test data (don't clean up)")
    args = ap.parse_args()

    print("** Creating test user with realistic shopping patterns...")
    uid = create_test_user()

    run_stats_engine(uid)

    if not args.keep:
        cleanup(uid)
    else:
        print(f"\n** Data kept for user {uid} (use --keep to preserve)")

"""
Statistics Engine — Rewritten
Calculates purchase patterns and predicts when products will run out.
Uses SQLAlchemy (consistent with the rest of the project).
"""

import logging
from datetime import datetime, date
from collections import defaultdict
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class StatisticsEngine:
    """
    Analyses a user's purchase history to:
      - Compute the average purchase cycle per product (weighted: recent > old).
      - Estimate daily consumption rate.
      - Predict when the product will be depleted.
      - Recommend a quantity for the upcoming week.

    Usage:
        engine = StatisticsEngine(session)
        recommendations = engine.get_recommendations(user_id)
        # Each recommendation is a product_id -> { cycle, quantity, ... }
    """

    # ── Tunable constants ─────────────────────────────────

    PREDICTION_WINDOW_DAYS = 7      # "This week" window
    MIN_PURCHASES         = 2        # Minimum purchases before we trust the data
    WEIGHT_DECAY          = 0.85     # Weight multiplier per older gap (0–1)
    OUTLIER_STD_MULT      = 2.5      # Treat gap/quantity beyond this many σ as outlier
    DEFAULT_CYCLE_DAYS    = 14       # Fallback when we lack enough data
    DEFAULT_QUANTITY      = 1        # Fallback quantity

    def __init__(self, session: Session):
        self.session = session

    # ── Starter pack for new users ───────────────────────

    STARTER_PRODUCTS = [
        {"name": "חלב 3%", "quantity": 2},
        {"name": "לחם", "quantity": 2},
        {"name": "ביצים", "quantity": 1},
        {"name": "קוטג'", "quantity": 2},
        {"name": "גבינה צהובה", "quantity": 1},
        {"name": "מלפפונים", "quantity": 3},
        {"name": "עגבניות", "quantity": 4},
        {"name": "בצל", "quantity": 2},
        {"name": "שמן", "quantity": 1},
        {"name": "מלח", "quantity": 1},
    ]

    # ── Public API ────────────────────────────────────────

    def get_recommendations(self, user_id: int) -> list[dict]:
        """
        Main entry point.
        Returns a list of dicts, sorted by urgency.
        If the user has no purchase history, returns a starter pack.
        """
        rows = self._fetch_history(user_id)
        if not rows:
            logger.info(f"No purchase history for user {user_id}, returning starter pack")
            return self._get_starter_pack(user_id)

        grouped = self._group_and_sort(rows)
        results = []

        for product_id, purchases in grouped.items():
            stats = self._compute_stats(product_id, purchases)
            if stats is None:
                continue

            # Predict how many days until depletion
            stats["days_until_empty"] = self._days_until_empty(stats)

            # Recommend quantity for this week
            stats["recommended_quantity"] = self._recommend_quantity(stats)

            results.append(stats)

        # Sort: products that already ran out (negative days_until_empty) first,
        # then by who runs out soonest
        results.sort(key=lambda r: r["days_until_empty"])
        return results

    def get_weekly_list(self, user_id: int) -> list[dict]:
        """
        Convenience method — only returns products needed this week.
        """
        all_recs = self.get_recommendations(user_id)
        return [
            r for r in all_recs
            if r["days_until_empty"] <= self.PREDICTION_WINDOW_DAYS
        ]

    # ── Database ──────────────────────────────────────────

    def _fetch_history(self, user_id: int) -> list[tuple]:
        sql = text("""
            SELECT
                rp.products_id,
                r.receipt_date,
                rp.amount,
                p.name
            FROM reception_products rp
            JOIN receipts r ON rp.receipts_id = r.id
            JOIN products p ON rp.products_id = p.id
            WHERE r.user_id = :user_id
            ORDER BY rp.products_id, r.receipt_date
        """)
        result = self.session.execute(sql, {"user_id": user_id})
        return [(row[0], row[1], row[2], row[3]) for row in result.fetchall()]

    def _group_and_sort(self, rows: list[tuple]) -> dict[int, list[dict]]:
        """
        Group rows by product_id, ensure dates are sorted,
        and add computed gap/quantity fields.
        """
        grouped: dict[int, list[dict]] = defaultdict(list)

        for prod_id, dt, amt, name in rows:
            # Normalize date
            if isinstance(dt, datetime):
                dt = dt.date()
            elif isinstance(dt, str):
                dt = datetime.strptime(str(dt)[:10], "%Y-%m-%d").date()

            grouped[prod_id].append({
                "date": dt,
                "amount": amt,
                "name": name,
            })

        # Ensure chronological order within each product
        for entries in grouped.values():
            entries.sort(key=lambda e: e["date"])

        return grouped

    # ── Core computation ──────────────────────────────────

    def _compute_stats(
        self, product_id: int, purchases: list[dict]
    ) -> Optional[dict]:
        """
        Given a product's purchase history, compute all statistics.
        Returns None when there isn't enough data.
        """
        if len(purchases) < self.MIN_PURCHASES:
            return None

        # 1. Inter-purchase gaps (in days)
        gaps = []
        quantities = []
        for i in range(1, len(purchases)):
            gap = (purchases[i]["date"] - purchases[i - 1]["date"]).days
            if gap > 0:
                gaps.append(gap)
                quantities.append(purchases[i - 1]["amount"])

        # Add the last purchase's amount too
        quantities.append(purchases[-1]["amount"])

        if not gaps:
            return None

        # 2. Filter outliers from gaps
        clean_gaps, clean_quantities = self._remove_outliers(gaps, quantities)

        if not clean_gaps:
            clean_gaps = gaps
            clean_quantities = quantities

        # 3. Weighted average cycle (recent gaps weighted more)
        avg_cycle = self._weighted_average(clean_gaps)
        if avg_cycle <= 0:
            avg_cycle = self.DEFAULT_CYCLE_DAYS

        # 4. Average quantity per purchase
        avg_quantity = sum(clean_quantities) / len(clean_quantities)

        # 5. Daily consumption rate
        daily_consumption = avg_quantity / avg_cycle

        # 6. Stability (1 – CV) — how consistent the purchase pattern is
        stability = self._compute_stability(clean_gaps)

        # 7. Confidence grows with number of data points
        n = len(purchases)
        confidence = min(1.0, n / 5)  # reaches 1.0 at 5+ purchases

        # 8. Days since last purchase
        last_date = purchases[-1]["date"]
        days_since_last = (date.today() - last_date).days

        return {
            "product_id": product_id,
            "product_name": purchases[0]["name"],
            "avg_cycle_days": round(avg_cycle, 1),
            "avg_quantity": round(avg_quantity, 2),
            "daily_consumption": round(daily_consumption, 3),
            "stability": round(stability, 2),
            "days_since_last": days_since_last,
            "confidence": round(confidence, 2),
            "n_purchases": n,
        }

    def _days_until_empty(self, stats: dict) -> float:
        """
        How many days until the product runs out.
        Negative = already ran out (should buy now).
        """
        # How many "cycles" worth of stock remain? We assume 1 cycle = avg_quantity bought
        # days_until_empty = avg_cycle_days - days_since_last
        # But if they bought more than usual, it lasts longer:
        # Actually simple: you bought avg_quantity, it lasts avg_cycle days.
        # If days_since_last > avg_cycle, you're already out.
        return round(stats["avg_cycle_days"] - stats["days_since_last"], 1)

    def _recommend_quantity(self, stats: dict) -> int:
        """
        How many units to recommend buying.
        Always recommends roughly 1 cycle's worth — the typical amount
        the user buys in one shopping trip. We don't try to "catch up"
        on missed weeks; that would produce absurd quantities.
        """
        # Cap: never recommend more than 2x the average purchase
        # (protection against long gaps inflating quantities)
        return max(1, round(stats["avg_quantity"]))

    def _get_starter_pack(self, user_id: int) -> list[dict]:
        """
        Returns a basic starter shopping list for new users with no history.
        """
        return [
            {
                "product_id": 0,
                "product_name": p["name"],
                "avg_cycle_days": 7,
                "avg_quantity": p["quantity"],
                "daily_consumption": round(p["quantity"] / 7, 3),
                "stability": 0.5,
                "days_since_last": 99,
                "confidence": 0.2,
                "n_purchases": 0,
                "days_until_empty": -1.0,
                "recommended_quantity": p["quantity"],
            }
            for p in self.STARTER_PRODUCTS
        ]

    # ── Math helpers ──────────────────────────────────────

    def _weighted_average(self, values: list) -> float:
        """
        Exponential decay weighting — most recent value gets weight 1.0,
        each step back multiplies by WEIGHT_DECAY.
        """
        if not values:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0
        weight = 1.0

        # Iterate in reverse — newest first
        for v in reversed(values):
            weighted_sum += v * weight
            total_weight += weight
            weight *= self.WEIGHT_DECAY

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _compute_stability(self, gaps: list) -> float:
        """
        1 = perfectly stable (same gap every time).
        0 = very erratic.
        Uses Coefficient of Variation: CV = std / mean.
        Stability = 1 / (1 + CV).  Bounded to [0, 1].
        """
        if not gaps:
            return 0.0

        mean = sum(gaps) / len(gaps)
        if mean == 0:
            return 1.0  # all gaps are 0 — perfectly stable (same day)

        variance = sum((g - mean) ** 2 for g in gaps) / len(gaps)
        std = variance ** 0.5
        cv = std / mean
        return round(1 / (1 + cv), 2)

    def _remove_outliers(
        self, gaps: list, quantities: list
    ) -> tuple[list, list]:
        """
        Remove gap/quantity pairs where the gap is an outlier
        (beyond OUTLIER_STD_MULT standard deviations from the mean).
        """
        if len(gaps) < 3:
            return gaps, quantities

        mean_gap = sum(gaps) / len(gaps)
        variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
        std_gap = variance ** 0.5
        if std_gap == 0:
            return gaps, quantities

        threshold = self.OUTLIER_STD_MULT * std_gap

        clean_gaps = []
        clean_quantities = []

        for i, g in enumerate(gaps):
            if abs(g - mean_gap) <= threshold:
                clean_gaps.append(g)
                clean_quantities.append(quantities[i])

        if len(clean_gaps) < 2:
            return gaps, quantities  # Don't over-filter

        return clean_gaps, clean_quantities

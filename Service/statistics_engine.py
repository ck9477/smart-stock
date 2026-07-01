import pyodbc
from datetime import datetime
from collections import defaultdict


class StatisticsEngine:
    def __init__(self):
        self.conn = pyodbc.connect(
            "DRIVER={SQL Server};"
            "SERVER=localhost;"
            "DATABASE=SmartStock;"
            "Trusted_Connection=yes;"
        )

    def fetch_data(self, user_id):
        query = """
        SELECT rp.Products_id, r.receipt_date
        FROM Reception_products rp
        JOIN receipts r ON rp.receipts_id = r.id
        WHERE r.user_id = ?
        ORDER BY rp.Products_id, r.receipt_date
        """
        return self.conn.cursor().execute(query, user_id).fetchall()

    def analyze(self, rows):
        data = defaultdict(list)

        # המרה בטוחה לתאריכים
        for product_id, date in rows:
            d = datetime.strptime(str(date)[:10], "%Y-%m-%d")
            data[product_id].append(d)

        results = []

        for product_id, dates in data.items():

            # 🔴 סינון רעש: לפחות 3 קניות
            if len(dates) < 3:
                continue

            gaps = [
                (dates[i] - dates[i - 1]).days
                for i in range(1, len(dates))
            ]

            if not gaps:
                continue

            avg_gap = sum(gaps) / len(gaps)

            # מניעת cycle 0 או לא הגיוני
            if avg_gap <= 0:
                continue

            variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
            stability = max(0, 1 - (variance / (avg_gap ** 2 + 1)))

            days_since = (datetime.now().date() - dates[-1].date()).days

            trend = (gaps[-1] - avg_gap) / (avg_gap + 1)

            n = len(dates)
            confidence = min(1.0, n / 8)

            score = (days_since / avg_gap) * stability * confidence

            results.append({
                "product_id": product_id,
                "cycle": round(avg_gap, 2),
                "stability": round(stability, 2),
                "trend": round(trend, 2),
                "days_since": days_since,
                "score": round(score, 2),
                "n": n
            })

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def get_recommendations(self, user_id):
        rows = self.fetch_data(user_id)
        results = self.analyze(rows)

        print("ENGINE RUNNING\n")

        for r in results:
            print(
                r["product_id"],
                r["score"],
                f"cycle:{r['cycle']}",
                f"since:{r['days_since']}",
                f"n:{r['n']}"
            )

        return results


if __name__ == "__main__":
    engine = StatisticsEngine()
    engine.get_recommendations(50)
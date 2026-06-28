import pyodbc
from datetime import datetime
import statistics


SERVER = 'D403-005'
DATABASE = 'SmartStock'
DRIVER = 'ODBC Driver 17 for SQL Server'


def get_connection():
    conn_str = (
        f'DRIVER={{{DRIVER}}};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)


class StatisticsEngine:

    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def fetch_user_data(self, user_id):

        query = """
        SELECT 
            p.name,
            p.code,
            rp.amount,
            r.receipt_date
        FROM receipts r
        JOIN Reception_products rp ON r.id = rp.receipts_id
        JOIN Products p ON p.id = rp.Products_id
        WHERE r.user_id = ?
        ORDER BY p.code, r.receipt_date
        """

        self.cursor.execute(query, (user_id,))
        return self.cursor.fetchall()

    def filter_outliers(self, history):

        if len(history) < 4:
            return history

        amounts = [h[1] for h in history]
        median_amount = statistics.median(amounts)

        filtered = []
        for date, amount in history:
            if amount > median_amount * 2.5:
                continue
            filtered.append((date, amount))

        return filtered if len(filtered) >= 2 else history

    def build_statistics(self, rows):

        if not rows:
            return []

        data = {}

        for name, barcode, amount, date in rows:
            data.setdefault(barcode, {
                "name": name,
                "history": []
            })
            data[barcode]["history"].append((date, int(amount or 0)))

        result = []
        now = datetime.now()

        for barcode, item in data.items():

            history = sorted(item["history"], key=lambda x: x[0])
            history = self.filter_outliers(history)

            dates = [h[0] for h in history]
            amounts = [h[1] for h in history]

            if not history:
                continue

            days_since = (now - dates[-1]).total_seconds() / 86400

            if len(history) == 1:
                result.append({
                    "product_name": item["name"],
                    "barcode": barcode,
                    "quantity": max(1, amounts[0]),
                    "avg_gap_days": None,
                    "days_since": round(days_since, 2),
                    "lateness_days": round(days_since, 2),
                    "stability": 0.0,
                    "confidence": 0.1,
                    "pattern": "single_point",
                    "score": 0.2,
                    "level": "low",
                    "next_expected_date": None
                })
                continue

            gaps = [
                (dates[i] - dates[i - 1]).total_seconds() / 86400
                for i in range(1, len(dates))
            ]

            avg_gap = statistics.median(gaps)

            if len(gaps) == 1:
                stability = 0.4
                confidence = 0.3
                pattern = "weak_signal"
            else:
                mad = statistics.mean([abs(g - avg_gap) for g in gaps])
                stability = max(0, 1 - (mad / avg_gap if avg_gap else 1))
                confidence = min(1.0, len(gaps) / 6) * stability

                if stability < 0.4:
                    pattern = "irregular"
                elif avg_gap <= 5:
                    pattern = "fast_cycle"
                elif avg_gap <= 15:
                    pattern = "weekly_cycle"
                else:
                    pattern = "long_cycle"

            expected_date = dates[-1] + statistics.timedelta(days=int(avg_gap)) if hasattr(statistics, "timedelta") else None

            lateness_days = 0
            score = 0.2
            level = "low"

            result.append({
                "product_name": item["name"],
                "barcode": barcode,
                "quantity": max(1, int(statistics.mean(amounts) * (1 + confidence))),
                "avg_gap_days": round(avg_gap, 2),
                "days_since": round(days_since, 2),
                "lateness_days": round(lateness_days, 2),
                "stability": round(stability, 2),
                "confidence": round(confidence, 2),
                "pattern": pattern,
                "score": round(score, 2),
                "level": level,
                "next_expected_date": None
            })

        return result

    def get_statistics(self, user_id):
        rows = self.fetch_user_data(user_id)
        return self.build_statistics(rows)


if __name__ == "__main__":
    engine = StatisticsEngine()

    for item in engine.get_statistics(29):
        print(f"{item['product_name']} -> {item['quantity']}")
"""
Blueprint למילוי עגלה אוטומטית ברמי לוי.
"""

import json
import queue
import threading

from flask import Blueprint, request, jsonify, Response, stream_with_context
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from models.shopping_list import ShoppingList
from models.Products import Product
from Service.rami_levy_adapter_old import RamiLevyAdapter

engine = create_engine(
    "mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server"
)

Session = sessionmaker(bind=engine)

rami_levy_bp = Blueprint("rami_levy", __name__, url_prefix="/rami-levy")


def _fill_cart_logic(user_id: int, progress_queue: queue.Queue):
    """
    הלוגיקה של מילוי העגלה — רצה ב-thread נפרד.
    מדווחת התקדמות דרך progress_queue.
    """
    session = Session()
    adapter = RamiLevyAdapter()
    results = []

    try:
        items = (
            session.query(ShoppingList)
            .filter(ShoppingList.user_id == user_id)
            .all()
        )

        total = len(items)

        if total == 0:
            progress_queue.put({"type": "done", "message": "רשימת הקניות ריקה", "results": []})
            return

        progress_queue.put({"type": "start", "total": total})

        for idx, item in enumerate(items):
            product = (
                session.query(Product)
                .filter(Product.id == item.product_id)
                .first()
            )

            product_name = (
                product.name if product else f"מוצר #{item.product_id}"
            )

            # דיווח: מתחיל מוצר
            progress_queue.put({
                "type": "progress",
                "current": idx + 1,
                "total": total,
                "product_name": product_name,
                "product_id": item.product_id,
                "status": "מחפש...",
            })

            try:
                ok = adapter.process_product(
                    barcode=product.code if product else None,
                    name=product_name,
                    quantity=item.amount,
                )

                result = {
                    "product_id": item.product_id,
                    "product_name": product_name,
                    "success": ok,
                }
                results.append(result)

                # דיווח: הסתיים מוצר
                progress_queue.put({
                    "type": "item_done",
                    "current": idx + 1,
                    "total": total,
                    "product_name": product_name,
                    "product_id": item.product_id,
                    "success": ok,
                })

            except Exception as e:
                result = {
                    "product_id": item.product_id,
                    "product_name": product_name,
                    "success": False,
                    "error": str(e),
                }
                results.append(result)

                progress_queue.put({
                    "type": "item_done",
                    "current": idx + 1,
                    "total": total,
                    "product_name": product_name,
                    "product_id": item.product_id,
                    "success": False,
                    "error": str(e),
                })

        progress_queue.put({
            "type": "done",
            "message": f"מילוי עגלה הסתיים: {sum(1 for r in results if r['success'])}/{total} מוצרים נוספו",
            "results": results,
        })

    except Exception as e:
        progress_queue.put({"type": "error", "error": str(e)})

    finally:
        try:
            adapter.close()
        except Exception:
            pass
        finally:
            session.close()


@rami_levy_bp.route("/fill-cart-stream", methods=["POST"])
def fill_cart_stream():
    """
    SSE endpoint — מילוי עגלה עם דיווח התקדמות בזמן אמת.

    גוף בקשה: { "user_id": 1 }
    מחזיר: text/event-stream
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    progress_queue = queue.Queue()

    def generate():
        thread = threading.Thread(
            target=_fill_cart_logic,
            args=(user_id, progress_queue),
            daemon=True,
        )
        thread.start()

        while True:
            try:
                msg = progress_queue.get(timeout=30.0)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                if msg["type"] in ("done", "error"):
                    break

            except queue.Empty:
                # שלח heartbeat (keep-alive) כל 30 שניות
                yield f": heartbeat\n\n"

        thread.join(timeout=10)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@rami_levy_bp.route("/fill-cart", methods=["POST"])
def fill_cart():
    """
    ממלא את עגלת רמי לוי במוצרים מרשימת הקניות של המשתמש.
    (גרסה סינכרונית — נשמרת לתאימות לאחור)

    גוף בקשה: { "user_id": 1 }
    תשובה: { "message": "...", "results": [...] }
    """
    progress_queue = queue.Queue()
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    _fill_cart_logic(user_id, progress_queue)

    # איסוף התוצאות מה-queue
    results = []
    message = ""
    while True:
        try:
            msg = progress_queue.get(timeout=0.5)
            if msg["type"] == "done":
                message = msg.get("message", "")
                results = msg.get("results", [])
                break
            elif msg["type"] == "error":
                return jsonify({"error": msg.get("error", "")}), 500
        except queue.Empty:
            break

    return jsonify({"message": message, "results": results})
import json
import queue
import threading
from flask import Blueprint, request, jsonify, Response, stream_with_context
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from werkzeug.datastructures import FileStorage
from Service.receipt_service import ReceiptService
from models.receipts import Receipt
from models.Reception_products import ReceptionProducts
from models.Products import Product
import io
import os
from datetime import datetime

engine = create_engine(
    'mssql+pyodbc://@D403-005/SmartStock?driver=ODBC Driver 17 for SQL Server'
)
Session = sessionmaker(bind=engine)

receipt_bp = Blueprint('receipts', __name__, url_prefix='/receipts')

# -----------------------------
# CREATE RECEIPT
# -----------------------------
@receipt_bp.route('', methods=['POST'])
def create():
    session = Session()
    try:
        data = request.get_json()
        if not data or "user_id" not in data:
            return jsonify({"error": "user_id is required"}), 400

        user_id = data["user_id"]
        receipt_date_str = data.get("receipt_date")  # optional: "YYYY-MM-DD"
        receipt_date = None
        if receipt_date_str:
            try:
                receipt_date = datetime.strptime(receipt_date_str, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400

        service = ReceiptService(session)
        receipt_id = service.create_receipt(user_id=user_id, receipt_date=receipt_date)
        return jsonify({"id": receipt_id, "receipt_date": (receipt_date or datetime.now()).strftime("%Y-%m-%d")})
    finally:
        session.close()

@receipt_bp.route('/upload-stream', methods=['POST'])
def upload_stream():
    """
    SSE endpoint — העלאת קבלה עם דיווח התקדמות בזמן אמת.

    גוף בקשה (multipart/form-data):
    - receipt: קובץ הקבלה (PDF/טקסט)
    - user_id: מזהה המשתמש

    מחזיר: text/event-stream
    """
    receipt_file = request.files.get("receipt")
    user_id = request.form.get("user_id") or request.args.get("user_id")

    if receipt_file is None:
        receipt_path = request.form.get("receipt") if not receipt_file else None
        if receipt_path:
            receipt_path = receipt_path.strip()
            try:
                with open(receipt_path, 'rb') as f:
                    raw_bytes = f.read()
                receipt_file = FileStorage(
                    stream=io.BytesIO(raw_bytes),
                    filename=os.path.basename(receipt_path),
                    content_type='application/octet-stream'
                )
            except Exception as exc:
                return jsonify({"error": f"Failed to open receipt path: {exc}"}), 400

    if receipt_file is None:
        return jsonify({"error": "No receipt file provided"}), 400
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "user_id must be an integer"}), 400

    # קוראים את הקובץ לזיכרון (צריך בשביל ה-thread)
    raw_bytes_copy = io.BytesIO(receipt_file.read())
    original_filename = getattr(receipt_file, 'filename', 'unknown')
    original_content_type = getattr(receipt_file, 'content_type', 'application/octet-stream')

    progress_queue = queue.Queue()

    def process_thread():
        session = Session()
        try:
            progress_queue.put({"type": "start", "stage": "קורא קובץ..."})

            from Service.receipt_parser import parse_receipt
            from Service.receipt_service import ReceiptService

            service = ReceiptService(session)

            # שלב 1: חילוץ טקסט
            progress_queue.put({"type": "progress", "stage": "extracting", "message": "מחלץ טקסט מהקובץ..."})
            text = service._read_receipt_text(
                FileStorage(stream=raw_bytes_copy, filename=original_filename, content_type=original_content_type)
            )

            # שלב 2: Parsing
            progress_queue.put({"type": "progress", "stage": "parsing", "message": "מפענח מוצרים..."})
            products, parsed_date = parse_receipt(text)

            if not products:
                progress_queue.put({"type": "error", "error": "לא נמצאו מוצרים בקבלה"})
                return

            total = len(products)
            progress_queue.put({"type": "start_items", "total": total, "message": f"נמצאו {total} מוצרים, מתחיל לזהות..."})

            # יצירת קבלה
            receipt_date = service._resolve_date(parsed_date)
            receipt = Receipt(user_id=user_id, receipt_date=receipt_date)
            service.receipt_repo.add_receipt(receipt)
            session.flush()
            session.refresh(receipt)
            receipt_id = receipt.id

            reception_items = []
            results = []

            # שלב 3: עיבוד כל מוצר (השלב הכי כבד)
            for idx, raw_product in enumerate(products):
                product_name = str(raw_product.get("name", "")) or "מוצר לא ידוע"
                product_code = str(raw_product.get("code", ""))

                progress_queue.put({
                    "type": "item_progress",
                    "current": idx + 1,
                    "total": total,
                    "product_name": product_name,
                    "product_code": product_code,
                    "status": "מזהה...",
                })

                try:
                    product = service.find_or_create_product(raw_product)
                    amount = service.parse_amount(raw_product.get("quantity", 1))
                    reception_item = ReceptionProducts(
                        receipts_id=receipt_id,
                        products_id=product.id,
                        amount=amount
                    )
                    reception_items.append(reception_item)
                    results.append({
                        "reception_id": None,
                        "product_id": product.id,
                        "product_code": product.code,
                        "name": product.name,
                        "amount": amount,
                    })

                    progress_queue.put({
                        "type": "item_done",
                        "current": idx + 1,
                        "total": total,
                        "product_name": product.name,
                        "product_code": product.code,
                        "success": True,
                    })

                except Exception as e:
                    results.append({
                        "product_name": product_name,
                        "product_code": product_code,
                        "success": False,
                        "error": str(e),
                    })

                    progress_queue.put({
                        "type": "item_done",
                        "current": idx + 1,
                        "total": total,
                        "product_name": product_name,
                        "product_code": product_code,
                        "success": False,
                        "error": str(e),
                    })

            # שלב 4: שמירה סופית
            progress_queue.put({"type": "progress", "stage": "saving", "message": "שומר למסד נתונים..."})
            service.reception_repo.add_items(reception_items)
            session.commit()

            for item, response_item in zip(reception_items, results):
                response_item["reception_id"] = item.id

            progress_queue.put({
                "type": "done",
                "receipt_id": receipt_id,
                "receipt_date": receipt_date.isoformat(),
                "products": results,
            })

        except Exception as e:
            progress_queue.put({"type": "error", "error": str(e)})
        finally:
            session.close()

    def generate():
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()

        while True:
            try:
                msg = progress_queue.get(timeout=30.0)
                # מוציאים שדות לא סריאליזביליים (כגון datetime)
                clean_msg = {}
                for k, v in msg.items():
                    try:
                        json.dumps({k: v})
                        clean_msg[k] = v
                    except (TypeError, ValueError):
                        clean_msg[k] = str(v)
                yield f"data: {json.dumps(clean_msg, ensure_ascii=False)}\n\n"

                if msg["type"] in ("done", "error"):
                    break

            except queue.Empty:
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


@receipt_bp.route('/upload', methods=['POST'])
def upload():
    session = Session()
    try:
        receipt_file = request.files.get("receipt")
        receipt_path = request.form.get("receipt") if not receipt_file else None
        user_id = request.form.get("user_id") or request.args.get("user_id")

        if receipt_file is None:
            if receipt_path:
                receipt_path = receipt_path.strip()
                try:
                    with open(receipt_path, 'rb') as f:
                        raw_bytes = f.read()
                    receipt_file = FileStorage(
                        stream=io.BytesIO(raw_bytes),
                        filename=os.path.basename(receipt_path),
                        content_type='application/octet-stream'
                    )
                except Exception as exc:
                    return jsonify({
                        "error": "No receipt file provided and fallback path failed",
                        "receipt_path": receipt_path,
                        "exception": str(exc),
                        "content_type": request.content_type,
                        "request_form": list(request.form.keys()),
                        "request_files": list(request.files.keys()),
                        "request_values": list(request.values.keys())
                    }), 400

        if receipt_file is None:
            return jsonify({
                "error": "No receipt file provided",
                "content_type": request.content_type,
                "request_form": list(request.form.keys()),
                "request_files": list(request.files.keys()),
                "request_values": list(request.values.keys()),
                "receipt_filename": getattr(receipt_file, "filename", None)
            }), 400
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"error": "user_id must be an integer"}), 400

        service = ReceiptService(session)
        result = service.process_receipt(receipt_file, user_id)
        return jsonify(result)
    except ValueError as exc:
        session.rollback()
        try:
            receipt_file.stream.seek(0)
            raw_bytes = receipt_file.read()
            content_length = len(raw_bytes or b"")
        except Exception:
            content_length = None
        return jsonify({
            "error": str(exc),
            "receipt_meta": {
                "filename": receipt_file.filename,
                "content_type": receipt_file.content_type,
                "content_length": content_length
            }
        }), 400
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()

# -----------------------------
# UPDATE RECEIPT
# -----------------------------
@receipt_bp.route('/<int:receipt_id>', methods=['PATCH'])
def update_receipt(receipt_id):
    session = Session()
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")

        if user_id is None:
            return jsonify({"error": "Nothing to update"}), 400

        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"error": "user_id must be an integer"}), 400

        service = ReceiptService(session)
        result = service.update_receipt(receipt_id, user_id=user_id)
        return jsonify(result)
    except ValueError as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()

# -----------------------------
# UPDATE RECEIPT PRODUCT
# -----------------------------
@receipt_bp.route('/<int:receipt_id>/products/<int:item_id>', methods=['PATCH'])
def update_receipt_product(receipt_id, item_id):
    session = Session()
    try:
        data = request.get_json() or {}
        product_id = data.get("product_id")
        amount = data.get("amount")

        item = session.query(ReceptionProducts).get(item_id)
        if not item or item.receipts_id != receipt_id:
            return jsonify({"error": "Receipt product item not found"}), 404

        if product_id is not None:
            try:
                product_id = int(product_id)
            except ValueError:
                return jsonify({"error": "product_id must be an integer"}), 400

        if amount is not None:
            try:
                amount = int(amount)
            except ValueError:
                return jsonify({"error": "amount must be an integer"}), 400

        service = ReceiptService(session)
        result = service.update_reception_product(item_id, product_id=product_id, amount=amount)
        return jsonify(result)
    except ValueError as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()

# -----------------------------
# PROCESS RECEIPT + PRODUCTS
# -----------------------------
@receipt_bp.route('/process/<int:receipt_id>', methods=['POST'])
def process_receipt(receipt_id):
    session = Session()
    try:
        data = request.json
        products = data.get("products", [])

        service = ReceiptService(session)
        result = service.save_receipt_products(receipt_id, products)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        session.close()

# -----------------------------
# GET BY USER ID
# -----------------------------
@receipt_bp.route('/user/<int:user_id>', methods=['GET'])
def get_by_user_id(user_id):
    session = Session()
    try:
        items = session.query(Receipt).filter(Receipt.user_id == user_id).all()
        if not items:
            return jsonify({"error": "not found"}), 404

        return jsonify([
            {
                "id": item.id,
                "user_id": item.user_id,
                "receipt_date": item.receipt_date.isoformat() if item.receipt_date else None
            } for item in items
        ])
    finally:
        session.close()

# -----------------------------
# DELETE RECEIPT
# -----------------------------
@receipt_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    session = Session()
    try:
        item = session.query(Receipt).filter(Receipt.id == id).first()
        if not item:
            return jsonify({"error": "not found"}), 404

        session.delete(item)
        session.commit()
        return jsonify({"message": "deleted"})
    finally:
        session.close()

# -----------------------------
# GET PRODUCTS BY RECEIPT ID
# -----------------------------
@receipt_bp.route('/<int:receipt_id>/products', methods=['GET'])
def get_products_by_receipt(receipt_id):
    session = Session()
    try:
        items = session.query(
            ReceptionProducts,
            Product
        ).join(
            Product,
            ReceptionProducts.products_id == Product.id
        ).filter(
            ReceptionProducts.receipts_id == receipt_id
        ).all()

        return jsonify([
            {
                "id": reception.id,
                "receipt_id": reception.receipts_id,
                "product_id": product.code if product and product.code else product.id,
                "product_code": product.code,
                "product_name": product.name,
                "volume_ml": product.volume_ml,
                "amount": reception.amount
            }
            for reception, product in items
        ])
    finally:
        session.close()

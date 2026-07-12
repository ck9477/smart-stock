"""
Blueprint למילוי עגלה אוטומטית ברמי לוי.
"""

from flask import Blueprint, request, jsonify
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


@rami_levy_bp.route("/fill-cart", methods=["POST"])
def fill_cart():
    """
    ממלא את עגלת רמי לוי במוצרים מרשימת הקניות של המשתמש.

    גוף בקשה: { "user_id": 1 }
    תשובה: { "message": "...", "results": [...] }
    """

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    session = Session()

    try:
        # שליפת רשימת קניות
        items = (
            session.query(ShoppingList)
            .filter(ShoppingList.user_id == user_id)
            .all()
        )

        if not items:
            return jsonify(
                {
                    "message": "רשימת הקניות ריקה",
                    "results": [],
                }
            )

        # הפעלת המתאם
        adapter = RamiLevyAdapter()
        results = []

        try:
            for item in items:
                product = (
                    session.query(Product)
                    .filter(Product.id == item.product_id)
                    .first()
                )

                product_name = (
                    product.name if product else f"מוצר #{item.product_id}"
                )

                try:
                    ok = adapter.process_product(
                        barcode=product.code if product else None,
                        name=product_name,
                        quantity=item.amount,
                    )

                    results.append(
                        {
                            "product_id": item.product_id,
                            "product_name": product_name,
                            "success": ok,
                        }
                    )

                except Exception as e:
                    results.append(
                        {
                            "product_id": item.product_id,
                            "product_name": product_name,
                            "success": False,
                            "error": str(e),
                        }
                    )

            return jsonify(
                {
                    "message": f"מילוי עגלה הסתיים: {sum(1 for r in results if r['success'])}/{len(results)} מוצרים נוספו",
                    "results": results,
                }
            )

        finally:
            adapter.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()
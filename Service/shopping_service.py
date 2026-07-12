# -----------------------------
# imports
# -----------------------------
from sqlalchemy.orm import Session

from models.users import User
from models.Products import Product
from models.shopping_list import ShoppingList
from models.Product_range_for_the_user import ProductRangeForTheUser
from Service.statistics_engine import StatisticsEngine


# -----------------------------
# פונקציה ליצירת רשימת קניות חכמה
# -----------------------------
def generate_shopping_list(session: Session, user_id: int):
    """
    יוצר רשימת קניות חכמה למשתמש, על בסיס:
      1. סטטיסטיקות צריכה מקבלות (StatisticsEngine) — המקור העיקרי
      2. קישורים ידניים (ProductRangeForTheUser) — תוספת/נפילה
    """

    # בדיקת משתמש
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    added_products = []
    seen_ids = set()

    # ──────────────────────────────────────────────────────
    # שלב 1: סטטיסטיקות מקבלות — המקור העיקרי
    # ──────────────────────────────────────────────────────
    engine = StatisticsEngine(session)
    try:
        recommendations = engine.get_weekly_list(user_id)
    except Exception:
        import traceback
        traceback.print_exc()
        recommendations = []

    for rec in recommendations:
        product_id = rec["product_id"]

        if product_id in seen_ids:
            continue
        seen_ids.add(product_id)

        # מוצרים מהסטטיסטיקות באים מקבלות — תמיד יש להם product_id אמיתי
        # המוצר קיים ב-DB (הוא הגיע מ-reception_products)
        quantity = rec.get("recommended_quantity", 1)

        # נסיון לאתר range_enum מקישור ידני (אם קיים), אחרת 7 (=יומי) כברירת מחדל
        manual_range = session.query(ProductRangeForTheUser).filter(
            ProductRangeForTheUser.user_id == user_id,
            ProductRangeForTheUser.Products_id == product_id,
        ).first()
        range_enum = manual_range.Range_id if manual_range else 7

        existing = session.query(ShoppingList).filter(
            ShoppingList.user_id == user_id,
            ShoppingList.product_id == product_id,
        ).first()

        if existing:
            continue

        session.add(ShoppingList(
            user_id=user_id,
            product_id=product_id,
            amount=quantity,
            range_enum=range_enum,
        ))

        product = session.query(Product).filter(Product.id == product_id).first()
        added_products.append({
            "product_id": product_id,
            "product_name": product.name if product else rec.get("product_name"),
            "source": "statistics",
        })

    # ──────────────────────────────────────────────────────
    # שלב 2: קישורים ידניים — משלימים מוצרים שלא הופיעו
    #         בסטטיסטיקות (מוצר חדש, או עדיין אין מספיק נתונים)
    # ──────────────────────────────────────────────────────
    manual_items = session.query(ProductRangeForTheUser).filter(
        ProductRangeForTheUser.user_id == user_id
    ).all()

    for item in manual_items:
        if item.Products_id in seen_ids:
            continue
        seen_ids.add(item.Products_id)

        existing = session.query(ShoppingList).filter(
            ShoppingList.user_id == user_id,
            ShoppingList.product_id == item.Products_id,
        ).first()
        if existing:
            continue

        product = session.query(Product).filter(Product.id == item.Products_id).first()

        session.add(ShoppingList(
            user_id=user_id,
            product_id=item.Products_id,
            amount=1,
            range_enum=item.Range_id,
        ))

        added_products.append({
            "product_id": item.Products_id,
            "product_name": product.name if product else None,
            "source": "manual",
        })

    # שמירה למסד
    session.commit()

    return {
        "message": "Shopping list generated successfully",
        "user_id": user_id,
        "products_added": added_products,
        "total_added": len(added_products),
        "sources": {
            "statistics": sum(1 for p in added_products if p.get("source") == "statistics"),
            "manual": sum(1 for p in added_products if p.get("source") == "manual"),
        },
    }
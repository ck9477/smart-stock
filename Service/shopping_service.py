# -----------------------------
# imports
# -----------------------------
from sqlalchemy.orm import Session

from models.users import User
from models.Products import Product
from models.shopping_list import ShoppingList
from models.Product_range_for_the_user import ProductRangeForTheUser


# -----------------------------
# פונקציה ליצירת רשימת קניות חכמה
# -----------------------------
def generate_shopping_list(session: Session, user_id: int):

    # -----------------------------
    # בדיקת משתמש
    # -----------------------------
    user = session.query(User).filter(User.id == user_id).first()

    if not user:
        raise ValueError(f"User with id {user_id} not found")

    # -----------------------------
    # שליפת כל המוצרים שמותר למשתמש
    # -----------------------------
    allowed_items = session.query(ProductRangeForTheUser).filter(
        ProductRangeForTheUser.user_id == user_id
    ).all()

    # -----------------------------
    # רשימת תוצאות
    # -----------------------------
    added_products = []

    # -----------------------------
    # מעבר על כל המוצרים המותרים
    # -----------------------------
    for item in allowed_items:

        # בדיקה אם כבר קיים ברשימת הקניות
        exists = session.query(ShoppingList).filter(
            ShoppingList.user_id == user_id,
            ShoppingList.product_id == item.Products_id
        ).first()

        if exists:
            continue

        # שליפת מוצר (לשם בלבד בתגובה)
        product = session.query(Product).filter(
            Product.id == item.Products_id
        ).first()

        # הוספה לטבלת shopping list
        session.add(
            ShoppingList(
                user_id=user_id,
                product_id=item.Products_id,
                amount=1,
                range_enum=item.Range_id
            )
        )

        added_products.append({
            "product_id": item.Products_id,
            "product_name": product.name if product else None
        })

    # -----------------------------
    # שמירה למסד
    # -----------------------------
    session.commit()

    # -----------------------------
    # תשובה
    # -----------------------------
    return {
        "message": "Shopping list generated successfully",
        "user_id": user_id,
        "products_added": added_products,
        "total_added": len(added_products)
    }
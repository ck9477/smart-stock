from sqlalchemy.orm import Session

from models.users import User
from models.Products import Product
from models.category import Category
from models.shopping_list import ShoppingList
from models.Product_range_for_the_user import ProductRangeForTheUser
from Service.statistics_engine import StatisticsEngine


def generate_shopping_list(session: Session, user_id: int):

    user = session.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise ValueError(f"User with id {user_id} not found")

    added_products = []
    seen_ids = set()

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

        quantity = rec.get(
            "recommended_quantity",
            1
        )


        manual_range = session.query(ProductRangeForTheUser).filter(
            ProductRangeForTheUser.user_id == user_id,
            ProductRangeForTheUser.Products_id == product_id,
        ).first()


        product = session.query(Product).filter(
            Product.id == product_id
        ).first()


        if manual_range:
            range_enum = manual_range.Range_id

        elif product:
            category = session.query(Category).filter(
                Category.id == product.category_id
            ).first()

            if category:
                range_enum = category.Range_id
            else:
                range_enum = 7

        else:
            range_enum = 7



        existing = session.query(ShoppingList).filter(
            ShoppingList.user_id == user_id,
            ShoppingList.product_id == product_id,
        ).first()


        if existing:
            continue


        session.add(
            ShoppingList(
                user_id=user_id,
                product_id=product_id,
                amount=quantity,
                range_enum=range_enum,
            )
        )


        added_products.append({
            "product_id": product_id,
            "product_name": product.name if product else rec.get("product_name"),
            "source": "statistics",
        })



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


        product = session.query(Product).filter(
            Product.id == item.Products_id
        ).first()


        session.add(
            ShoppingList(
                user_id=user_id,
                product_id=item.Products_id,
                amount=1,
                range_enum=item.Range_id,
            )
        )


        added_products.append({
            "product_id": item.Products_id,
            "product_name": product.name if product else None,
            "source": "manual",
        })


    session.commit()


    return {
        "message": "Shopping list generated successfully",
        "user_id": user_id,
        "products_added": added_products,
        "total_added": len(added_products),
        "sources": {
            "statistics": sum(
                1 for p in added_products
                if p.get("source") == "statistics"
            ),
            "manual": sum(
                1 for p in added_products
                if p.get("source") == "manual"
            ),
        },
    }
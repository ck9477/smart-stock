import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_connection import SessionLocal, engine
from models.base import Base
from models.Products import Product
from models.Range import Range
from models.shopping_list import ShoppingList
# יצירת טבלאות
Base.metadata.create_all(engine)
session = SessionLocal()
try:
    product = session.query(Product).first()
    if not product:
        product = Product(name="wather", category_id=1)
        session.add(product)
        session.commit()
        session.refresh(product)

    range_item = session.query(Range).first()
    if not range_item:
        range_item = Range(range_name="שתיה", Number_of_days=7)
        session.add(range_item)
        session.commit()
        session.refresh(range_item)

    # -------------------------------
    # CREATE SHOPPING LIST ITEM (REAL INSERT)
    # -------------------------------

    new_item = ShoppingList(
        product_id=product.id,
        amount=2,
        range_enum=range_item.id
    )

    session.add(new_item)
    session.commit()
    session.refresh(new_item)

    print("Created Item:")
    print("ID:", new_item.id)
    print("Product:", new_item.product_id)
    print("Amount:", new_item.amount)
    print("Range:", new_item.range_enum)

    all_items = session.query(ShoppingList).all()
    print("\nAll Items:")
    for i in all_items:
        print(i.id, i.product_id, i.amount, i.range_enum)

finally:
    session.close()
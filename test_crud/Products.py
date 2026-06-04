# test_crud/Products.py
import os
import sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.Products import Product, Base
from Repository.Products import ProductRepository
from db_connection import engine, SessionLocal

# -------------------------------
# יצירת טבלאות אם הן לא קיימות
# -------------------------------
Base.metadata.create_all(engine)

# -------------------------------
# יצירת סשן
# -------------------------------
session = SessionLocal()
repo = ProductRepository(session)  # שים לב: פה משתמשים רק בסשן, לא שולחים את המודל

# -------------------------------
# CREATE - הוספת מוצר
# -------------------------------
new_product = Product(
    name="Test p",
    category_id=23,
    volume_ml=500
)
added_product = repo.add(new_product)
print(f"Created Product: {added_product.id}, {added_product.name}, category_id={added_product.category_id}")

# -------------------------------
# READ - קריאה של כל המוצרים
# -------------------------------
all_products = repo.get_all()
print("All Products:", [(p.id, p.name, p.category_id) for p in all_products])

# -------------------------------
# UPDATE - עדכון מוצר
# -------------------------------
# if all_products:
#     product_to_update = all_products[0]
#     updated_product = repo.update(product_to_update.id, name="Updated Product")
#     print(f"Updated Product: {updated_product.id}, {updated_product.name}, category_id={updated_product.category_id}")

# # -------------------------------
# # DELETE - מחיקת מוצר
# # -------------------------------
# if all_products:
#     product_to_delete = all_products[0]
#     deleted = repo.delete(product_to_delete.id)
#     print(f"Deleted Product ID: {product_to_delete.id}")

# -------------------------------
# סגירת הסשן
# -------------------------------
session.close()
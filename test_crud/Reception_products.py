import sys
import os

# הוספת תיקיית הפרויקט ל-Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_connection import SessionLocal, engine
from models.base import Base
from models.category import Category
from models.Products import Product
from models.Reception_products import ReceptionProducts
from models.receipts import Receipt
from Repository.Reception_products import ReceptionProductsRepository

# יצירת סשן
session = SessionLocal()

# יצירת הטבלאות במידה ועדיין לא קיימות
Base.metadata.create_all(engine)

# יצירת ריפוזיטורי
repo = ReceptionProductsRepository(session)

# -------------------------------
# CREATE - הוספת פריט חדש
# -------------------------------
#new_item = ReceptionProducts(receipts_id=3, products_id=2, amount=10)
#added_item = repo.add_item(new_item)
#print("Created Item:", added_item.id, added_item.receipts_id, added_item.products_id, added_item.amount)

# # -------------------------------
# # READ - קבלת כל הפריטים
# # -------------------------------
all_items = repo.get_all_items()
print("All Items:", [(i.id, i.receipts_id, i.products_id, i.amount) for i in all_items])
#
# # -------------------------------
# # DELETE - מחיקת פריט ראשון ברשימה (אם קיים)
# # -------------------------------
#if all_items:
#    deleted_item = repo.delete_item(all_items[0].id)
#     print("Deleted Item:", deleted_item.id)
#else:
#    print("No items to delete")
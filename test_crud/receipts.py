import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_connection import SessionLocal, engine
from models.base import Base
from models.users import User
from models.receipts import Receipt
from Repository.receipts import ReceiptRepository
# יצירת סשן
session = SessionLocal()

# יצירת כל הטבלאות (כולל users ו-receipts)
Base.metadata.create_all(engine)

# יצירת הריפוזיטורי
repo = ReceiptRepository(session)

# -------------------------------
# # CREATE - הוספת קבלה
# # -------------------------------
# new_receipt = Receipt(user_id=36)
# repo.add_receipt(new_receipt)
# print("Created Receipt:", new_receipt.id, new_receipt.user_id, new_receipt.receipt_date)

# -------------------------------
# READ - קבלת כל הקבלות
# -------------------------------
# all_receipts = repo.get_all_receipts()
# print("All Receipts:", [(r.id, r.user_id, r.receipt_date) for r in all_receipts])

# -------------------------------
# DELETE - מחיקת קבלה
# -------------------------------
# all_receipts = repo.get_all_receipts()
# print("All Receipts:", [(r.id, r.user_id, r.receipt_date) for r in all_receipts])
#
# receipt_to_delete = all_receipts[0] if all_receipts else None
# if receipt_to_delete:
#     deleted = repo.delete_receipt(receipt_to_delete.id)
#     print("Deleted Receipt:", deleted.id)
# else:
#     print("No receipts to delete")
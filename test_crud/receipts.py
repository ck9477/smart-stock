import sys
import os

# הוספת תיקיית הפרויקט ל-Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_connection import SessionLocal, engine  # החיבור למסד הנתונים
from moddels.base import Base
from moddels.users import User
from moddels.receipts import Receipt
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
new_receipt = Receipt(user_id=4)
repo.add_receipt(new_receipt)
print("Created Receipt:", new_receipt.id, new_receipt.user_id, new_receipt.receipt_date)

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
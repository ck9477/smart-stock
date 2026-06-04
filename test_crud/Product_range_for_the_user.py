import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_connection import SessionLocal, engine
from models.base import Base
from models.users import User
from models.Range import Range
from models.Products import Product
from models.Product_range_for_the_user import ProductRangeForTheUser
from Repository.Product_range_for_the_user import ProductRangeForTheUserRepository

Base.metadata.create_all(engine)

# יצירת סשן
session = SessionLocal()

# יצירת ריפוזיטורי
repo = ProductRangeForTheUserRepository(session)

# -------------------------------
# CREATE - הוספת פריט חדש
# -------------------------------
new_item = ProductRangeForTheUser(user_id=4, Products_id=5, Range_id=4)
added_item = repo.add_item(new_item)
print("Created Item:", added_item.id, added_item.user_id, added_item.Products_id, added_item.Range_id)
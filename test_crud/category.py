# test_crud_category.py
import os
import sys
from sqlalchemy.orm import sessionmaker
from db_connection import engine, SessionLocal  # ודא שיש לך את db_connection
from moddels.category import Category, Base
from Repository.category import CategoryRepository

# יצירת הטבלאות אם הן לא קיימות
Base.metadata.create_all(engine)

# יצירת סשן
session = SessionLocal()
repo = CategoryRepository(session)

# -------------------------------
# CREATE - הוספת קטגוריות
# -------------------------------
# new_category1 = Category(name="Electronics", Range_id=2)
# new_category2 = Category(name="Books", Range_id=3)
#
# repo.add_category(new_category1)
# repo.add_category(new_category2)
#
# print("Created Categories:")
# for c in [new_category1, new_category2]:
#     print(f"{c.id}: {c.name}, Range_id={c.Range_id}")

# # -------------------------------
# # READ - קבלת כל הקטגוריות
# # -------------------------------
all_categories = repo.get_all_categories()
print("All Categories:", [(c.id, c.name, c.Range_id) for c in all_categories])

# # -------------------------------
# # UPDATE - עדכון קטגוריה
# # -------------------------------
# category_to_update = all_categories[0] if all_categories else None
# if category_to_update:
#     updated = repo.update_category(category_to_update.id, name="Updated Electronics")
#     print("Updated Category:", updated.id, updated.name, updated.Range_id)
#
# # -------------------------------
# # DELETE - מחיקת קטגוריה
# # -------------------------------
category_to_delete = all_categories[1] if all_categories else None
if category_to_delete:
    deleted = repo.delete_category(category_to_delete.id)
    print("Deleted Category:", deleted.id, deleted.name)
else:
    print("No categories to delete")

# סגירת הסשן
session.close()
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_connection import SessionLocal,engine
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# ייבוא המודל והריפוזיטורי
from moddels.users import Base, User
from Repository.users import UserRepository
session = SessionLocal()  # הסשן שאת מייבאת לכל מקום

# יצירת טבלאות
Base.metadata.create_all(engine)

# יצירת הריפוזיטורי
repo = UserRepository(session)

# -------------------------------
# CREATE - הוספת משתמש חדש
# -------------------------------

new_user = User(name="ראעקר", email="ss@example.com", password_hash="434")
repo.add_user(new_user)
print("Created User:", new_user.id, new_user.name)

# -------------------------------
# READ - קבלת כל המשתמשים
# -------------------------------
# all_users = repo.get_all_users()
# print("All Users:", [(u.id, u.name, u.email) for u in all_users])
#
# # -------------------------------
# # UPDATE - שינוי שם
# # -------------------------------
# שליפת המשתמש הקיים לפי id או email
# existing_user = repo.get_user_by_email("c0556789477@gmail.com")
# או: existing_user = repo.get_user_by_id(1)

# עדכון השם
# updated_user = repo.update_user(existing_user.id, name="chani haisherik")
#
# print("Updated User Name:", updated_user.name)
# updated_user = repo.update_user(new_user.id, name="Moshe Cohen")
# print("Updated User Name:", updated_user.name)
#
# # -------------------------------
# # DELETE - מחיקת משתמש
# -------------------------------
# נניח שאתה רוצה למחוק משתמש ששמו "חני"
# user_to_delete = repo.session.query(User).filter(User.name == "hell").first()
#
# if user_to_delete:
#     deleted_user = repo.delete_user(user_to_delete.id)
#     print("Deleted User:", deleted_user.id)
# else:
#     print("No user found with that name.")

# בדיקה סופית
# remaining_users = repo.get_all_users()
# print("Remaining Users:", remaining_users)

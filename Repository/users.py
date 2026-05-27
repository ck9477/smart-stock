from sqlalchemy.orm import Session
from models.users import User  # הנח שהמודל שלך נקרא User

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    # Create - הוספת משתמש חדש
    def add_user(self, user: User):
        self.session.add(user)
        self.session.commit()

        return user

    # Read - קבלת משתמש לפי id
    def get_user_by_id(self, user_id: int):
        return self.session.query(User).filter(User.id == user_id).first()

    # Read - קבלת כל המשתמשים
    def get_all_users(self):
        return self.session.query(User).all()

    # Read - קבלת משתמש לפי email
    def get_user_by_email(self, email: str):
        return self.session.query(User).filter(User.email == email).first()

    # Update - עדכון פרטי משתמש
    def update_user(self, user_id: int, **kwargs):
        user = self.get_user_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            self.session.commit()
        return user

    # Delete - מחיקת משתמש
    def delete_user(self, user_id: int):
        user = self.get_user_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
        return user
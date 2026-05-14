# Repository/category.py
from moddels.category import Category
from sqlalchemy.orm import Session

class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    # CREATE
    def add_category(self, category: Category):
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    # READ - קבלת כל הקטגוריות
    def get_all_categories(self):
        return self.db.query(Category).all()

    # READ - קבלת קטגוריה לפי ID
    def get_category_by_id(self, category_id: int):
        return self.db.query(Category).filter(Category.id == category_id).first()

    # UPDATE
    def update_category(self, category_id: int, name: str = None, Range_id: int = None):
        category = self.get_category_by_id(category_id)
        if not category:
            return None
        if name is not None:
            category.name = name
        if Range_id is not None:
            category.Range_id = Range_id
        self.db.commit()
        self.db.refresh(category)
        return category

    # DELETE
    def delete_category(self, category_id: int):
        category = self.get_category_by_id(category_id)
        if not category:
            return None
        self.db.delete(category)
        self.db.commit()
        return category
# moddels/repositories/shopping_list_repo.py

from sqlalchemy.orm import Session
from models.shopping_list import ShoppingList

class ShoppingListRepository:
    def __init__(self, session):
        self.session = session

    def add_item(self, item):
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get_all_items(self):
        return self.session.query(ShoppingList).all()

    def delete_item(self, item_id):
        item = self.session.query(ShoppingList).get(item_id)
        if item:
            self.session.delete(item)
            self.session.commit()
        return item
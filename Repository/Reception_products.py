from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.Reception_products import ReceptionProducts

class ReceptionProductsRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_items(self, items: List[ReceptionProducts]) -> List[ReceptionProducts]:
        if not items:
            return []
        self.session.add_all(items)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        for item in items:
            try:
                self.session.refresh(item)
            except SQLAlchemyError:
                pass
        return items

    def get_by_id(self, item_id: int):
        return self.session.get(ReceptionProducts, item_id)

    def get_by_receipt_id(self, receipt_id: int):
        return self.session.query(ReceptionProducts)\
            .filter(ReceptionProducts.receipts_id == receipt_id).all()

    def update_item(self, item_id: int, **kwargs):
        item = self.get_by_id(item_id)
        if not item:
            return None
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        try:
            self.session.commit()
            self.session.refresh(item)
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return item

    def delete_item(self, item_id: int) -> bool:
        item = self.get_by_id(item_id)
        if not item:
            return False
        self.session.delete(item)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return True
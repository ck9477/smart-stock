from sqlalchemy.orm import Session
from models.Products import Product  # או הייבוא המתאים לפי הפרויקט שלך

class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, product: Product):
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)  # מחזיר את האובייקט עם ה-ID שנוצר
        return product

    def get_by_id(self, product_id: int):
        return self.session.query(Product).filter(Product.id == product_id).first()

    def get_all(self):
        return self.session.query(Product).all()

    def update(self, product_id: int, **kwargs):
        product = self.get_by_id(product_id)
        if not product:
            return None
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        self.session.commit()
        return product

    def delete(self, product_id: int):
        product = self.get_by_id(product_id)
        if not product:
            return False
        self.session.delete(product)
        self.session.commit()
        return True
from sqlalchemy.orm import Session
from models.Products import Product

class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, product: Product):
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def get_by_id(self, product_id: int):
        return self.session.query(Product).filter(Product.id == product_id).first()

    def get_all(self):
        return self.session.query(Product).all()

    def get_by_code(self, code: str):
        return self.session.query(Product).filter(Product.code == code).first()

    def get_by_name(self, name: str):
        return self.session.query(Product).filter(Product.name == name).first()

    def find_by_code_partial(self, code: str):
        if not code:
            return None
        return self.session.query(Product).filter(Product.code.like(f"%{code}%")).first()

    def find_by_name_partial(self, name: str):
        if not name:
            return None
        return self.session.query(Product).filter(Product.name.ilike(f"%{name}%")).first()

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
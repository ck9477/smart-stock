from sqlalchemy import Column, Integer, ForeignKey
from models.base import Base
from models.receipts import Receipt
from models.Products import Product

class ReceptionProducts(Base):
    __tablename__ = 'reception_products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipts_id = Column(Integer, ForeignKey('receipts.id',ondelete="CASCADE"), nullable=False)
    products_id = Column(Integer, ForeignKey('products.id',ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)
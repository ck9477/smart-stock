from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ReceptionProducts(Base):
    __tablename__ = 'Reception_products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipts_id = Column(Integer, ForeignKey('receipts.id'), nullable=False)
    Products_id = Column(Integer, ForeignKey('Products.id'), nullable=False)
    amount = Column(Integer, nullable=False)
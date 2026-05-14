from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ShoppingList(Base):
    __tablename__ = 'Shopping_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    Products_id = Column(Integer, ForeignKey('Products.id'), nullable=False)
    amount = Column(Integer, nullable=False)
    Range_enum = Column(Integer, ForeignKey('Range.id'), nullable=False)
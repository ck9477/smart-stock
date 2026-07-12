from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
from models.Range import Range
from models.Products import Product

class ShoppingList(Base):
    __tablename__ = 'Shopping_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id',ondelete="CASCADE"), nullable=False, name="Products_id")
    amount = Column(Integer, nullable=False)
    range_enum = Column(Integer, ForeignKey('Range.id',ondelete="CASCADE"), nullable=False, name="Range_enum")

    user_id = Column(
        Integer,
        ForeignKey('dbo.users.id', ondelete="CASCADE"),
        nullable=False,
        name="user_id"
    )

    product = relationship("Product", backref="shopping_items")
    range = relationship("Range", backref="shopping_items")
from sqlalchemy import Column, Integer, ForeignKey
from models.base import Base           # Base המרכזי
from models.Products import Product     # מודל Product
from models.Range import Range         # מודל Range

from sqlalchemy import Column, Integer, ForeignKey
from models.base import Base

class ShoppingList(Base):
    __tablename__ = 'Shopping_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id',ondelete="CASCADE"), nullable=False, name="Products_id")  # שדה בפייתון = product_id, בטבלה = Products_id
    amount = Column(Integer, nullable=False)
    range_enum = Column(Integer, ForeignKey('Range.id',ondelete="CASCADE"), nullable=False, name="Range_enum")
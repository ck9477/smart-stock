from sqlalchemy import Column, Integer, ForeignKey
from models.base import Base        # ✅ להשתמש ב-Base המרכזי
from models.receipts import Receipt  # ✅ ייבוא מודל Receipt כדי שה-FK יעבוד
from models.Products import Product  # ✅ ייבוא מודל Product כדי שה-FK יעבוד

class ReceptionProducts(Base):
    __tablename__ = 'reception_products'  # שמות טבלאות קטנים ומקובלים

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipts_id = Column(Integer, ForeignKey('receipts.id',ondelete="CASCADE"), nullable=False)
    products_id = Column(Integer, ForeignKey('products.id',ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)
from sqlalchemy import Column, Integer, ForeignKey
from models.base import Base

class ProductRangeForTheUser(Base):
    __tablename__ = 'product_range_for_the_user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("dbo.users.id", ondelete="CASCADE"),
        nullable=False
    )
    Products_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    Range_id = Column(Integer, ForeignKey('Range.id',ondelete="CASCADE"), nullable=False)
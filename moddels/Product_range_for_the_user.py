from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ProductRangeForTheUser(Base):
    __tablename__ = 'Product_range_for_the_user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    Products_id = Column(Integer, ForeignKey('Products.id'), nullable=False)
    Range_id = Column(Integer, ForeignKey('Range.id'), nullable=False)

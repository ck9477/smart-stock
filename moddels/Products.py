from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from moddels.base import Base
from moddels.category import Category

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)


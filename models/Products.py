from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)

    category_id = Column(
        Integer,
        ForeignKey('category.id'),
        nullable=False
    )

    code = Column(String(50), unique=True, nullable=True)

    volume_ml = Column(Integer, nullable=True)

    source = Column(String(20), default='manual', nullable=False)
    off_category = Column(String(100), nullable=True)
    off_brand = Column(String(100), nullable=True)

    category = relationship("Category")
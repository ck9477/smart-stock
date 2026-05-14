# models/category.py
from sqlalchemy import Column, Integer, String, ForeignKey
from .base import Base
from .Range import Range  # חשוב לייבא את Range לפני השימוש

class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    Range_id = Column(Integer, ForeignKey('Range.id'), nullable=False)
# models/category.py
from sqlalchemy import Column, Integer, String, ForeignKey
from models.base import Base
from models.Range import Range
class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    Range_id = Column(Integer, ForeignKey('Range.id',ondelete="CASCADE"), nullable=False)  # שם הטבלה ב-FK צריך להיות קטן כמו ב-Range.__tablename__
# class category(Base):
#     __tablename__ = 'category'
#     __table_args__ = {'schema': 'dbo'}  # אם כל השאר בסכימה dbo
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     name = Column(String(50), nullable=False)
#     range_id = Column(Integer, ForeignKey('dbo.range.id'), nullable=False)  # שם הטבלה לפי schema


# models/range.py
from sqlalchemy import Column, Integer, String
from .base import Base

class Range(Base):
    __tablename__ = 'Range'  # שם הטבלה כפי במסד

    id = Column(Integer, primary_key=True, autoincrement=True)
    range_name = Column(String(25), nullable=False)
    Number_of_days = Column(Integer, nullable=False)


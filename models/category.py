from sqlalchemy import Column, Integer, String, ForeignKey
from models.base import Base
from models.Range import Range
class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    Range_id = Column(Integer, ForeignKey('Range.id',ondelete="CASCADE"), nullable=False)



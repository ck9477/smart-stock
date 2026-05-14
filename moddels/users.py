
from sqlalchemy import Column, Integer, String
from .base import Base

class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'dbo'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)

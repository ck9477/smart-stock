from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from .base import Base

class Receipt(Base):
    __tablename__ = 'receipts'
    __table_args__ = {'schema': 'dbo'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('dbo.users.id'), nullable=False)
    receipt_date = Column(DateTime, nullable=False, server_default=func.now())
from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from models.base import Base

class Receipt(Base):
    __tablename__ = 'receipts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("dbo.users.id", ondelete="CASCADE"),
        nullable=False
    )
    receipt_date = Column(DateTime, nullable=True, server_default=func.sysdatetime())

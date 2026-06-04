from sqlalchemy import Column, Integer, String, DateTime, func
from models.base import Base

class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'dbo'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(25), nullable=False)
    email = Column(String(30), nullable=False, unique=True)
    password_hash = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.sysdatetime())

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', created_at={self.created_at})>"
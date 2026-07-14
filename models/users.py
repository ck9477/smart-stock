from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base
from models.rbac import user_role


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'dbo'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(25), nullable=False)
    email = Column(String(30), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.sysdatetime())

    # Many-to-Many: User <-> Role
    roles = relationship("Role", secondary=user_role, lazy="joined")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', created_at={self.created_at})>"

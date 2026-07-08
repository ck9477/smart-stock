"""
מודל לקשר Many-to-Many: User <-> Role <-> Permission
"""

from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


# ── טבלת קשר: User <-> Role ────────────────────────────
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("dbo.users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("dbo.roles.id", ondelete="CASCADE"), primary_key=True),
    schema="dbo",
)

# ── טבלת קשר: Role <-> Permission ──────────────────────
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("dbo.roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("dbo.permissions.id", ondelete="CASCADE"), primary_key=True),
    schema="dbo",
)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "dbo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), nullable=False, unique=True)
    description = Column(String(200), nullable=True)

    def __repr__(self):
        return f"<Permission(name='{self.name}')>"


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "dbo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(200), nullable=True)

    # Many-to-Many: Role <-> Permission
    permissions = relationship("Permission", secondary=role_permission, lazy="joined")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"

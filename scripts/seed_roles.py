"""
Seed: creates base roles + permissions, assigns admin role to user #1.
Safe to re-run — skips already-existing records.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import engine, SessionLocal
from models.base import Base
from models.rbac import *
from models.users import User
import models.rbac  # ensure tables registered on Base.metadata

# Create tables if not exist
Base.metadata.create_all(engine)

session = SessionLocal()

# ── Permissions ─────────────────────────────────────────
PERMISSIONS = [
    ("manage_users", "Create / update / delete users"),
    ("view_all_users", "List and view all users"),
    ("manage_products", "Create / update / delete products"),
    ("view_reports", "View statistics and reports"),
    ("manage_categories", "Create / update / delete categories"),
]

perm_objects = {}
for name, desc in PERMISSIONS:
    existing = session.query(Permission).filter(Permission.name == name).first()
    if not existing:
        p = Permission(name=name, description=desc)
        session.add(p)
        session.flush()
        perm_objects[name] = p
        print(f"  + Permission: {name}")
    else:
        perm_objects[name] = existing
        print(f"  = Permission exists: {name}")

# ── Roles ───────────────────────────────────────────────
ROLES = {
    "admin": {
        "desc": "Full access to all features",
        "perms": ["manage_users", "view_all_users", "manage_products", "view_reports", "manage_categories"],
    },
    "user": {
        "desc": "Standard user — can view own data",
        "perms": [],
    },
    "viewer": {
        "desc": "Read-only access",
        "perms": ["view_reports"],
    },
}

role_objects = {}
for role_name, cfg in ROLES.items():
    existing = session.query(Role).filter(Role.name == role_name).first()
    if not existing:
        r = Role(name=role_name, description=cfg["desc"])
        session.add(r)
        session.flush()
        role_objects[role_name] = r
        print(f"  + Role: {role_name}")
    else:
        role_objects[role_name] = existing
        print(f"  = Role exists: {role_name}")

# Link permissions to roles
for role_name, cfg in ROLES.items():
    role = role_objects[role_name]
    for perm_name in cfg["perms"]:
        perm = perm_objects[perm_name]
        if perm not in role.permissions:
            role.permissions.append(perm)
            print(f"    link: {role_name} -> {perm_name}")

# ── Assign admin to user #1 ─────────────────────────────
admin = session.query(User).filter(User.id == 1).first()
if admin and role_objects["admin"] not in admin.roles:
    admin.roles.append(role_objects["admin"])
    print(f"\n  *** Admin role assigned to user #1 ({admin.name}) ***")
elif admin:
    print(f"\n  = User #1 already has admin role")
else:
    print(f"\n  ! User #1 not found — register first, then re-run this script")

session.commit()
session.close()
print("\nDone.")

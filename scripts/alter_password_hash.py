"""
Script: expand password_hash from VARCHAR(20) to VARCHAR(255) for werkzeug hashes.
One-time run.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_connection import get_connection

conn = get_connection()
cursor = conn.cursor()

try:
    conn.autocommit = False

    # Check current column definition
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'password_hash'
    """)
    row = cursor.fetchone()
    print(f"Before: {row.COLUMN_NAME} -> {row.DATA_TYPE}({row.CHARACTER_MAXIMUM_LENGTH})")

    # ALTER
    cursor.execute("ALTER TABLE users ALTER COLUMN password_hash VARCHAR(255) NOT NULL")
    conn.commit()
    print("OK: password_hash altered to VARCHAR(255)")

    # Verify
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'password_hash'
    """)
    row = cursor.fetchone()
    print(f"After: {row.COLUMN_NAME} -> {row.DATA_TYPE}({row.CHARACTER_MAXIMUM_LENGTH})")

except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")

finally:
    cursor.close()
    conn.close()

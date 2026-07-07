"""
Adds new columns to products table:
- source: where the product came from ('openfoodfacts' or 'manual')
- off_category: category from OpenFoodFacts
- off_brand: brand from OpenFoodFacts
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import engine
from sqlalchemy import text


def run():
    with engine.connect() as conn:
        # Add columns one by one
        for col_name, col_type, col_default in [
            ("source", "NVARCHAR(20)", "'manual'"),
            ("off_category", "NVARCHAR(100)", "NULL"),
            ("off_brand", "NVARCHAR(100)", "NULL"),
        ]:
            try:
                conn.execute(text(f"""
                    IF NOT EXISTS (
                        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_NAME = 'products' AND COLUMN_NAME = '{col_name}'
                    )
                    BEGIN
                        ALTER TABLE products ADD {col_name} {col_type}
                    END
                """))
                conn.commit()
                print(f"[OK] Column {col_name} added")
            except Exception as e:
                print(f"[!] Column {col_name}: {e}")

        # Add CHECK constraint for source
        try:
            conn.execute(text("""
                ALTER TABLE products ADD CONSTRAINT CK_products_source
                CHECK (source IN ('openfoodfacts', 'manual'))
            """))
            conn.commit()
            print("[OK] CHECK constraint added for source")
        except Exception:
            pass  # may already exist

        # Add default for source
        try:
            conn.execute(text("""
                ALTER TABLE products ADD CONSTRAINT DF_products_source
                DEFAULT 'manual' FOR source
            """))
            conn.commit()
            print("[OK] DEFAULT constraint added")
        except Exception:
            pass  # may already exist

    print("\nDone! products table is ready.")


if __name__ == "__main__":
    run()

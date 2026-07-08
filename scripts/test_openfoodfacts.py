"""
Test the OpenFoodFacts pipeline:
1. Lookup by barcode
2. Lookup by name
3. Save to DB
4. Fuzzy matching
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import SessionLocal
from Service.product_lookup_service import ProductLookupService


def test():
    session = SessionLocal()
    service = ProductLookupService(session)

    print("=" * 60)
    print("ProductLookupService Test")
    print("=" * 60)

    test_cases = [
        # Known Israeli product barcode (Coca Cola)
        {"barcode": "7290102645105", "name": "קוקה קולה", "desc": "Known product - should be found on OFF"},
        # Non-existent barcode - falls to fuzzy
        {"barcode": "9999999999999", "name": "חלב תנובה 3%", "desc": "Bad barcode - try fuzzy"},
        # Name only
        {"name": "במבה", "desc": "Name only - API search + fuzzy"},
    ]

    for tc in test_cases:
        print(f"\n>> Testing: {tc['desc']}")
        print(f"   Input: barcode={tc.get('barcode')}, name={tc.get('name')}")

        result = service.lookup(
            barcode=tc.get("barcode"),
            name=tc.get("name"),
        )

        if result:
            print(f"   [FOUND] id={result['id']}, name={result['name']}, "
                  f"barcode={result.get('code')}, source={result.get('source')}")
        else:
            print(f"   [NOT FOUND] (manual entry needed)")

    # Show manual-source products
    print("\n-- Products with source='manual' --")
    pending = service.get_pending_manual()
    if pending:
        for p in pending:
            print(f"  id={p['id']} | {p['name']} | code={p.get('code')}")
    else:
        print("  (none)")

    session.close()
    print("\nDone.")


if __name__ == "__main__":
    test()

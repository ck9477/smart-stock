#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from chiloz.חני1 import extract_single_invoice

try:
    result = extract_single_invoice('attachments (13)/30000219419.pdf')
    print(f'✓ Found {len(result["items"])} products:')
    print()
    for i, item in enumerate(result['items'][:10], 1):
        print(f'{i}. Code: {item["code"]}')
        print(f'   Name: {item["name"]}')
        print(f'   Qty: {item["quantity"]} ({item["unit_type"]})')
        print()
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

import os
import sys
sys.path.insert(0, os.getcwd())
import traceback

from db_connection import SessionLocal
from Repository.Products import ProductRepository

code = '7290110114985'
print('Checking product code:', code)
try:
    session = SessionLocal()
    repo = ProductRepository(session)
    prod = repo.get_by_code(code)
    if prod:
        print('FOUND:', prod.id, prod.name, prod.code)
    else:
        print('NOT FOUND')
    session.close()
except Exception:
    print('DB check failed:')
    traceback.print_exc()

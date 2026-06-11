import io
import os
import sys
import traceback

sys.path.insert(0, os.getcwd())
from Service.receipt_service import ReceiptService
from werkzeug.datastructures import FileStorage

p = os.path.join(os.getcwd(), "attachments (13)", "30000219419.pdf")
print('Parsing file:', p)
with open(p, 'rb') as f:
    raw = f.read()

fs = FileStorage(stream=io.BytesIO(raw), filename=os.path.basename(p), content_type='application/pdf')
svc = ReceiptService(None)
try:
    products = svc.parse_receipt_file(fs)
    print('PARSED_PRODUCTS:')
    print(products)
except Exception as e:
    print('ERROR:')
    traceback.print_exc()

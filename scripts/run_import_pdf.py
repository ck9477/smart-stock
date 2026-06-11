import io
import os
import sys
import traceback
import json

sys.path.insert(0, os.getcwd())
from db_connection import SessionLocal
from Service.receipt_service import ReceiptService
from werkzeug.datastructures import FileStorage
import models.users  # ensure users table is registered in metadata

# choose file from attachments
p = os.path.join(os.getcwd(), "attachments (13)", "30000219419.pdf")
print('Using file:', p)

with open(p, 'rb') as f:
    raw = f.read()

fs = FileStorage(stream=io.BytesIO(raw), filename=os.path.basename(p), content_type='application/pdf')

session = SessionLocal()
service = ReceiptService(session)
try:
    # Ensure a user exists with id=1 (or create a new user and use its id)
    from models.users import User

    user = session.query(User).filter(User.id == 1).first()
    if not user:
        user = User(name='imported_user', email=f'import_{os.getpid()}@local', password_hash='x')
        session.add(user)
        session.flush()
    result = service.process_receipt(fs, user_id=user.id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print('ERROR:')
    traceback.print_exc()
finally:
    session.close()

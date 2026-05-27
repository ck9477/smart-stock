# controllers/base_controller.py

from db_connection import SessionLocal


class BaseController:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        self.db.close()
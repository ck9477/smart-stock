from sqlalchemy.orm import Session
from models.receipts import Receipt


class ReceiptRepository:
    def __init__(self, session: Session):
        self.session = session

    # CREATE
    def add_receipt(self, receipt: Receipt):
        self.session.add(receipt)
        return receipt

    # READ
    def get_receipt_by_id(self, receipt_id: int):
        return self.session.get(Receipt, receipt_id)

    def get_all_receipts(self):
        return self.session.query(Receipt).all()

    # UPDATE
    def update_receipt(self, receipt_id: int, **kwargs):
        receipt = self.get_receipt_by_id(receipt_id)
        if receipt is None:
            return None
        for key, value in kwargs.items():
            if hasattr(receipt, key):
                setattr(receipt, key, value)
        self.session.commit()
        return receipt

    # DELETE
    def delete_receipt(self, receipt_id: int):
        receipt = self.get_receipt_by_id(receipt_id)
        if receipt:
            self.session.delete(receipt)
        return receipt

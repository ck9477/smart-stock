from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from moddels.receipts import Receipt

class ReceiptRepository:
    def __init__(self, session: Session):
        self.session = session

    # CREATE
    def add_receipt(self, receipt: Receipt):
        try:
            with self.session.begin():  # התחלת טרנזקציה
                self.session.add(receipt)
            return receipt
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    # READ
    def get_receipt_by_id(self, receipt_id: int):
        return self.session.query(Receipt).filter(Receipt.id == receipt_id).first()

    def get_all_receipts(self):
        return self.session.query(Receipt).all()

    # DELETE


    def delete_receipt(self, receipt_id: int):
        receipt = self.session.query(Receipt).get(receipt_id)
        if receipt:
            self.session.delete(receipt)
            self.session.commit()
        return receipt
from sqlalchemy.orm import Session
from models.receipts import Receipt
from models.Reception_products import ReceptionProducts
from models.Products import Product

class ReceiptService:
    def __init__(self, session: Session):
        self.session = session

    def create_receipt(self, user_id: int) -> int:
        receipt = Receipt(user_id=user_id)
        self.session.add(receipt)
        self.session.commit()
        self.session.refresh(receipt)
        return receipt.id

    def process_receipt(self, receipt_id: int, products: list) -> dict:
        # בדיקה שהקבלה קיימת
        receipt = self.session.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise ValueError("Receipt not found")

        # רשימת מוצרים קיימים
        existing_products = {p.id for p in self.session.query(Product.id).all()}

        inserted = 0

        for p in products:
            if p["product_id"] in existing_products:
                self.session.add(ReceptionProducts(
                    receipts_id=receipt_id,
                    products_id=p["product_id"],
                    amount=p["amount"]
                ))
                inserted += 1

        self.session.commit()

        return {
            "receipt_id": receipt_id,
            "inserted_products": inserted
        }
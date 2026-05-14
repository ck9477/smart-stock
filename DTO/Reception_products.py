class ReceptionProductDTO:
    def __init__(self, id, receipts_id, products_id, amount):
        self.id = id
        self.receipts_id = receipts_id
        self.products_id = products_id
        self.amount = amount
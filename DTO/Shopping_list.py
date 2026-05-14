class ShoppingListDTO:
    def __init__(self, id, products_id, amount, range_enum):
        self.id = id
        self.products_id = products_id
        self.amount = amount
        self.range_enum = range_enum
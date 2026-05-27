from models.Reception_products import ReceptionProducts

class ReceptionProductsRepository:
    def __init__(self, session):
        self.session = session

    # CREATE
    def add_item(self, item: ReceptionProducts):
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    # READ
    def get_all_items(self):
        return self.session.query(ReceptionProducts).all()

    # DELETE
    def delete_item(self, item_id: int):
        item = self.session.query(ReceptionProducts).get(item_id)
        if item:
            self.session.delete(item)
            self.session.commit()
        return item
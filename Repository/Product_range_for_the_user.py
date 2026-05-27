from models.Product_range_for_the_user import ProductRangeForTheUser

class ProductRangeForTheUserRepository:
    def __init__(self, session):
        self.session = session

    def add_item(self, item):
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get_all_items(self):
        return self.session.query(ProductRangeForTheUser).all()

    def delete_item(self, item_id):
        item = self.session.query(ProductRangeForTheUser).filter_by(id=item_id).first()
        if item:
            self.session.delete(item)
            self.session.commit()
        return item

    def update_item(self, item_id, **kwargs):
        item = self.session.query(ProductRangeForTheUser).filter_by(id=item_id).first()
        if not item:
            return None

        # עדכון השדות שהועברו
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)

        self.session.commit()
        self.session.refresh(item)
        return item
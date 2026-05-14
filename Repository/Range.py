from moddels.Range import Range

class RangeRepository:
    def __init__(self, session):
        self.session = session

    # CREATE
    def add_range(self, range_obj: Range) -> Range:
        self.session.add(range_obj)
        self.session.commit()
        self.session.refresh(range_obj)
        return range_obj

    # READ - כל הרשומות
    def get_all_ranges(self):
        return self.session.query(Range).all()

    # READ - לפי ID
    def get_range_by_id(self, range_id: int):
        return self.session.query(Range).get(range_id)

    # UPDATE
    def update_range(self, range_id: int, new_name: str = None, new_days: int = None):
        range_obj = self.session.query(Range).get(range_id)
        if not range_obj:
            return None
        if new_name is not None:
            range_obj.range_name = new_name
        if new_days is not None:
            range_obj.Number_of_days = new_days
        self.session.commit()
        self.session.refresh(range_obj)
        return range_obj

    # DELETE
    def delete_range(self, range_id: int):
        range_obj = self.session.query(Range).get(range_id)
        if range_obj:
            self.session.delete(range_obj)
            self.session.commit()
        return range_obj
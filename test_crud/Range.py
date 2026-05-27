import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_connection import SessionLocal, engine
from models.base import Base
from models.Range import Range
from Repository.Range import RangeRepository

# יצירת סשן
session = SessionLocal()

# יצירת טבלאות אם לא קיימות
Base.metadata.create_all(engine)

# יצירת ריפוזיטורי
repo = RangeRepository(session)

# CREATE
# new_range = Range(range_name="weekly", Number_of_days=7)
# repo.add_range(new_range)
# print("Created Range:", new_range.id, new_range.range_name, new_range.Number_of_days)

# # READ
all_ranges = repo.get_all_ranges()
print("All Ranges:", [(r.id, r.range_name, r.Number_of_days) for r in all_ranges])

# UPDATE - שינוי שם ומספר ימים של הטווח הראשון
# range_to_update = all_ranges[0] if all_ranges else None
# if range_to_update:
#     updated = repo.update_range(range_to_update.id, new_name="weekly", new_days=7)
#     print("Updated Range:", updated.id, updated.range_name, updated.Number_of_days)
# else:
#     print("No ranges to update")


# DELETE - מחיקת טווח
# range_to_delete = all_ranges[2] if all_ranges else None
# if range_to_delete:
#     deleted = repo.delete_range(range_to_delete.id)
#     print("Deleted Range:", deleted.id, deleted.range_name)
# else:
#     print("No ranges to delete")
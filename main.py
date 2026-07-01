import sys
sys.stdout.reconfigure(encoding='utf-8')

from Service.rami_levy_adapter import RamiLevyAdapter

# הקלטה — 6 מוצרים להדגמה
products = [
    # ברקוד + שם (קיים במלאי)
    {"barcode": "7290112495037", "name": "דגני בוקר קוקומן", "quantity": 2},

    # שם בלבד
    {"name": "חלב תנובה 3%", "quantity": 1},

    # ברקוד לא קיים -> חלופה לפי שם
    {"barcode": "9999999999999", "name": "קוקה קולה זירו", "quantity": 2},

    # ברקוד בלי שם
    {"barcode": "7290000288024", "quantity": 1},

    # פרי עם kg_per_click
    {"name": "בננה", "quantity": 3, "kg_per_click": 0.5},

    # ירק
    {"name": "מלפפון", "quantity": 2, "kg_per_click": 0.5},
]

print("=" * 60)
print("מערכת קניות אוטומטית — רמי לוי")
print("=" * 60)

bot = RamiLevyAdapter()

ok = 0
fail = 0

for p in products:
    result = bot.process_product(
        barcode=p.get("barcode"),
        name=p.get("name"),
        quantity=p.get("quantity", 1),
        kg_per_click=p.get("kg_per_click"),
    )
    if result:
        ok += 1
    else:
        fail += 1

print(f"\n{'='*60}")
print(f"סיכום: {ok} הצליחו, {fail} נכשלו")
print(f"{'='*60}")

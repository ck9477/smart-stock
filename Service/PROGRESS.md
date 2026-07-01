# Rami Levy Adapter — progress

## What works
- Barcode search + name verification + quantities
- Out of stock -> automatic fallback to name search
- Name search + smart scoring + best match
- Quantity (click plus N times)
- **kg_per_click** for fruits/veg — e.g. 3kg with 0.5kg per click = 6 clicks
- Modal/popup closing (BV_modal)
- 404 handling
- Scraped results filtering (fake promo labels removed)

## Entry point
```python
bot.process_product(barcode="729...", name="product", quantity=2)
bot.process_product(name="apple", quantity=3, kg_per_click=0.5)  # fruits/veg
```

## Run
```bash
cd h:/smart-stock-project && .venv/Scripts/python.exe main.py
```

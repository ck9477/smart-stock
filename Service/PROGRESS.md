# Multi-Site Grocery Adapters — Progress

## Architecture
```
BaseGroceryAdapter (ABC)
├── RamiLevyAdapter  – FULL (tested)
├── ShukCityAdapter  – STUB (NotImplementedError)
└── VictoryAdapter   – STUB (NotImplementedError)
```

## What works (all adapters inherit this)
- Browser lifecycle (headless=False default)
- Homepage navigation + 404 retry
- Popup/modal closing (JS + Escape + close buttons)
- Search: type query + Enter
- Smart scoring: word match, brand bonus/penalty, category penalty
- Best-match selection
- Orchestration: barcode→name fallback, name-only path
- Quantity: click N times, kg_per_click support

## Rami Levy (implemented)
- URL: https://www.rami-levy.co.il/he/online
- Scraping: sr-only span → card → name/brand/size/price
- Card expand: click card div
- Plus button: button.plus

## Shuk City (stub)
- URL: https://www.shukcity.co.il
- TODO: implement _scrape_results, _expand_product_card, _click_plus
- TODO: verify selectors after first run

## Victory (stub)
- URL: https://www.victoryonline.co.il
- TODO: implement _scrape_results, _expand_product_card, _click_plus
- TODO: verify selectors after first run

## Usage
```python
# Direct
from Service.grocery_adapters import RamiLevyAdapter
bot = RamiLevyAdapter()
bot.process_product(barcode="729...", name="product", quantity=2)

# Factory
from Service.grocery_adapters import create_adapter
bot = create_adapter("rami_levy")
bot = create_adapter("shuk_city")   # will raise NotImplementedError
bot = create_adapter("victory")     # will raise NotImplementedError

# Backward-compatible (still works)
from Service.rami_levy_adapter import RamiLevyAdapter
```

## Files
- `Service/grocery_adapters/__init__.py` — package init + factory
- `Service/grocery_adapters/base_adapter.py` — abstract base class
- `Service/grocery_adapters/rami_levy.py` — RamiLevyAdapter
- `Service/grocery_adapters/shuk_city.py` — ShukCityAdapter (stub)
- `Service/grocery_adapters/victory.py` — VictoryAdapter (stub)
- `Service/rami_levy_adapter.py` — backward-compatible shim

## Run
```bash
cd h:/smart-stock-project && .venv/Scripts/python.exe main.py
```

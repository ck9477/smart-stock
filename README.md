# Smart Stock — Backend

Python Flask 3.1 REST API with SQLAlchemy 2.0 ORM over Microsoft SQL Server 2022.

---

## Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Runtime |
| Flask 3.1 | Web framework |
| SQLAlchemy 2.0 | ORM (pymssql driver) |
| pdfplumber | PDF receipt parsing |
| Playwright | Browser automation (standalone) |
| Werkzeug | Password hashing (scrypt) |
| flask-cors | CORS middleware |

---

## Quick Start

### Docker (Recommended)

```bash
docker-compose up -d
```

Starts SQL Server, initializes the DB, and runs the API on `http://localhost:5000`.

### Local Dev

```bash
pip install -r requirements.txt
python app.py
```

Requires a running SQL Server instance (set `DB_SERVER`, `DB_PASSWORD`, etc. via env vars).

---

## Project Structure

```
backend/
├── app.py                          # Flask entry point — blueprint registration
├── main.py                         # Standalone Rami Levy automation script
├── config.py                       # DB connection string from env vars
├── db_connection.py                # SQLAlchemy engine + SessionLocal factory
├── Dockerfile                      # Python 3.12 + system deps
├── docker-compose.yml              # Full stack: DB + init + app
├── docker/
│   └── init.sql                    # Full DB schema + demo seed data
├── requirements.txt                # Python dependencies
│
├── models/                         # SQLAlchemy ORM models (8 tables)
│   ├── base.py                     # declarative_base
│   ├── users.py                    # User
│   ├── Products.py                 # Product
│   ├── category.py                 # Category
│   ├── Range.py                    # Range
│   ├── receipts.py                 # Receipt
│   ├── Reception_products.py       # ReceptionProducts
│   ├── shopping_list.py            # ShoppingList
│   └── Product_range_for_the_user.py
│
├── Controler/                      # Flask blueprints (route handlers)
│   ├── base.py                     # BaseController with shared session
│   ├── User.py                     # /users — CRUD + login + search
│   ├── products.py                 # /products — CRUD
│   ├── category.py                 # /category — CRUD
│   ├── range.py                    # /range — CRUD
│   ├── receipts.py                 # /receipts — upload + CRUD
│   ├── receiption_products.py      # /reception-products — CRUD
│   ├── shopping_list.py            # /shopping — generate + CRUD
│   ├── product_renge_for_user.py   # /product-range-for-user — CRUD
│   └── receipt_processing.py       # Standalone ReceiptController class
│
├── Service/                        # Business logic
│   ├── receipt_service.py          # Receipt file parsing (PDF/JSON/text)
│   ├── shopping_service.py         # Smart shopping list generation
│   ├── statistics_engine.py        # Purchase cycle analysis
│   └── rami_levy_adapter.py        # Playwright browser automation
│
├── Repository/                     # Data access layer
│   └── (one file per entity — CRUD methods)
│
├── DTO/                            # Data transfer objects
│   └── (one file per entity — request/response shapes)
│
├── test_crud/                      # Manual CRUD test scripts
│   └── (one file per entity)
│
└── scripts/                        # Utility scripts
    ├── check_product.py
    ├── parse_test.py
    └── run_import_pdf.py
```

---

## Architecture

### Layered Design

```
Controller (Flask Blueprints)     ← HTTP handling, validation, response formatting
        │
   Service Layer                  ← Business logic, parsing, statistics, automation
        │
   Repository Layer               ← Data access, SQLAlchemy queries
        │
   Models (SQLAlchemy ORM)        ← Table declarations
        │
   SQL Server 2022
```

### Key Design Decisions

- **Blueprint-based routes** — one blueprint per entity, registered in `app.py`
- **BaseController** — provides shared SQLAlchemy session handling for all controllers
- **No JWT/sessions** — login returns `user_id`, stored client-side in localStorage
- **CORS enabled globally** — `flask-cors` applied at app level
- **pymssql driver** — no ODBC dependency; uses pure Python driver

---

## Services

### ReceiptService (`Service/receipt_service.py`)

Primary receipt processing pipeline.

| Method | Description |
|---|---|
| `process_receipt(file, user_id)` | Main entry: parse file → create Receipt → find/create Products → create ReceptionProducts |
| `find_or_create_product(raw)` | Lookup by barcode → lookup by name → create with `category_id=22` as fallback |
| `parse_receipt_file(file)` | JSON first, then regex text parsing with Hebrew bidi support |
| `filter_real_products(list)` | Removes noise (delivery notes, promotions, headers, footers) |
| `parse_amount(val)` | Sanitizes to valid int (1–1000) |

### ShoppingService (`Service/shopping_service.py`)

Generates shopping lists from user product-range mappings.

| Method | Description |
|---|---|
| `generate_shopping_list(session, user_id)` | Queries `ProductRangeForTheUser` → creates `ShoppingList` entries for any not yet in the list |

### StatisticsEngine (`Service/statistics_engine.py`)

Purchase cycle analysis.

| Metric | Description |
|---|---|
| `cycle` | Average days between purchases (requires ≥3 purchases) |
| `stability` | Consistency score (0–1) — how regular the cycle is |
| `trend` | Positive = purchases accelerating, negative = slowing |
| `days_since` | Days since last purchase |
| `score` | Composite urgency score (higher = buy sooner) |
| `n` | Number of purchases analyzed |

### RamiLevyAdapter (`Service/rami_levy_adapter.py`)

Playwright browser automation for rami-levy.co.il. Standalone — not part of the Flask app.

| Method | Description |
|---|---|
| `process_product(barcode?, name?, quantity, kg_per_click?)` | Search → scrape results → smart match → add to cart |

Supports barcode search with name-based fallback, and fruits/vegetables with weight-based click amounts.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_SERVER` | `localhost` | SQL Server host |
| `DB_PORT` | `1433` | SQL Server port |
| `DB_NAME` | `SmartStock` | Database name |
| `DB_USERNAME` | `sa` | Database user |
| `DB_PASSWORD` | `SmartStock123!` | Database password |
| `DB_TRUSTED_CONNECTION` | `no` | Windows auth flag |
| `FLASK_ENV` | `development` | Flask environment |

---

## API

Base URL: `http://localhost:5000`

Health check: `GET /test` → `{"message": "working"}`

Full API reference: [docs/rest-api-reference.md](../docs/rest-api-reference.md)

---

## Known Issues

- `db_connection.py` has side effects — it imports Flask and registers routes at module level (refactoring planned)
- Playwright Chromium not in Docker image (network restrictions prevent browser download)
- No Alembic/migration system — schema changes require SQL scripts + volume reset
- Table naming is inconsistent: `Range`, `users`, `category`, `Shopping_list`, `products`, etc. (mixed casing)

# DOCS.md — Backend

This file provides guidance to Claude Code when working with code in the `backend/` directory.

## Commands

```bash
pip install -r requirements.txt   # Install dependencies
python app.py                     # Run Flask dev server on port 5000
```

Node: SQLAlchemy echo mode is enabled (`echo=True` in `db_connection.py`) — all SQL queries print to console.

## Architecture

This is a **Python Flask 3.1 + SQLAlchemy 2.0** REST API for the Smart Stock household inventory system. MS SQL Server 2022 via `pymssql`.

### Stack
- **Framework:** Flask 3.1 with `flask-cors` (CORS enabled globally)
- **ORM:** SQLAlchemy 2.0 with `declarative_base`, sessionmaker
- **DB Driver:** `pymssql` — connection string format: `mssql+pymssql://user:pass@server:port/db`
- **Auth:** Simple email/password, werkzeug `generate_password_hash` / `check_password_hash`. Login returns `user_id` — no JWT, no sessions. Client stores it in localStorage.
- **Config:** `config.py` auto-loads `.env` from the backend directory, exposes all DB/Flask vars + `get_sqlalchemy_connection_string()`

### Layer Architecture

Every request flows through three layers:

```
Controller (Blueprint) → Service (business logic) → Repository (data access)
```

| Layer | Directory | Responsibility |
|---|---|---|
| **Controller** | `Controler/` | Flask blueprints — route definitions, request parsing, response formatting. Some controllers use `BaseController` which provides a shared `SessionLocal` session. `ReceiptController` is a standalone class (mounted in `db_connection.py`). |
| **Service** | `Service/` | Stateless business logic. Takes a `Session` in constructor. No Flask dependencies. |
| **Repository** | `Repository/` | SQLAlchemy CRUD operations. One class per entity. Takes a `Session` in constructor. |
| **Model** | `models/` | SQLAlchemy ORM classes using `Base = declarative_base()` from `models/base.py`. Maps to `dbo` schema (some tables use `dbo` explicitly, others don't). |
| **DTO** | `DTO/` | Plain data classes for typed request/response shapes. |

### Database Setup

- `db_connection.py` creates the global `engine` and `SessionLocal` at module level
- **Important:** `db_connection.py` also creates a standalone Flask app that mounts `ReceiptController` at `/receipt/upload` — this is a known quirk, not the main Flask app
- The main Flask app is in `app.py` — it registers blueprints and runs on `0.0.0.0:{FLASK_PORT}`
- Schema initialization is in `docker/init.sql` — uses `IF NOT EXISTS` guards, creates 8 tables + demo seed data

### Dockerfile

`backend/Dockerfile` builds a Python 3.12 image with ODBC Driver 18 for SQL Server and Playwright. However, Playwright Chromium is NOT installed in the Docker image due to network restrictions — the Rami Levy adapter must run on the host.

### Key Design Issues (Known)
- `db_connection.py` imports Flask and registers routes at module level — unconventional; refactoring planned
- No Alembic or migration tool — schema changes require manual `ALTER TABLE` in `init.sql` + volume reset (`docker compose down -v`)
- Some controllers create their own engine/session instead of using the shared `SessionLocal`

## Controllers (Blueprints)

Each blueprint is registered in `app.py` with a URL prefix:

| Blueprint | Prefix | File |
|---|---|---|
| `user_bp` | `/users` | `Controler/User.py` |
| `category_bp` | `/category` | `Controler/category.py` |
| `product_bp` | `/products` | `Controler/products.py` |
| `range_bp` | `/range` | `Controler/range.py` |
| `receipt_bp` | `/receipts` | `Controler/receipts.py` |
| `reception_bp` | `/reception-products` | `Controler/receiption_products.py` |
| `shopping_bp` | `/shopping` | `Controler/shopping_list.py` |
| `product_range_bp` | `/product-range-for-user` | `Controler/product_renge_for_user.py` |

**Note:** `product_renge_for_user.py` has a typo in the filename ("renge" instead of "range").

## Services

| Service | File | Purpose |
|---|---|---|
| `ReceiptService` | `Service/receipt_service.py` | Parses uploaded receipts (PDF/JSON/text), extracts products, matches by barcode → name → create, creates `Receipt` + `ReceptionProducts` records |
| `ShoppingService` | `Service/shopping_service.py` | `generate_shopping_list(session, user_id)` — reads `product_range_for_the_user`, creates `Shopping_list` entries for products not yet listed |
| `StatisticsEngine` | `Service/statistics_engine.py` | Raw `pymssql` connection (not SQLAlchemy). Queries receipt history, computes: cycle (avg days), stability (0-1), trend acceleration, urgency score. Requires ≥3 purchases per product. |
| `RamiLevyAdapter` | `Service/rami_levy_adapter.py` | Standalone Playwright browser automation. Searches products on rami-levy.co.il by barcode or name, adds to cart. NOT part of Flask — runs on host. |

### Receipt Processing Flow
1. `ReceiptService.parse_receipt_file()` — detects format (PDF → pdfplumber, JSON → `json.loads`, text → regex barcode matching)
2. `ReceiptService.filter_real_products()` — removes noise lines (promo text, headers), requires valid 6-14 digit barcode
3. `ReceiptService.find_or_create_product()` — lookup by code → lookup by name → create new product (in "כללי" category id=8)
4. Creates `Receipt` record → `ReceptionProducts` records → commits
5. Returns `{receipt_id, products: [{reception_id, product_id, product_code, name, amount}]}`

### Statistics Computation
- `StatisticsEngine.fetch_data(user_id)` — raw SQL joining `Reception_products` + `receipts`
- `StatisticsEngine.analyze(rows)` — groups dates by product, computes gaps, filters <3 purchases
- Output per product: `{product_id, cycle, stability, trend, days_since, score, n}`

## Database Schema (8 Tables)

```
users ──┬── receipts ──┬── reception_products ── products ── category ── Range
        │              │
        ├── Shopping_list ── products, Range
        │
        └── product_range_for_the_user ── products, Range
```

- **users** (dbo) — id, name (NVARCHAR 25), email (NVARCHAR 30, unique), password_hash (NVARCHAR 255), created_at
- **category** — id, name (NVARCHAR 50), Range_id (FK → Range)
- **products** — id, name (NVARCHAR 50), category_id (FK → category), code (NVARCHAR 50, unique, nullable), volume_ml (int, nullable)
- **Range** — id, range_name (NVARCHAR 25), Number_of_days (int)
- **receipts** — id, user_id (FK → users), receipt_date
- **reception_products** — id, receipts_id (FK → receipts), products_id (FK → products), amount
- **Shopping_list** — id, Products_id (FK → products), amount, Range_enum (FK → Range, nullable), user_id (FK → users)
- **product_range_for_the_user** — id, user_id (FK → users), Products_id (FK → products), Range_id (FK → Range)

All FKs use `ON DELETE CASCADE`. Full schema + seed data in `docker/init.sql`.

## API Conventions

- **POST** (create) → returns `{"id": <new_id>}` only
- **PUT/PATCH** (update) → returns `{"message": "updated"}` or the updated object
- **DELETE** → returns `{"message": "deleted"}`
- **Errors** → `{"error": "<description>"}` with appropriate HTTP status (400/404/500)
- **File upload** (`POST /receipts/upload`) uses `multipart/form-data` with fields: `receipt` (file) + `user_id` (int)

See [docs/rest-api-reference.md](docs/rest-api-reference.md) for the complete API reference with all endpoints.

## Adding a New Entity

1. Create SQLAlchemy model in `models/`
2. Create Repository class in `Repository/`
3. Create DTO in `DTO/`
4. Create Controller (blueprint) in `Controler/`
5. Register blueprint in `app.py`
6. Add table + seed data to `docker/init.sql`

## Environment Variables

Set via `backend/.env` (auto-loaded by `config.py`):

| Variable | Default | Notes |
|---|---|---|
| `DB_SERVER` | `localhost` | `db` in Docker |
| `DB_PORT` | `1433` | |
| `DB_NAME` | `SmartStock` | |
| `DB_USERNAME` | `sa` | |
| `DB_PASSWORD` | `SmartStock123!` | |
| `DB_TRUSTED_CONNECTION` | `no` | |
| `DB_DRIVER` | `ODBC Driver 18 for SQL Server` | |
| `FLASK_ENV` | `development` | |
| `FLASK_PORT` | `5000` | |

## Testing

CRUD test scripts in `test_crud/` — one per entity. Standalone scripts for manual testing. No automated test framework yet.

## Debugging

- SQLAlchemy echo mode prints all SQL to console
- Flask debug mode enabled in development
- Receipt parsing writes debug output to `debug_receipt.txt`
- Check container logs: `docker logs smart-stock-backend`

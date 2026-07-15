# Development Guide

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker + Docker Compose | Latest | Database + backend containerization |
| Python | 3.12 | Backend development |
| Node.js | 18+ | Frontend development |
| npm | 9+ | Frontend package management |

---

## Getting Started

### Full Stack (Docker)

The easiest way to run the entire stack:

```bash
cd backend
docker-compose up -d
```

This starts three services in order:

1. **SQL Server 2022** — port 1433, with persistent volumes for data and logs
2. **db-init** — runs `docker/init.sql` to create schema and seed demo data, then exits
3. **Flask API** — port 5000, depends on both database and init completing

Health check: `GET http://localhost:5000/test` → `{"message": "working"}`

### Backend (Local Dev)

If you prefer running the backend outside Docker:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

You'll need a running SQL Server instance. Set environment variables if not using defaults (see below).

### Frontend (Local Dev)

```bash
cd frontend
npm install
npm run dev
```

The React app runs on `http://localhost:3000`. The Vite dev server proxies `/api/*` requests to `http://localhost:5000`.

---

## Environment Variables

All variables are centralized in the **root `.env` file** (at `smart-stock/.env`). Copy `.env.example` to `.env` and adjust as needed. Docker Compose reads the root `.env` automatically.

### Root `.env` (used by `docker-compose.yml`)

| Variable | Default | Description |
|---|---|---|
| **Database** | | |
| `DB_SERVER` | `db` | SQL Server hostname (`db` in Docker, `localhost` on host) |
| `DB_PORT` | `1433` | SQL Server port |
| `DB_NAME` | `SmartStock` | Database name |
| `DB_USERNAME` | `sa` | Database user |
| `DB_PASSWORD` | `SmartStock123!` | SA password (must meet SQL Server complexity) |
| `DB_TRUSTED_CONNECTION` | `no` | Windows auth (unused with Docker) |
| **Ports** | | |
| `MSSQL_HOST_PORT` | `1433` | Host port mapped to MSSQL container port 1433 |
| `BACKEND_HOST_PORT` | `5000` | Host port mapped to Flask container port 5000 |
| `FRONTEND_HOST_PORT` | `80` | Host port mapped to nginx container port 80 |
| **Flask** | | |
| `FLASK_ENV` | `development` | Flask environment mode |
| **Frontend (local dev)** | | |
| `VITE_API_URL` | `http://localhost:5000` | Backend URL the Vite dev server proxies to |
| `VITE_DEV_PORT` | `3000` | Vite dev server port |

### Backend (local dev without Docker)

When running `python app.py` directly, use `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `DB_SERVER` | `localhost` | SQL Server hostname |
| `DB_PORT` | `1433` | SQL Server port |
| `DB_NAME` | `SmartStock` | Database name |
| `DB_USERNAME` | `sa` | Database user |
| `DB_PASSWORD` | `SmartStock123!` | Database password |
| `DB_TRUSTED_CONNECTION` | `no` | Windows auth |
| `DB_DRIVER` | `ODBC Driver 18 for SQL Server` | ODBC driver name |
| `FLASK_ENV` | `development` | Flask environment mode |
| `FLASK_PORT` | `5000` | Flask dev server port |

### Frontend (local dev)

Use `frontend/.env` (Vite requires `VITE_` prefix):

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:5000` | Backend API base URL |
| `VITE_DEV_PORT` | `3000` | Vite dev server port |

---

## Project Commands

### Backend

```bash
# Run Flask dev server
python app.py

# Run the Rami Levy automation script (standalone)
python main.py
```

### Frontend

```bash
npm run dev       # Start dev server (localhost:3000)
npm run build     # TypeScript check + Vite production build
npm run preview   # Preview production build locally
```

---

## Database

### Connecting Directly

```bash
docker exec -it smart-stock-db /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'SmartStock123!' -C
```

Then: `USE SmartStock;` to select the database.

### Schema Changes

To modify the schema:

1. Edit `docker/init.sql` — add `ALTER TABLE` statements or new `CREATE TABLE` blocks (with `IF NOT EXISTS` guards)
2. Update the corresponding SQLAlchemy model in `backend/models/`
3. Rebuild: `docker-compose down -v && docker-compose up -d` (the `-v` flag resets volumes)

**Note:** `-v` deletes all data. For production schema changes, write migration scripts instead.

---

## Code Organization

### Backend Layers

| Layer | Directory | Pattern |
|---|---|---|
| Routes | `Controler/` | Flask blueprints, one per entity. Inherit `BaseController` for shared DB session. |
| Services | `Service/` | Stateless business logic. No Flask dependencies. |
| Repositories | `Repository/` | SQLAlchemy queries. One file per entity. |
| Models | `models/` | SQLAlchemy ORM classes with `declarative_base`. |
| DTOs | `DTO/` | Plain data classes for request/response shapes. |

### Frontend Layers

| Layer | Directory | Pattern |
|---|---|---|
| Pages | `src/pages/` | One file per route. Dispatch thunks, read state via hooks. |
| Components | `src/components/` | Reusable UI: layout/, shared/, charts/ |
| Store | `src/store/` | Redux Toolkit: slices + async thunks |
| Services | `src/services/` | Typed Axios wrappers (one per entity) |
| Types | `src/types/models.ts` | All TypeScript interfaces |

---

## Adding a New Entity

### Backend

1. Create SQLAlchemy model in `backend/models/`
2. Create Repository in `backend/Repository/`
3. Create DTO in `backend/DTO/`
4. Create Controller (blueprint) in `backend/Controler/`
5. Register blueprint in `backend/app.py`
6. Add table + seed data to `docker/init.sql`

### Frontend

1. Add TypeScript interfaces to `src/types/models.ts`
2. Create service in `src/services/`
3. Create Redux slice in `src/store/slices/`
4. Create page(s) in `src/pages/`
5. Add routes in `src/routes/index.tsx`

---

## Debugging

### Backend

- SQLAlchemy echo mode is enabled by default (`echo=True` in `db_connection.py`) — all SQL queries are printed to console
- Flask debug mode is on in development
- Check container logs: `docker logs smart-stock`

### Frontend

- Redux DevTools — enabled in development, check browser extension
- Network tab — all API calls go through the Axios instance
- Vite HMR — changes reflect instantly in browser

---

## Testing

CRUD test scripts are located in `backend/test_crud/` — one file per entity. These are standalone scripts for manual testing.

Automated testing is a planned improvement (see [Future Roadmap](future-roadmap.md)).

---

## Known Limitations

- The `db_connection.py` module imports Flask and registers routes at module level — this is unconventional; refactoring is planned
- Playwright Chromium is not installed in the Docker image due to network restrictions; the Rami Levy adapter must run on the host
- No database migrations (Alembic or similar) — schema changes require manual SQL + volume reset
- No JWT or token-based auth — the client stores `user_id` in localStorage

# SupplyChainX

A B2B inventory and supply chain management platform: products, suppliers,
warehouses, purchase orders, customer orders, stock levels, and inventory
movements — all backed by a transactional PostgreSQL core.

This is a portfolio/interview project. The goal is not another CRUD demo —
it's to show correct handling of the things that actually break in
inventory systems: concurrent stock updates, partial receiving, multi-leg
transfers, and reservation vs. on-hand accounting, all inside real
database transactions with row-level locking.

## Business problem

A company selling physical goods needs one system that can answer:
*How much stock do we have, where is it, what's on order, what's
reserved, and what moved today?* SupplyChainX centralizes that instead of
spreading it across spreadsheets.

## Architecture

```
frontend/   React + Vite + Tailwind + TanStack Query + Recharts
backend/    FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL
```

Backend is layered:

```
app/api/        thin route handlers — auth, validation, delegate to services
app/services/    all business logic and transaction boundaries live here
app/models/      SQLAlchemy models — the schema, including CHECK constraints
app/schemas/     Pydantic request/response contracts
app/core/        config, JWT/password security, RBAC dependency
app/database/    engine, session, declarative base
app/utils/       CSV import, seed data
```

Routes never touch the DB for business rules directly — they call a
service function, which owns the transaction.

## Database transaction strategy

Every inventory-changing operation is wrapped in a single DB transaction
and follows the same pattern:

1. Take a row lock on the affected `inventory` row(s) with
   `SELECT ... FOR UPDATE` (`inventory_service._get_or_create_locked_inventory_row`).
2. Validate against the *locked* values (not a stale read from before the
   lock), so two concurrent requests can never both pass validation
   against the same stock.
3. Mutate `inventory` and insert a `stock_movements` row in the same
   transaction.
4. Commit, or roll back everything on any failure.

Multi-step workflows (PO receiving with several line items, a transfer's
outbound + inbound legs, order fulfillment across several line items) call
the single-item functions with `commit=False` and commit once at the end,
so a failure on line 3 of a 5-line PO rolls back lines 1–2 as well —
nothing is left half-applied.

`quantity_on_hand >= 0`, `quantity_reserved >= 0`, and
`quantity_reserved <= quantity_on_hand` are also enforced as PostgreSQL
CHECK constraints, as a second line of defense independent of the Python
code above them.

## Role-based access control

Five roles, enforced on every API request via `require_roles(...)`
(`app/core/permissions.py`). The sidebar hides pages a role cannot use,
and those URLs also show “Access denied” — hiding a menu is never the
real gate.

| Role | Sees | Can do | Warehouse scope |
| --- | --- | --- | --- |
| **Admin** | Everything | Users, warehouses, and every workflow | All |
| **Inventory manager** | Products, inventory, transfers, reports | Catalog, stock adjust, transfers | All |
| **Warehouse manager** | Inventory, transfers, POs, orders | Adjust stock, receive POs, fulfill orders, transfers | Assigned only |
| **Procurement manager** | Suppliers, purchase orders | Create / submit / approve / receive POs | All |
| **Sales** | Customer orders | Create, confirm, cancel — not fulfill | Assigned only |

Demo logins (click a role card on the login page):

- `admin@supplychainx.dev` / `Admin123!`
- `inventory.manager@supplychainx.dev` / `Password123!`
- `warehouse.a@supplychainx.dev` / `Password123!` (Warehouse A)
- `procurement@supplychainx.dev` / `Password123!`
- `sales@supplychainx.dev` / `Password123!` (Warehouse A)

Admins assign warehouses on **Users**. A warehouse manager or sales user
with no assignment sees empty inventory and cannot create orders.

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic, Alembic,
  Pandas (CSV import), Pytest, python-jose + passlib/bcrypt
- **Database:** PostgreSQL (NUMERIC for all money fields — never floats)
- **Frontend:** React, Vite, Tailwind CSS, TanStack Query, Recharts, Axios
- **Infra:** Docker, Docker Compose

## Local development

### Option A — Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

This starts Postgres, runs Alembic migrations, seeds demo data, and
starts both the API (`:8000`) and frontend (`:5173`).

Seed admin login: `admin@supplychainx.dev` / `Admin123!`
(other seeded users: `inventory.manager@…`, `warehouse.a@…`,
`procurement@…`, `sales@…` — all `Password123!`)

### Option B — run backend and frontend separately

```bash
# Postgres (however you prefer — Docker, local install)
createdb supplychainx

cd backend
cp .env.example .env   # edit DATABASE_URL if not using Docker's default
pip install -r requirements.txt --break-system-packages
alembic upgrade head
python -m app.utils.seed
uvicorn app.main:app --reload
```

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

API docs (Swagger): `http://localhost:8000/docs`

## Database migrations

```bash
cd backend
alembic revision --autogenerate -m "description of change"
alembic upgrade head
```

## Testing

```bash
cd backend
# tests run against a real Postgres DB — Postgres-specific behavior
# (row locking, CHECK constraints, ENUM types) doesn't translate to SQLite
createdb supplychainx_test
export TEST_DATABASE_URL=postgresql+psycopg2://supplychainx:supplychainx@localhost:5432/supplychainx_test
pytest -v
```

Coverage includes: auth, RBAC per role, duplicate SKU rejection, negative
stock prevention, stock reservation, partial PO receiving (and rollback
when over-receiving is attempted), warehouse transfers (including
full rollback when one line item in a multi-item transfer can't be
satisfied), and the full order lifecycle (confirm → reserve → fulfill →
cancel).

## CSV import

`POST /api/products/import` accepts a CSV with columns
`sku,name,category,warehouse,quantity,cost_price,reorder_level`, validates
every row (numeric fields, known warehouse codes, duplicate SKUs within
the file), and returns a summary:

```json
{"total_rows": 500, "successful": 482, "failed": 12, "duplicates": 6, "errors": [...]}
```

## Environment variables

See `backend/.env.example` and `frontend/.env.example`.

## What's implemented vs. what's a natural next step

Implemented: full schema + migrations, JWT auth, RBAC, products,
categories, suppliers, warehouses, inventory with row-locked mutations,
stock movements ledger, low-stock detection, purchase orders with partial
receiving, warehouse transfers, customer order reserve/fulfill/cancel,
CSV import, dashboard, SQL-aggregated reports, audit logging, seed data,
Docker Compose, and a Pytest suite covering the transactional core.

Natural next steps if extending this further: PDF report export,
supplier performance report (avg. receiving time), product create/edit
modals in the UI (the API already supports it), and CI running the test
suite against a Postgres service container.

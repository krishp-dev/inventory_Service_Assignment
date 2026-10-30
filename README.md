# Shared Inventory Service

A robust, multi-tenant backend inventory API for businesses sharing inventory across locations, engineered using **Python 3.11+**, **FastAPI**, **SQLAlchemy 2.0**, **Alembic**, **PostgreSQL 16**, **Pydantic v2**, and **pytest**.

---

## 1. Architecture & Security Invariants

- **Multi-Tenant Isolation**: Every database interaction is scoped by `organization_id == current_user.organization_id`. Any cross-tenant attempt returns `HTTP 404 Not Found` (indistinguishable from a non-existent record).
- **Location-Based Access Control**:
  - Items can be available across all organization locations (empty `location_ids`) or restricted to a specific set of locations.
  - A user whose read covers only some locations can only see items available at those locations (any other item returns `404`).
  - To modify an item or its stock, a user's write permission must cover **every location** where the item is available. An item available everywhere requires global write access (`403 Forbidden` otherwise).
  - Organization settings can only be altered by a user holding write permission covering every location (`is_global_write: true`).
- **Overselling Prevention**: Stock adjustments execute `SELECT ... FOR UPDATE` pessimistic row locks inside explicit database transactions. Non-permitted negative balances are rejected with `HTTP 409 Conflict`.
- **Deadlock-Free Bulk Imports**: `POST /stock/import` accepts up to 1,000 rows. Item locks are acquired in **deterministic ascending UUID order (`ORDER BY id ASC`)**, preventing deadlocks. If any row fails, zero changes are committed, and the response is a `422 Unprocessable Entity` listing every failing row and its reason.
- **PostgreSQL JSONB Attributes**: Manages `color`, `size`, and `weight_grams`. Unmanaged keys (e.g. `legacy_code`) are preserved without loss. A PUT with unchanged GET data produces a strict no-op.
- **Audit Ledger**: Every stock adjustment generates an immutable history entry with user ID, timestamp, quantity, direction, comment, and resulting stock balance.

---

## 2. Quickstart & Running PostgreSQL in Docker

### Step 1: Start PostgreSQL 16
```bash
docker run --name inventory-db -e POSTGRES_PASSWORD=inventory \
  -e POSTGRES_DB=inventory -p 5432:5432 -d postgres:16

# Create the dedicated test database
docker exec -it inventory-db createdb -U postgres inventory_test
```

### Step 2: Set Environment Variables
```bash
# Linux / macOS
export DATABASE_URL="postgresql+psycopg2://postgres:inventory@localhost:5432/inventory"
export TEST_DATABASE_URL="postgresql+psycopg2://postgres:inventory@localhost:5432/inventory_test"

# Windows PowerShell
$env:DATABASE_URL="postgresql+psycopg2://postgres:inventory@localhost:5432/inventory"
$env:TEST_DATABASE_URL="postgresql+psycopg2://postgres:inventory@localhost:5432/inventory_test"
```

---

## 3. Database Migrations

Apply Alembic migrations to construct all tables, foreign keys, indexes, and constraints:

```bash
alembic upgrade head
```

Verify downgrade and upgrade integrity:
```bash
alembic downgrade base
alembic upgrade head
```

---

## 4. Database Seeding

Run the idempotent seed script to populate `ABC Retail` with sample locations, items, and users:

```bash
python -m scripts.seed
```

### Seeded Credentials & Roles:
| Username | Password | Role / Location Scope |
| :--- | :--- | :--- |
| `admin` | `Admin@12345` | Full read and write access across all locations |
| `manager` | `Manager@12345` | Read and write access restricted to **Ahmedabad** only |
| `viewer` | `Viewer@12345` | Read-only access across all locations (no write permission) |

---

## 5. Starting the Service

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger)**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## 6. Running the Test Suite

Execute the full integration test suite:

```bash
pytest -v
```

### Verified Test Results:
```text
tests/test_adjustments.py::test_stock_adjustments_and_history PASSED     [  7%]
tests/test_adjustments.py::test_allow_negative_stock PASSED              [ 15%]
tests/test_attributes.py::test_attributes_managed_and_unmanaged_keys PASSED [ 23%]
tests/test_concurrency.py::test_concurrent_removals_20_iterations PASSED [ 30%]
tests/test_concurrency.py::test_concurrent_imports_deadlock_free PASSED  [ 38%]
tests/test_items.py::test_items_crud_and_stock_readonly PASSED           [ 46%]
tests/test_items.py::test_items_pagination PASSED                        [ 53%]
tests/test_organizations.py::test_organization_isolation_items PASSED    [ 61%]
tests/test_permissions.py::test_permission_403_for_users_lacking_read_or_write PASSED [ 69%]
tests/test_permissions.py::test_permission_403_settings_change_restricted_to_global_write PASSED [ 76%]
tests/test_permissions.py::test_location_limited_item_visibility_and_writing PASSED [ 84%]
tests/test_settings.py::test_organization_settings_and_low_stock PASSED  [ 92%]
tests/test_stock_import.py::test_stock_import_all_or_nothing_and_sequential_order PASSED [100%]

======================= 13 passed in 12.01s =======================
```

---

## 7. 20-Run Concurrency Verification Output

Under `test_concurrent_removals_20_iterations`, 20 simultaneous threads attempt to deduct 1 unit from stock of 10. Exactly 10 succeed, exactly 10 fail with `HTTP 409 Conflict`, and final stock is guaranteed to be 0:

```text
Executing 20-run concurrency verification...
  [Iteration  1/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  2/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  3/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  4/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  5/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  6/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  7/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  8/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration  9/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 10/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 11/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 12/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 13/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 14/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 15/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 16/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 17/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 18/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 19/20]: PASS (10 successes, 10 conflicts, final stock 0)
  [Iteration 20/20]: PASS (10 successes, 10 conflicts, final stock 0)
PASSED
```

---

## 8. Safeguard Removal Experiment Script

To inspect the empirical observations from disabling each of the three safeguards (Location Filter, Row Lock, Below-Zero Check):

```bash
python scripts/run_safeguard_experiments.py
```

See [NOTES.md](NOTES.md) for full architectural commentary and threat analysis.

---

## 9. API Endpoints Summary

| Method | Route | Description | Permission Requirement |
| :--- | :--- | :--- | :--- |
| `POST` | `/items` | Create new item (`stock` starts at 0) | Write access covering item locations |
| `GET` | `/items` | Paginated item list (`limit`, `offset`) | Read access covering item locations |
| `GET` | `/items/{id}` | Lookup item by ID (includes `low_stock`) | Read access covering item locations |
| `PUT` | `/items/{id}` | Update item (preserves unmanaged JSONB keys) | Write access covering item locations |
| `DELETE` | `/items/{id}` | Delete item | Write access covering item locations |
| `POST` | `/items/{id}/adjustments` | Adjust stock (`add`/`remove`, 409 if negative) | Write access covering item locations |
| `GET` | `/items/{id}/history` | Paginated stock adjustment audit ledger | Read access covering item locations |
| `POST` | `/stock/import` | Bulk import 1-1,000 rows (deadlock-free) | Write access covering each row item |
| `GET` | `/settings` | Retrieve organization `low_stock_level` | Read access |
| `PUT` | `/settings` | Update `low_stock_level` | **Global write access across all locations** |
| `GET` | `/health` | Service health status | Public |

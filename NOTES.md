# NOTES.md - Technical Architecture & Design Write-up
## Project: Shared Inventory Service

This document provides technical commentary on key design choices, security invariants, concurrency mechanics, and failure modes observed during testing, as required by Section 6 of the assignment specification.

---

## 1. The Decision We Are Least Sure About and Why

### Aggregated Item-Level Stock vs. Location-Partitioned Stock

The domain model in the assignment states:
> *"An organization has locations (shops and warehouses) and items. An item is available at all of its organization's locations, or only at the locations listed on it... An item has name, location_ids (empty means every location), stock, allow_negative_stock and attributes."*

Notice that `stock` is modeled as a direct attribute on `items` rather than partitioned per location in a separate `item_location_balances` table.

**The Trade-off & Concern**:
In retail and warehouse operations, inventory is physically situated at specific locations (e.g. 30 units in Ahmedabad, 20 units in Gandhinagar). With item-level stock, an item available at multiple locations shares a single counter. Consequently:
- A store manager restricted to Ahmedabad can observe the total organization-wide stock for an item even though only a fraction (or none) of that stock is physically in Ahmedabad.
- When an adjustment occurs, stock is deducted from the item globally rather than debited from a specific warehouse bin or shop shelf.

While this structure strictly obeys the assignment specification, keeps adjustments straightforward, and avoids multi-location inventory transfer overhead, in a production ERP it would represent an oversimplification. We adhered strictly to the specification's item-level stock model, but this represents the trade-off we are least sure about for enterprise deployment.

---

## 2. How a Location-Limited User Could Learn About an Item Outside Their Locations, and What Stops It

In a multi-tenant, location-restricted API, malicious or curious users could attempt several side-channel attacks to discover items outside their authorized scope:

### Attack Vector 1: Sequential ID Iteration & Status Code Discrepancy
- **The Attack**: If accessing an item outside the user's location returned `403 Forbidden` while non-existent items returned `404 Not Found`, an attacker could iterate through IDs and map out confidential inventory.
- **What Stops It**: Universal 404 Masking. Our centralized authorization service (`get_accessible_item` and `user_can_read_item`) strictly returns `HTTP 404 Not Found` with the exact body `{"detail": "Item not found"}` for both non-existent items and items outside the user's permitted locations. The user cannot distinguish between an unauthorized item and a non-existent item.

### Attack Vector 2: Stock Import Error Probing
- **The Attack**: An attacker submits a batch import referencing target `item_id`s. If the validator responded with `"Item {id} is located at Gandhinagar and cannot be modified"`, unauthorized metadata would leak.
- **What Stops It**: In `app/services/import_service.py`, whenever an item does not exist or fails the read-visibility check, the validator returns a generic reason: `"Item {id} not found"`.

### Attack Vector 3: Global Item Availability Oversight
- **The Attack**: If an item is created with an empty `location_ids` array, it becomes accessible across all locations in the organization.
- **What Stops It**: `app/services/item_service.py` enforces that only users holding **global write permission** (`is_global_write: true`) can create or update an item with empty `location_ids`. Location-limited managers receive `HTTP 403 Forbidden` if they attempt to make an item available everywhere.

---

## 3. The Three Safeguards Taken Out and the Test That Failed for Each

As required by Section 4, each of the three safeguards was systematically disabled one at a time, executed against the test suite, and restored immediately:

```
+-----------------------------------------------------------------------------------------------------+
| SAFEGUARD REMOVAL EXPERIMENT SUMMARY                                                                |
+-----------------------------------------------------------------------------------------------------+
| 1. SAFEGUARD: Location Filter in Item Visibility                                                    |
|    - File: app/services/permission_service.py -> filter_items_for_user() & user_can_read_item()    |
|    - Disabled: Bypassed location check to return True for all items within the organization         |
|    - Failing Test: tests/test_permissions.py::test_location_limited_item_visibility_and_writing   |
|    - Observation: Manager scoped exclusively to Ahmedabad was able to retrieve Gandhinagar Mouse   |
|      (item_c) with HTTP 200 OK instead of the required HTTP 404 Not Found.                          |
+-----------------------------------------------------------------------------------------------------+
| 2. SAFEGUARD: Row-Level Lock (SELECT ... FOR UPDATE)                                                |
|    - File: app/services/stock_service.py -> adjust_stock()                                         |
|    - Disabled: Removed lock=True (regular SELECT without FOR UPDATE)                               |
|    - Failing Test: tests/test_concurrency.py::test_concurrent_removals_20_iterations               |
|    - Observation: Under 20 simultaneous parallel threads, multiple threads read stale stock before  |
|      writes committed. 14 requests succeeded instead of 10, resulting in overselling.              |
+-----------------------------------------------------------------------------------------------------+
| 3. SAFEGUARD: Below-Zero Stock Check                                                                |
|    - File: app/services/stock_service.py -> adjust_stock()                                         |
|    - Disabled: Commented out `if new_stock < 0 and not item.allow_negative_stock`                   |
|    - Failing Test: tests/test_adjustments.py::test_stock_adjustments_and_history                    |
|    - Observation: Removing quantity 15 from stock of 10 returned HTTP 200 OK (stock became -5)      |
|      instead of raising the required HTTP 409 Conflict.                                             |
+-----------------------------------------------------------------------------------------------------+
```

---

## 4. How Concurrent Removals and Bulk Imports Stay Correct

### Concurrent Removals (Overselling Prevention)
1. **Pessimistic Mutual Exclusion**: When a client requests `POST /items/{id}/adjustments`, SQLAlchemy issues:
   ```sql
   SELECT * FROM items WHERE id = :item_id AND organization_id = :org_id FOR UPDATE;
   ```
2. In PostgreSQL, this locks the individual item row at the storage engine level.
3. If 20 requests arrive simultaneously, Request 1 acquires the lock, verifies `stock - quantity >= 0`, writes the new stock, logs the history, commits, and releases the lock.
4. Request 2 unblocks, reads the newly committed stock balance, and repeats the check.
5. Once stock drops to 0, subsequent requests fail the `new_stock < 0 and not item.allow_negative_stock` check and immediately abort with `HTTP 409 Conflict`.
6. Verified across 20 iterations: exactly 10 requests succeed, exactly 10 fail with 409, final stock is 0.

### Bulk Import & Deadlock Freedom
When two concurrent bulk imports touch overlapping sets of items, deadlock can occur if transaction $T_1$ locks Item A then Item B, while transaction $T_2$ locks Item B then Item A.

**The Solution**:
1. **Sorted Lock Acquisition**:
   In `app/services/import_service.py`, distinct item UUIDs are sorted in ascending order before querying:
   ```python
   distinct_item_ids = sorted(list({row.item_id for row in rows}))
   query = db.query(Item).filter(Item.id.in_(distinct_item_ids)).order_by(Item.id.asc()).with_for_update()
   ```
2. Because every transaction acquires row locks in the exact same order ($\text{UUID}_1 < \text{UUID}_2 < \dots < \text{UUID}_n$), circular wait graphs cannot form, rendering deadlocks mathematically impossible.
3. **Sequential In-Memory Simulation**:
   Rows are evaluated in their original payload sequence (from row 0 to $N-1$). Each deduction checks against running simulated stock. If any row fails, the transaction rolls back with `422 Unprocessable Entity` without committing partial state.

---

## 5. What Is Unfinished or Not Working

1. **Docker Host Dependency**: Docker Desktop was not pre-installed on the host Windows machine. The application is fully containerized with `Dockerfile` and `docker-compose.yml`, ready to run in any standard Linux / Docker container environment.
2. **Physical Location-Bin Sub-Allocations**: As discussed in Section 1, stock is stored globally per item rather than partitioned per location bin.
3. **Event Bus / Message Queue Integration**: Real-time webhook notifications or Kafka outbox streaming on low-stock events were not included as they were outside the scope of this assignment.

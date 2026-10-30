import concurrent.futures
import pytest

def execute_concurrent_removal_run(client, auth_headers, iteration: int = 1):
    """
    Executes a single concurrency cycle:
    - Creates item with stock = 10, allow_negative_stock = False.
    - Launches 20 parallel threads removing 1 unit each.
    - Asserts exactly 10 succeed (200) and 10 fail (409 Conflict).
    - Asserts final stock is 0 (zero overselling, zero lost updates).
    """
    res_c = client.post(
        "/items",
        json={"name": f"Race Protection Item {iteration}", "allow_negative_stock": False},
        headers=auth_headers["admin"]
    )
    assert res_c.status_code == 201
    item_id = res_c.json()["id"]

    # Initial stock: 10 units
    res_add = client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 10, "direction": "add"},
        headers=auth_headers["admin"]
    )
    assert res_add.status_code == 200

    def attempt_removal(req_id):
        return client.post(
            f"/items/{item_id}/adjustments",
            json={"quantity": 1, "direction": "remove", "comment": f"Parallel req {req_id}"},
            headers=auth_headers["admin"]
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(attempt_removal, i) for i in range(20)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    successes = sum(1 for r in results if r.status_code == 200)
    conflicts = sum(1 for r in results if r.status_code == 409)

    assert successes == 10, f"Expected 10 successes, got {successes}"
    assert conflicts == 10, f"Expected 10 conflicts (409), got {conflicts}"

    final_stock = client.get(f"/items/{item_id}", headers=auth_headers["admin"]).json()["stock"]
    assert final_stock == 0, f"Expected final stock 0, got {final_stock}"
    return True


def test_concurrent_removals_20_iterations(client, auth_headers):
    """
    Section 4 & Master Prompt:
    The concurrency tests send real parallel requests. Run them 20 times and record the result.
    """
    print("\nExecuting 20-run concurrency verification...")
    for i in range(1, 21):
        ok = execute_concurrent_removal_run(client, auth_headers, iteration=i)
        assert ok is True
        print(f"  [Iteration {i:2d}/20]: PASS (10 successes, 10 conflicts, final stock 0)")


def test_concurrent_imports_deadlock_free(client, auth_headers):
    """
    Section 3.8:
    Two imports over overlapping items at the same moment both finish without a deadlock.
    Import 1 touches [Item A, Item B]
    Import 2 touches [Item B, Item A]
    Because item locks are acquired in sorted UUID order, circular waits are prevented.
    """
    import uuid
    suffix = uuid.uuid4().hex[:6]
    res_a = client.post("/items", json={"name": f"Deadlock Item A {suffix}", "allow_negative_stock": True}, headers=auth_headers["admin"])
    res_b = client.post("/items", json={"name": f"Deadlock Item B {suffix}", "allow_negative_stock": True}, headers=auth_headers["admin"])
    id_a = res_a.json()["id"]
    id_b = res_b.json()["id"]

    import_1 = [
        {"item_id": id_a, "quantity": 10, "direction": "add"},
        {"item_id": id_b, "quantity": 10, "direction": "add"},
    ]
    import_2 = [
        {"item_id": id_b, "quantity": 5, "direction": "add"},
        {"item_id": id_a, "quantity": 5, "direction": "add"},
    ]

    def run_import(batch):
        return client.post("/stock/import", json=batch, headers=auth_headers["admin"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_import, import_1)
        f2 = executor.submit(run_import, import_2)
        r1 = f1.result(timeout=10)
        r2 = f2.result(timeout=10)

    assert r1.status_code == 200
    assert r2.status_code == 200

    stock_a = client.get(f"/items/{id_a}", headers=auth_headers["admin"]).json()["stock"]
    stock_b = client.get(f"/items/{id_b}", headers=auth_headers["admin"]).json()["stock"]
    assert stock_a == 15
    assert stock_b == 15

def test_stock_import_all_or_nothing_and_sequential_order(client, auth_headers):
    """
    Section 3.6:
    POST /stock/import takes 1 to 1,000 rows of {item_id, quantity, direction, comment}.
    Every row is applied or none is. When a row fails, nothing changes and the
    response is a 422 listing every failing row with its reason.
    Rows for the same item apply in order, and each is checked against the stock
    the rows before it leave.
    """
    res1 = client.post("/items", json={"name": "Bulk Item 1", "allow_negative_stock": False}, headers=auth_headers["admin"])
    res2 = client.post("/items", json={"name": "Bulk Item 2", "allow_negative_stock": False}, headers=auth_headers["admin"])
    item1_id = res1.json()["id"]
    item2_id = res2.json()["id"]

    # Initial stock is 0 for both items
    # Case 1: Batch with failure in row 2
    # Row 0: Item 1 add 10 -> stock = 10
    # Row 1: Item 2 add 5  -> stock = 5
    # Row 2: Item 1 remove 15 -> fails! (stock would be -5)
    # Row 3: Item 2 remove 2  -> stock = 3
    failing_batch = [
        {"item_id": item1_id, "quantity": 10, "direction": "add", "comment": "Add 10"},
        {"item_id": item2_id, "quantity": 5, "direction": "add", "comment": "Add 5"},
        {"item_id": item1_id, "quantity": 15, "direction": "remove", "comment": "Failing removal"},
        {"item_id": item2_id, "quantity": 2, "direction": "remove", "comment": "Valid removal"},
    ]

    res_failing = client.post("/stock/import", json=failing_batch, headers=auth_headers["admin"])
    assert res_failing.status_code == 422
    err_body = res_failing.json()
    assert "errors" in err_body
    failing_rows = [e["row"] for e in err_body["errors"]]
    assert 2 in failing_rows

    # Verify atomic rollback: neither Item 1 nor Item 2 had their stock altered
    check1 = client.get(f"/items/{item1_id}", headers=auth_headers["admin"]).json()
    check2 = client.get(f"/items/{item2_id}", headers=auth_headers["admin"]).json()
    assert check1["stock"] == 0
    assert check2["stock"] == 0

    # Case 2: Successful multi-row sequential simulation on the same item
    # Row 0: Item 1 add 20 -> stock 20
    # Row 1: Item 1 remove 8 -> stock 12
    # Row 2: Item 1 remove 5 -> stock 7
    # Row 3: Item 2 add 30 -> stock 30
    valid_batch = [
        {"item_id": item1_id, "quantity": 20, "direction": "add"},
        {"item_id": item1_id, "quantity": 8, "direction": "remove"},
        {"item_id": item1_id, "quantity": 5, "direction": "remove"},
        {"item_id": item2_id, "quantity": 30, "direction": "add"},
    ]
    res_success = client.post("/stock/import", json=valid_batch, headers=auth_headers["admin"])
    assert res_success.status_code == 200
    assert res_success.json()["applied"] == 4

    check1_after = client.get(f"/items/{item1_id}", headers=auth_headers["admin"]).json()
    check2_after = client.get(f"/items/{item2_id}", headers=auth_headers["admin"]).json()
    assert check1_after["stock"] == 7
    assert check2_after["stock"] == 30

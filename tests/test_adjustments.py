def test_stock_adjustments_and_history(client, auth_headers):
    """
    Section 3.4:
    POST /items/{id}/adjustments with {quantity, direction, comment}
    Quantity >= 1, direction 'add' or 'remove'
    Each adjustment writes history entry.
    Removal below 0 is 409 unless allow_negative_stock is True.
    GET /items/{id}/history returns newest first, paginated.
    """
    # 1. Create item with stock=0, allow_negative_stock=False
    res_c = client.post(
        "/items",
        json={"name": "Gaming Console", "allow_negative_stock": False},
        headers=auth_headers["admin"]
    )
    item_id = res_c.json()["id"]

    # 2. Validation: quantity < 1 -> 422
    assert client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 0, "direction": "add"},
        headers=auth_headers["admin"]
    ).status_code == 422

    # 3. Validation: invalid direction -> 422
    assert client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 5, "direction": "increment"},
        headers=auth_headers["admin"]
    ).status_code == 422

    # 4. Valid add of 10 units -> stock = 10
    res_add = client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 10, "direction": "add", "comment": "PO-991 Delivery"},
        headers=auth_headers["admin"]
    )
    assert res_add.status_code == 200
    assert res_add.json()["stock"] == 10

    # 5. Removal of 15 (exceeding stock 10) -> MUST be 409 Conflict
    res_409 = client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 15, "direction": "remove", "comment": "Over-deduction attempt"},
        headers=auth_headers["admin"]
    )
    assert res_409.status_code == 409
    assert "negative stock" in res_409.json()["detail"].lower()

    # Stock must remain unchanged at 10
    check_item = client.get(f"/items/{item_id}", headers=auth_headers["admin"]).json()
    assert check_item["stock"] == 10

    # 6. Valid remove of 4 -> stock = 6
    res_rem = client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 4, "direction": "remove", "comment": "Customer sale"},
        headers=auth_headers["admin"]
    )
    assert res_rem.status_code == 200
    assert res_rem.json()["stock"] == 6

    # 7. GET /items/{id}/history (newest first, paginated)
    res_hist = client.get(f"/items/{item_id}/history", headers=auth_headers["admin"])
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert hist["total"] == 2
    entries = hist["items"]
    assert len(entries) == 2
    # First entry (newest): remove 4
    assert entries[0]["direction"] == "remove"
    assert entries[0]["quantity"] == 4
    assert entries[0]["stock_after"] == 6
    assert entries[0]["comment"] == "Customer sale"
    # Second entry: add 10
    assert entries[1]["direction"] == "add"
    assert entries[1]["quantity"] == 10
    assert entries[1]["stock_after"] == 10


def test_allow_negative_stock(client, auth_headers):
    """Items with allow_negative_stock=True can have stock drop below 0."""
    res_c = client.post(
        "/items",
        json={"name": "Backordered Books", "allow_negative_stock": True},
        headers=auth_headers["admin"]
    )
    item_id = res_c.json()["id"]

    # Deduct 8 from initial 0 stock
    res_rem = client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 8, "direction": "remove", "comment": "Backordered order #104"},
        headers=auth_headers["admin"]
    )
    assert res_rem.status_code == 200
    assert res_rem.json()["stock"] == -8

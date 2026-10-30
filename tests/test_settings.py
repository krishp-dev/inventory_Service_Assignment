def test_organization_settings_and_low_stock(client, auth_headers):
    """
    Section 3.7:
    GET /settings and PUT /settings with low_stock_level (an integer, 0 or more).
    Item reads include low_stock, which is true when the item's stock is at or below that level.
    """
    # 1. Update settings: low_stock_level = 5
    res_put = client.put("/settings", json={"low_stock_level": 5}, headers=auth_headers["admin"])
    assert res_put.status_code == 200
    assert res_put.json()["low_stock_level"] == 5

    # 2. Validation 422: low_stock_level < 0
    assert client.put("/settings", json={"low_stock_level": -1}, headers=auth_headers["admin"]).status_code == 422

    # 3. Create two items:
    # Item 1: stock 4 (<= 5, so low_stock should be True)
    # Item 2: stock 6 (> 5, so low_stock should be False)
    res1 = client.post("/items", json={"name": "Low Threshold Item"}, headers=auth_headers["admin"])
    item1_id = res1.json()["id"]
    client.post(f"/items/{item1_id}/adjustments", json={"quantity": 4, "direction": "add"}, headers=auth_headers["admin"])

    res2 = client.post("/items", json={"name": "High Threshold Item"}, headers=auth_headers["admin"])
    item2_id = res2.json()["id"]
    client.post(f"/items/{item2_id}/adjustments", json={"quantity": 6, "direction": "add"}, headers=auth_headers["admin"])

    # 4. Check Item 1: low_stock is True
    check1 = client.get(f"/items/{item1_id}", headers=auth_headers["admin"]).json()
    assert check1["stock"] == 4
    assert check1["low_stock"] is True

    # 5. Check Item 2: low_stock is False
    check2 = client.get(f"/items/{item2_id}", headers=auth_headers["admin"]).json()
    assert check2["stock"] == 6
    assert check2["low_stock"] is False

    # 6. Adjust threshold down to 3: now Item 1 (stock 4) is no longer low stock
    client.put("/settings", json={"low_stock_level": 3}, headers=auth_headers["admin"])
    check1_new = client.get(f"/items/{item1_id}", headers=auth_headers["admin"]).json()
    assert check1_new["low_stock"] is False

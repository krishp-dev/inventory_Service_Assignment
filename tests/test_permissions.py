def test_permission_403_for_users_lacking_read_or_write(client, auth_headers):
    """
    Section 3.2:
    A request without the needed permission is a 403.
    """
    # User without read permission receives 403 on read routes
    assert client.get("/items", headers=auth_headers["noread"]).status_code == 403
    assert client.get("/settings", headers=auth_headers["noread"]).status_code == 403

    # Viewer without write permission receives 403 on write routes
    assert client.post("/items", json={"name": "Forbidden Item"}, headers=auth_headers["viewer"]).status_code == 403
    assert client.post(
        "/stock/import",
        json=[{"item_id": "00000000-0000-0000-0000-000000000000", "quantity": 1, "direction": "add"}],
        headers=auth_headers["viewer"]
    ).status_code == 403


def test_permission_403_settings_change_restricted_to_global_write(client, auth_headers):
    """
    Section 3.2:
    Organization settings (3.7) change only for a user whose write covers every location. Anyone else gets a 403.
    """
    # Manager has write permission restricted to Ahmedabad only -> MUST get 403
    res_mgr = client.put("/settings", json={"low_stock_level": 25}, headers=auth_headers["manager"])
    assert res_mgr.status_code == 403
    assert "every location" in res_mgr.json()["detail"].lower()

    # Viewer has no write permission -> MUST get 403
    res_v = client.put("/settings", json={"low_stock_level": 25}, headers=auth_headers["viewer"])
    assert res_v.status_code == 403

    # Admin covers all locations -> MUST succeed
    res_admin = client.put("/settings", json={"low_stock_level": 25}, headers=auth_headers["admin"])
    assert res_admin.status_code == 200
    assert res_admin.json()["low_stock_level"] == 25


def test_location_limited_item_visibility_and_writing(client, auth_headers, seed_test_data):
    """
    Section 3.2:
    A user whose read covers only some locations sees only the items available at those locations:
    in lists, in lookups by id, and in stock history entries that name an item. Any other item is a 404.
    For an item available everywhere, only global write access can modify it.
    """
    loc_ahm_id = str(seed_test_data["loc_ahm_id"])
    loc_gan_id = str(seed_test_data["loc_gan_id"])

    # 1. Create Item A (available everywhere, empty location_ids)
    res_a = client.post(
        "/items",
        json={"name": "Global Laptop", "location_ids": []},
        headers=auth_headers["admin"]
    )
    assert res_a.status_code == 201
    item_a_id = res_a.json()["id"]

    # 2. Create Item B (available ONLY at Ahmedabad)
    res_b = client.post(
        "/items",
        json={"name": "Ahmedabad Keyboard", "location_ids": [loc_ahm_id]},
        headers=auth_headers["admin"]
    )
    assert res_b.status_code == 201
    item_b_id = res_b.json()["id"]

    # 3. Create Item C (available ONLY at Gandhinagar)
    res_c = client.post(
        "/items",
        json={"name": "Gandhinagar Mouse", "location_ids": [loc_gan_id]},
        headers=auth_headers["admin"]
    )
    assert res_c.status_code == 201
    item_c_id = res_c.json()["id"]

    # Add adjustment to Item C so it has history
    client.post(f"/items/{item_c_id}/adjustments", json={"quantity": 10, "direction": "add"}, headers=auth_headers["admin"])

    # Manager covers Ahmedabad ONLY:
    # Item A (everywhere): Visible to Manager
    assert client.get(f"/items/{item_a_id}", headers=auth_headers["manager"]).status_code == 200

    # Item B (Ahmedabad): Visible to Manager
    assert client.get(f"/items/{item_b_id}", headers=auth_headers["manager"]).status_code == 200

    # Item C (Gandhinagar): Inaccessible to Manager -> MUST return 404!
    assert client.get(f"/items/{item_c_id}", headers=auth_headers["manager"]).status_code == 404
    assert client.get(f"/items/{item_c_id}/history", headers=auth_headers["manager"]).status_code == 404

    # Item C must NOT appear in Manager's item list
    mgr_items = client.get("/items", headers=auth_headers["manager"]).json()["items"]
    mgr_item_ids = [it["id"] for it in mgr_items]
    assert item_a_id in mgr_item_ids
    assert item_b_id in mgr_item_ids
    assert item_c_id not in mgr_item_ids

    # Write coverage check:
    # Manager can write to Item B (covered by Ahmedabad write scope)
    res_adj_b = client.post(f"/items/{item_b_id}/adjustments", json={"quantity": 5, "direction": "add"}, headers=auth_headers["manager"])
    assert res_adj_b.status_code == 200

    # Manager CANNOT write to Item A (available everywhere, requires global write access) -> 403 Forbidden!
    res_adj_a = client.post(f"/items/{item_a_id}/adjustments", json={"quantity": 5, "direction": "add"}, headers=auth_headers["manager"])
    assert res_adj_a.status_code == 403

    # Manager CANNOT write to Item C (outside Ahmedabad) -> 404 Not Found (item inaccessible)
    res_adj_c = client.post(f"/items/{item_c_id}/adjustments", json={"quantity": 5, "direction": "add"}, headers=auth_headers["manager"])
    assert res_adj_c.status_code == 404

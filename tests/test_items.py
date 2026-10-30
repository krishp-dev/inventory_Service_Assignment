def test_items_crud_and_stock_readonly(client, auth_headers):
    """
    Section 3.3:
    POST /items, GET /items, GET /items/{id}, PUT /items/{id}, DELETE /items/{id}.
    stock is read-only on these routes. It changes only through adjustments.
    """
    # 1. POST /items (client attempts stock=100, but stock is read-only)
    create_res = client.post(
        "/items",
        json={
            "name": "Standard Laptop Bag",
            "stock": 100,
            "allow_negative_stock": False,
            "location_ids": [],
            "attributes": {"color": "black", "size": "15-inch"}
        },
        headers=auth_headers["admin"]
    )
    assert create_res.status_code == 201
    item = create_res.json()
    item_id = item["id"]
    assert item["name"] == "Standard Laptop Bag"
    assert item["stock"] == 0  # stock remains 0

    # 2. GET /items/{id}
    get_res = client.get(f"/items/{item_id}", headers=auth_headers["admin"])
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Standard Laptop Bag"

    # 3. PUT /items/{id} (attempting to alter stock directly)
    put_res = client.put(
        f"/items/{item_id}",
        json={
            "name": "Deluxe Laptop Bag",
            "stock": 999
        },
        headers=auth_headers["admin"]
    )
    assert put_res.status_code == 200
    assert put_res.json()["name"] == "Deluxe Laptop Bag"
    assert put_res.json()["stock"] == 0  # stock still unchanged

    # 4. DELETE /items/{id}
    del_res = client.delete(f"/items/{item_id}", headers=auth_headers["admin"])
    assert del_res.status_code == 204

    # Subsequent GET returns 404
    assert client.get(f"/items/{item_id}", headers=auth_headers["admin"]).status_code == 404


def test_items_pagination(client, auth_headers):
    """
    Section 3.3:
    GET /items is paginated with limit and offset, and returns items and total.
    """
    for i in range(5):
        client.post(
            "/items",
            json={"name": f"Paging Product {i}"},
            headers=auth_headers["admin"]
        )

    res1 = client.get("/items?limit=2&offset=0", headers=auth_headers["admin"])
    assert res1.status_code == 200
    d1 = res1.json()
    assert len(d1["items"]) == 2
    assert d1["total"] >= 5

    res2 = client.get("/items?limit=2&offset=2", headers=auth_headers["admin"])
    assert res2.status_code == 200
    d2 = res2.json()
    assert len(d2["items"]) == 2

    ids1 = {it["id"] for it in d1["items"]}
    ids2 = {it["id"] for it in d2["items"]}
    assert ids1.isdisjoint(ids2)

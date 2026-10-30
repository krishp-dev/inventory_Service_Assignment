def test_organization_isolation_items(client, auth_headers):
    """
    Section 3.1 & Master Prompt:
    A user never sees or changes another organization's data, through any route, filter or id.
    Another organization's record returns the same 404 as a record that does not exist.
    """
    # 1. ABC Retail admin creates an item
    res_create = client.post(
        "/items",
        json={"name": "ABC Confidential Product", "attributes": {"color": "blue"}},
        headers=auth_headers["admin"]
    )
    assert res_create.status_code == 201
    item_id = res_create.json()["id"]

    # 2. XYZ Corp user queries the item by ID -> MUST return 404
    get_res = client.get(f"/items/{item_id}", headers=auth_headers["org2"])
    assert get_res.status_code == 404
    assert get_res.json()["detail"] == "Item not found"

    # 3. XYZ Corp user tries PUT -> MUST return 404
    put_res = client.put(
        f"/items/{item_id}",
        json={"name": "Hacked Title"},
        headers=auth_headers["org2"]
    )
    assert put_res.status_code == 404

    # 4. XYZ Corp user tries DELETE -> MUST return 404
    del_res = client.delete(f"/items/{item_id}", headers=auth_headers["org2"])
    assert del_res.status_code == 404

    # 5. XYZ Corp user tries stock adjustment -> MUST return 404
    adj_res = client.post(
        f"/items/{item_id}/adjustments",
        json={"quantity": 10, "direction": "add"},
        headers=auth_headers["org2"]
    )
    assert adj_res.status_code == 404

    # 6. XYZ Corp user tries history lookup -> MUST return 404
    hist_res = client.get(f"/items/{item_id}/history", headers=auth_headers["org2"])
    assert hist_res.status_code == 404

    # 7. XYZ Corp user lists items -> ABC Retail's item must NOT appear
    list_res = client.get("/items", headers=auth_headers["org2"])
    assert list_res.status_code == 200
    listed_ids = [it["id"] for it in list_res.json()["items"]]
    assert item_id not in listed_ids

    # 8. XYZ Corp attempts bulk import referencing ABC item -> 422 with row error
    imp_res = client.post(
        "/stock/import",
        json=[{"item_id": item_id, "quantity": 5, "direction": "add"}],
        headers=auth_headers["org2"]
    )
    assert imp_res.status_code == 422
    errors = imp_res.json()["errors"]
    assert any(e["item_id"] == item_id for e in errors)

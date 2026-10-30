def test_attributes_managed_and_unmanaged_keys(client, auth_headers):
    """
    Section 3.5:
    - attributes is a JSON object. Other systems write keys into it.
    - This API manages only color, size and weight_grams.
    - A PUT of an item exactly as GET returned it changes nothing in the database.
    - A PUT that changes color changes only color. Every other key stays as stored,
      including keys this API does not manage.
    - Stored {"color": "red", "legacy_code": "A-17"}, a PUT with color set to blue,
      stored afterwards {"color": "blue", "legacy_code": "A-17"}.
    """
    # 1. Create item with managed and unmanaged keys
    initial_attrs = {
        "color": "red",
        "size": "M",
        "weight_grams": 500,
        "legacy_code": "A-17",
        "warehouse_bin": "BIN-44B"
    }
    create_res = client.post(
        "/items",
        json={"name": "Attributed Shirt", "attributes": initial_attrs},
        headers=auth_headers["admin"]
    )
    assert create_res.status_code == 201
    item = create_res.json()
    item_id = item["id"]

    # 2. GET the item
    get_res = client.get(f"/items/{item_id}", headers=auth_headers["admin"])
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["attributes"]["color"] == "red"
    assert retrieved["attributes"]["legacy_code"] == "A-17"

    # 3. PUT of an item exactly as GET returned it produces identical stored state
    put_identical = client.put(
        f"/items/{item_id}",
        json={
            "name": retrieved["name"],
            "location_ids": retrieved["location_ids"],
            "allow_negative_stock": retrieved["allow_negative_stock"],
            "attributes": retrieved["attributes"]
        },
        headers=auth_headers["admin"]
    )
    assert put_identical.status_code == 200
    assert put_identical.json()["attributes"] == retrieved["attributes"]

    # 4. PUT with color set to blue changes ONLY color; legacy_code and others stay stored!
    put_color = client.put(
        f"/items/{item_id}",
        json={"attributes": {"color": "blue"}},
        headers=auth_headers["admin"]
    )
    assert put_color.status_code == 200
    updated_attrs = put_color.json()["attributes"]
    assert updated_attrs["color"] == "blue"
    assert updated_attrs["legacy_code"] == "A-17"
    assert updated_attrs["warehouse_bin"] == "BIN-44B"
    assert updated_attrs["size"] == "M"
    assert updated_attrs["weight_grams"] == 500

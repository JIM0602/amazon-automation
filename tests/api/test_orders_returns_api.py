from fastapi.testclient import TestClient


def test_orders_list_supports_time_range_filter(client: TestClient, boss_headers: dict) -> None:
    full_response = client.get(
        "/api/orders",
        params={"page": 1, "page_size": 50},
        headers=boss_headers,
    )
    filtered_response = client.get(
        "/api/orders",
        params={"time_range": "site_today", "page": 1, "page_size": 50},
        headers=boss_headers,
    )
    assert full_response.status_code == 200
    assert filtered_response.status_code == 200

    full_data = full_response.json()
    filtered_data = filtered_response.json()
    assert "items" in filtered_data
    assert "summary_row" in filtered_data
    assert filtered_data["total_count"] < full_data["total_count"]



def test_orders_list_flattens_frontend_fields(client: TestClient, boss_headers: dict) -> None:
    response = client.get(
        "/api/orders",
        params={"page": 1, "page_size": 20},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    first_item = data["items"][0]
    assert "image_url" in first_item
    assert "asin" in first_item
    assert "msku" in first_item
    assert "product_name" in first_item
    assert "sku" in first_item
    assert "refund_quantity" in first_item
    assert "profit_rate" in first_item
    assert "product_info" not in first_item
    assert "product_name_sku" not in first_item
    assert "refund_qty" not in first_item
    assert "order_profit_rate" not in first_item



def test_order_detail_returns_sections(client: TestClient, boss_headers: dict) -> None:
    listing = client.get("/api/orders", headers=boss_headers)
    order_id = listing.json()["items"][0]["order_id"]
    response = client.get(f"/api/orders/{order_id}", headers=boss_headers)
    assert response.status_code == 200
    detail = response.json()
    assert "basic_info" in detail
    assert "shipping_info" in detail
    assert "products" in detail
    assert "fee_details" in detail



def test_returns_list_supports_time_reason_status_filters(client: TestClient, boss_headers: dict) -> None:
    response = client.get(
        "/api/returns",
        params={"time_range": "this_month", "reason": "DEFECTIVE", "status": "Received", "page": 1, "page_size": 50},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "summary_row" in data
    if data["items"]:
        first_item = data["items"][0]
        assert first_item["return_reason"] == "DEFECTIVE"
        assert first_item["status"] == "Received"
        assert "after_sale_tags" in first_item
        assert "store" in first_item
        assert "site" in first_item
        assert "product_title" in first_item
        assert "return_quantity" in first_item
        assert "inventory_property" in first_item
        assert "buyer_notes" in first_item
        assert "after_sale_label" not in first_item
        assert "store_site" not in first_item
        assert "product_info" not in first_item
        assert "return_qty" not in first_item
        assert "inventory_attribute" not in first_item
        assert "return_status" not in first_item
        assert "buyer_remarks" not in first_item
        assert "remarks" not in first_item



def test_orders_and_returns_items_are_flattened(client: TestClient, boss_headers: dict) -> None:
    orders_response = client.get("/api/orders", params={"page": 1, "page_size": 1}, headers=boss_headers)
    returns_response = client.get("/api/returns", params={"page": 1, "page_size": 1}, headers=boss_headers)
    assert orders_response.status_code == 200
    assert returns_response.status_code == 200

    order_item = orders_response.json()["items"][0]
    return_item = returns_response.json()["items"][0]

    assert {"image_url", "asin", "msku"}.issubset(order_item.keys())
    assert {"image_url", "asin", "msku"}.issubset(return_item.keys())
    assert "product_info" not in order_item
    assert "product_info" not in return_item

from fastapi.testclient import TestClient


def test_dashboard_metrics_returns_expected_cards(client: TestClient, boss_headers: dict) -> None:
    response = client.get("/api/dashboard/metrics", params={"time_range": "site_today"}, headers=boss_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_sales" in data
    assert "tacos" in data
    assert "acos" in data


def test_dashboard_sku_ranking_supports_full_time_range(client: TestClient, boss_headers: dict) -> None:
    named_range_response = client.get(
        "/api/dashboard/sku_ranking",
        params={"time_range": "this_month", "page": 1, "page_size": 10},
        headers=boss_headers,
    )
    assert named_range_response.status_code == 200
    named_range_data = named_range_response.json()
    assert "items" in named_range_data
    assert "summary_row" in named_range_data

    custom_range_response = client.get(
        "/api/dashboard/sku_ranking",
        params={
            "time_range": "custom",
            "start_date": "2026-04-01",
            "end_date": "2026-04-21",
            "page": 1,
            "page_size": 10,
        },
        headers=boss_headers,
    )
    assert custom_range_response.status_code == 200
    custom_range_data = custom_range_response.json()
    assert "items" in custom_range_data
    assert "summary_row" in custom_range_data
    assert len(custom_range_data["items"]) <= 10
    assert custom_range_data["summary_row"]["sku"] == "TOTAL"


def test_dashboard_sku_ranking_rejects_incomplete_custom_range(client: TestClient, boss_headers: dict) -> None:
    response = client.get(
        "/api/dashboard/sku_ranking",
        params={"time_range": "custom", "start_date": "2026-04-01"},
        headers=boss_headers,
    )
    assert response.status_code == 422


def test_dashboard_metrics_exposes_ratio_fields(client: TestClient, boss_headers: dict) -> None:
    response = client.get("/api/dashboard/metrics", headers=boss_headers)
    data = response.json()
    assert {"tacos", "acos"}.issubset(data.keys())
    assert "value" in data["tacos"]
    assert "change_percentage" in data["acos"]

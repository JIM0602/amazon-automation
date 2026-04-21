from fastapi.testclient import TestClient


def test_ads_dashboard_metrics_returns_expected_fields(client: TestClient, boss_headers: dict) -> None:
    response = client.get("/api/ads/dashboard/metrics", params={"time_range": "site_today"}, headers=boss_headers)
    assert response.status_code == 200
    data = response.json()
    assert "ad_spend" in data
    assert "acos" in data


def test_ads_campaign_ranking_supports_this_year(client: TestClient, boss_headers: dict) -> None:
    response = client.get(
        "/api/ads/dashboard/campaign_ranking",
        params={"time_range": "this_year", "page": 1, "page_size": 10},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "summary_row" in data
    assert len(data["items"]) <= 10


def test_ads_campaign_ranking_supports_custom_range(client: TestClient, boss_headers: dict) -> None:
    response = client.get(
        "/api/ads/dashboard/campaign_ranking",
        params={
            "time_range": "custom",
            "start_date": "2026-04-01",
            "end_date": "2026-04-21",
            "page": 1,
            "page_size": 10,
        },
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "summary_row" in data


def test_ads_campaign_ranking_rejects_incomplete_custom_range(client: TestClient, boss_headers: dict) -> None:
    response = client.get(
        "/api/ads/dashboard/campaign_ranking",
        params={"time_range": "custom", "start_date": "2026-04-01"},
        headers=boss_headers,
    )
    assert response.status_code == 422


def test_ads_portfolio_tree_returns_items_wrapper(client: TestClient, boss_headers: dict) -> None:
    response = client.get("/api/ads/portfolio_tree", headers=boss_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)



def test_ads_campaign_ranking_items_include_tacos(client: TestClient, boss_headers: dict) -> None:
    response = client.get(
        "/api/ads/dashboard/campaign_ranking",
        params={"time_range": "site_today", "page": 1, "page_size": 10},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    first_item = data["items"][0]
    assert "name" in first_item
    assert "clicks" in first_item
    assert "ad_spend" in first_item
    assert "acos" in first_item
    assert "tacos" in first_item
    assert "campaign_name" not in first_item
    assert "ad_clicks" not in first_item
    assert data["summary_row"]["name"] == "TOTAL"

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


def test_ads_portfolios_support_portfolio_id_filter(client: TestClient, boss_headers: dict) -> None:
    tree_response = client.get("/api/ads/portfolio_tree", headers=boss_headers)
    assert tree_response.status_code == 200
    portfolio_id = tree_response.json()["items"][0]["id"]

    response = client.get(
        "/api/ads/portfolios",
        params={"portfolio_id": portfolio_id, "page": 1, "page_size": 20},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == portfolio_id


def test_ads_ad_groups_support_portfolio_id_filter(client: TestClient, boss_headers: dict) -> None:
    tree_response = client.get("/api/ads/portfolio_tree", headers=boss_headers)
    assert tree_response.status_code == 200
    portfolio_id = tree_response.json()["items"][0]["id"]

    response = client.get(
        "/api/ads/ad_groups",
        params={"portfolio_id": portfolio_id, "page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert all(item["portfolio_id"] == portfolio_id for item in data["items"])


def test_ads_campaigns_support_service_status_filter(client: TestClient, boss_headers: dict) -> None:
    baseline = client.get(
        "/api/ads/campaigns",
        params={"page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert baseline.status_code == 200
    baseline_items = baseline.json()["items"]
    service_status = next(item["service_status"] for item in baseline_items if item["service_status"] != "Delivering")

    response = client.get(
        "/api/ads/campaigns",
        params={"service_status": service_status, "page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert all(item["service_status"] == service_status for item in data["items"])


def test_ads_targeting_support_keyword_filter(client: TestClient, boss_headers: dict) -> None:
    baseline = client.get(
        "/api/ads/targeting",
        params={"page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert baseline.status_code == 200
    keyword = baseline.json()["items"][0]["keyword"].split()[0]

    response = client.get(
        "/api/ads/targeting",
        params={"keyword": keyword, "page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert all(keyword.lower() in item["keyword"].lower() for item in data["items"])


def test_ads_ad_products_support_ad_type_filter(client: TestClient, boss_headers: dict) -> None:
    baseline = client.get(
        "/api/ads/ad_products",
        params={"page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert baseline.status_code == 200
    ad_type = next(item["ad_type"] for item in baseline.json()["items"] if item["ad_type"] != "SP")

    response = client.get(
        "/api/ads/ad_products",
        params={"ad_type": ad_type, "page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert all(item["ad_type"] == ad_type for item in data["items"])


def test_ads_search_terms_support_keyword_filter(client: TestClient, boss_headers: dict) -> None:
    baseline = client.get(
        "/api/ads/search_terms",
        params={"page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert baseline.status_code == 200
    keyword = baseline.json()["items"][0]["search_term"].split()[0]

    response = client.get(
        "/api/ads/search_terms",
        params={"keyword": keyword, "page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert all(keyword.lower() in item["search_term"].lower() for item in data["items"])


def test_ads_negative_targeting_support_keyword_filter(client: TestClient, boss_headers: dict) -> None:
    baseline = client.get(
        "/api/ads/negative_targeting",
        params={"page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert baseline.status_code == 200
    keyword = baseline.json()["items"][0]["keyword"].split()[0]

    response = client.get(
        "/api/ads/negative_targeting",
        params={"keyword": keyword, "page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert all(keyword.lower() in item["keyword"].lower() for item in data["items"])


def test_ads_logs_support_portfolio_id_filter(client: TestClient, boss_headers: dict) -> None:
    tree_response = client.get("/api/ads/portfolio_tree", headers=boss_headers)
    assert tree_response.status_code == 200
    first_portfolio = tree_response.json()["items"][0]
    portfolio_id = first_portfolio["id"]
    portfolio_name = first_portfolio["name"]

    response = client.get(
        "/api/ads/logs",
        params={"portfolio_id": portfolio_id, "page": 1, "page_size": 100},
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert all(item["portfolio_name"] == portfolio_name for item in data["items"])


def test_ads_ad_group_detail_returns_object_payload(client: TestClient, boss_headers: dict) -> None:
    ad_groups_response = client.get(
        "/api/ads/ad_groups",
        params={"page": 1, "page_size": 1},
        headers=boss_headers,
    )
    assert ad_groups_response.status_code == 200
    ad_group = ad_groups_response.json()["items"][0]

    response = client.get(f"/api/ads/ad_groups/{ad_group['id']}", headers=boss_headers)
    assert response.status_code == 200
    data = response.json()
    assert "ad_group" in data
    assert data["ad_group"]["id"] == ad_group["id"]
    assert data["ad_group"]["campaign_name"] == ad_group["campaign_name"]


def test_ads_ad_group_drill_endpoints_return_paginated_items(client: TestClient, boss_headers: dict) -> None:
    ad_groups_response = client.get(
        "/api/ads/ad_groups",
        params={"page": 1, "page_size": 1},
        headers=boss_headers,
    )
    assert ad_groups_response.status_code == 200
    ad_group = ad_groups_response.json()["items"][0]

    for endpoint in ["ad_products", "targeting", "search_terms", "negative_targeting", "logs"]:
        response = client.get(
            f"/api/ads/ad_groups/{ad_group['id']}/{endpoint}",
            params={"page": 1, "page_size": 20},
            headers=boss_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_count" in data
        assert isinstance(data["items"], list)
        assert data["total_count"] >= len(data["items"])
        if data["items"]:
            assert all(item.get("id") for item in data["items"])
            if endpoint == "ad_products":
                assert all(item["group_id"] == ad_group["id"] for item in data["items"])
            elif endpoint == "targeting":
                assert all(item["group_id"] == ad_group["id"] for item in data["items"])
            elif endpoint == "negative_targeting":
                assert all(item["group_id"] == ad_group["id"] for item in data["items"])
            elif endpoint == "logs":
                assert all(item["group_name"] == ad_group["group_name"] for item in data["items"])
            elif endpoint == "search_terms":
                assert all("search_term" in item for item in data["items"])
                assert all("targeting" in item for item in data["items"])
                assert data["total_count"] > 0
                assert data["summary_row"] is None
                continue
        assert data["summary_row"] is None



def test_ads_action_gateway_returns_unified_mock_response(client: TestClient, boss_headers: dict) -> None:
    response = client.post(
        "/api/ads/actions",
        json={
            "action_key": "edit_budget",
            "target_type": "campaign",
            "target_ids": ["campaign_001"],
            "payload": {"budgetMode": "daily", "budgetValue": "120"},
        },
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"
    assert data["action_key"] == "edit_budget"
    assert data["target_type"] == "campaign"
    assert data["target_ids"] == ["campaign_001"]
    assert data["level"] == "L1"
    assert data["committed"] is True
    assert data["is_real_write"] is False
    assert data["should_reload"] is True
    assert data["message"]
    assert data["payload"]["budgetMode"] == "daily"



def test_ads_action_gateway_accepts_negative_keyword_action(client: TestClient, boss_headers: dict) -> None:
    response = client.post(
        "/api/ads/actions",
        json={
            "action_key": "add_negative_keyword",
            "target_type": "negative_targeting",
            "target_ids": ["targeting_001"],
            "payload": {"keywordText": "cheap toys", "matchType": "negative_phrase"},
        },
        headers=boss_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"
    assert data["level"] == "L1"
    assert data["committed"] is True
    assert data["is_real_write"] is False
    assert data["should_reload"] is True
    assert data["payload"]["matchType"] == "negative_phrase"



def test_ads_action_gateway_rejects_unknown_action(client: TestClient, boss_headers: dict) -> None:
    response = client.post(
        "/api/ads/actions",
        json={
            "action_key": "unknown_action",
            "target_type": "campaign",
            "target_ids": ["campaign_001"],
            "payload": {},
        },
        headers=boss_headers,
    )
    assert response.status_code == 400
    assert "Unsupported action" in response.json()["detail"]




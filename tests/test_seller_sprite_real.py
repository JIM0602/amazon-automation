"""Seller Sprite 真实客户端测试。"""

# pyright: reportMissingTypeArgument=false, reportGeneralTypeIssues=false, reportArgumentType=false, reportAbstractUsage=false, reportMissingImports=false

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clear_cache_and_env():
    from src.seller_sprite.client import clear_cache

    clear_cache()
    with patch.dict(
        "os.environ",
        {"SELLER_SPRITE_USE_MOCK": "false", "SELLER_SPRITE_API_KEY": "test-secret"},
        clear=False,
    ):
        yield
    clear_cache()


@pytest.fixture(autouse=True)
def disable_seller_sprite_rate_limit():
    from src.seller_sprite import client as ss_client

    class _DummyLimiter:
        def acquire_or_raise(self, **kwargs):
            return None

    original = ss_client.get_rate_limiter
    ss_client.get_rate_limiter = lambda: _DummyLimiter()
    yield
    ss_client.get_rate_limiter = original


def _response(payload: dict, status_code: int = 200):
    return SimpleNamespace(status_code=status_code, json=lambda: payload, text=str(payload))


def _client_mock(response):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.request.return_value = response
    return client


def test_get_client_returns_real_client():
    from src.seller_sprite.client import RealSellerSpriteClient, get_client

    client = get_client()
    assert isinstance(client, RealSellerSpriteClient)


def test_search_keyword_success_and_cache():
    from src.seller_sprite.client import RealSellerSpriteClient

    payload = {
        "code": "OK",
        "message": "成功",
        "data": {
            "items": [
                {
                    "keywords": "dog leash",
                    "searches": 45000,
                    "purchaseRate": 0.72,
                    "relationAsinList": [{"asin": "B08AAA111"}, {"asin": "B08BBB222"}],
                    "avgPrice": 15.99,
                    "araClickRate": 0.68,
                }
            ]
        },
    }

    with patch("httpx.Client", return_value=_client_mock(_response(payload))) as mock_http:
        client = RealSellerSpriteClient()
        result1 = client.search_keyword("dog leash")
        result2 = client.search_keyword("dog leash")

    assert result1 == result2
    assert result1["keyword"] == "dog leash"
    assert result1["search_volume"] == 45000
    assert result1["top_asins"] == ["B08AAA111", "B08BBB222"]
    assert mock_http.return_value.request.call_count == 1


def test_get_asin_data_success():
    from src.seller_sprite.client import RealSellerSpriteClient

    payload = {
        "code": "OK",
        "message": "成功",
        "data": {
            "asin": "B08TEST123",
            "title": "Test Product",
            "avgRating": 4.6,
            "ratings": 186,
            "currentPrice": 29.99,
            "bsrRank": 1523,
            "predictedSales": 320,
            "categoryName": "Pet Beds",
            "keywords": ["pet bed", {"keyword": "dog bed"}],
        },
    }

    with patch("httpx.Client", return_value=_client_mock(_response(payload))):
        client = RealSellerSpriteClient()
        result = client.get_asin_data("B08TEST123")

    assert result == {
        "asin": "B08TEST123",
        "title": "Test Product",
        "rating": 4.6,
        "review_count": 186,
        "price": 29.99,
        "bsr_rank": 1523,
        "monthly_sales": 320,
        "category": "Pet Beds",
        "keywords": ["pet bed", "dog bed"],
    }


def test_get_category_data_success():
    from src.seller_sprite.client import RealSellerSpriteClient

    payload = {
        "code": "OK",
        "message": "成功",
        "data": {
            "category": "pet supplies",
            "marketSizeUsd": 12500000000.0,
            "topSellers": [
                {"sellerName": "KONG", "marketShare": 0.08, "asinCount": 156},
                {"sellerName": "Petmate", "marketShare": 0.06, "asinCount": 243},
            ],
            "priceDistribution": {"under_10": 0.2, "10_to_25": 0.3},
            "avgReviewCount": 342,
            "growthRate": 0.12,
        },
    }

    with patch("httpx.Client", return_value=_client_mock(_response(payload))):
        client = RealSellerSpriteClient()
        result = client.get_category_data("pet supplies")

    assert result["category"] == "pet supplies"
    assert result["market_size_usd"] == 12500000000.0
    assert result["top_sellers"][0]["seller_name"] == "KONG"
    assert result["avg_review_count"] == 342
    assert result["growth_rate"] == 0.12


def test_reverse_lookup_success():
    from src.seller_sprite.client import RealSellerSpriteClient

    payload = {
        "code": "OK",
        "message": "成功",
        "data": {
            "items": [
                {"keyword": "dog leash", "searchVolume": 45000, "rank": 2},
                {"keyword": "nylon dog leash", "searches": 12000, "rank": 1},
            ]
        },
    }

    with patch("httpx.Client", return_value=_client_mock(_response(payload))):
        client = RealSellerSpriteClient()
        result = client.reverse_lookup("B08TEST123")

    assert result["asin"] == "B08TEST123"
    assert result["keywords"] == [
        {"keyword": "dog leash", "search_volume": 45000, "rank": 2},
        {"keyword": "nylon dog leash", "search_volume": 12000, "rank": 1},
    ]


@pytest.mark.parametrize(
    "payload,exc_type,message_part",
    [
        ({"code": "ERROR_SECRET_KEY", "message": "invalid"}, Exception, "API error: ERROR_SECRET_KEY - invalid"),
        ({"code": "ERROR_VISIT_MAX", "message": "rate limited"}, Exception, "API error: ERROR_VISIT_MAX - rate limited"),
    ],
)
def test_error_handling(payload, exc_type, message_part):
    from src.seller_sprite.client import RealSellerSpriteClient, SellerSpriteApiError, SellerSpriteRateLimitError

    with patch("httpx.Client", return_value=_client_mock(_response(payload))):
        client = RealSellerSpriteClient()
        if payload["code"] == "ERROR_VISIT_MAX":
            with pytest.raises(SellerSpriteRateLimitError):
                client.search_keyword("dog leash")
        else:
            with pytest.raises(SellerSpriteApiError, match=message_part):
                client.search_keyword("dog leash")


def test_http_4xx_raises_api_error():
    from src.seller_sprite.client import RealSellerSpriteClient, SellerSpriteApiError

    with patch("httpx.Client", return_value=_client_mock(_response({"detail": "bad"}, status_code=401))):
        client = RealSellerSpriteClient()
        with pytest.raises(SellerSpriteApiError, match="HTTP error: 401"):
            client.search_keyword("dog leash")


def test_missing_optional_fields_degrade_gracefully():
    from src.seller_sprite.client import RealSellerSpriteClient

    payload = {"code": "OK", "message": "成功", "data": {"items": [{}]}}
    with patch("httpx.Client", return_value=_client_mock(_response(payload))):
        client = RealSellerSpriteClient()
        result = client.search_keyword("unknown")

    assert result["keyword"] == "unknown"
    assert result["search_volume"] == 0
    assert result["top_asins"] == []
    assert len(result["trend"]) == 12

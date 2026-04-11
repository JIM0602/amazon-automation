from __future__ import annotations

from datetime import date, timedelta
from random import Random


_rng = Random(42)


def get_mock_products() -> list[dict]:
    return [
        {
            "asin": "B0PUDI001",
            "title": "PUDIWIND 宠物记忆棉睡垫",
            "price": 29.99,
            "bsr_rank": 1523,
            "category": "Pet Beds",
            "review_count": 186,
            "rating": 4.6,
        },
        {
            "asin": "B0PUDI002",
            "title": "PUDIWIND 自动循环宠物饮水机",
            "price": 39.99,
            "bsr_rank": 884,
            "category": "Pet Supplies",
            "review_count": 243,
            "rating": 4.7,
        },
        {
            "asin": "B0PUDI003",
            "title": "PUDIWIND 耐咬宠物互动玩具套装",
            "price": 18.99,
            "bsr_rank": 2310,
            "category": "Pet Toys",
            "review_count": 97,
            "rating": 4.5,
        },
    ]


def get_mock_orders(days: int = 30) -> list[dict]:
    products = get_mock_products()
    orders: list[dict] = []
    total_days = max(days, 30)
    for idx in range(total_days):
        product = products[idx % len(products)]
        orders.append(
            {
                "order_id": f"ORDER-{idx + 1:05d}",
                "asin": product["asin"],
                "quantity": (idx % 3) + 1,
                "price": product["price"],
                "order_date": str(date.today() - timedelta(days=idx)),
                "status": "Shipped" if idx % 4 != 0 else "Delivered",
            }
        )
    return orders


def get_mock_advertising() -> list[dict]:
    return [
        {
            "campaign_id": "CAMP-001",
            "name": "PUDIWIND 宠物床-品牌词广告",
            "budget": 25.0,
            "spend": 18.4,
            "impressions": 12450,
            "clicks": 286,
            "acos": 21.3,
        },
        {
            "campaign_id": "CAMP-002",
            "name": "PUDIWIND 饮水机-商品投放",
            "budget": 35.0,
            "spend": 28.7,
            "impressions": 17890,
            "clicks": 349,
            "acos": 24.1,
        },
        {
            "campaign_id": "CAMP-003",
            "name": "PUDIWIND 玩具-自动投放",
            "budget": 20.0,
            "spend": 12.2,
            "impressions": 9800,
            "clicks": 201,
            "acos": 19.8,
        },
        {
            "campaign_id": "CAMP-004",
            "name": "PUDIWIND 宠物碗-关键词广告",
            "budget": 18.0,
            "spend": 14.1,
            "impressions": 7420,
            "clicks": 167,
            "acos": 23.5,
        },
        {
            "campaign_id": "CAMP-005",
            "name": "PUDIWIND 清洁用品-再营销广告",
            "budget": 15.0,
            "spend": 9.6,
            "impressions": 6510,
            "clicks": 132,
            "acos": 17.2,
        },
    ]


def get_mock_inventory() -> list[dict]:
    products = get_mock_products()
    return [
        {
            "sku": "PUDIWIND-BED-001",
            "asin": products[0]["asin"],
            "quantity": 120,
            "reserved": 18,
            "inbound": 40,
            "fulfillable": 102,
        },
        {
            "sku": "PUDIWIND-WTR-001",
            "asin": products[1]["asin"],
            "quantity": 86,
            "reserved": 12,
            "inbound": 30,
            "fulfillable": 74,
        },
        {
            "sku": "PUDIWIND-TOY-001",
            "asin": products[2]["asin"],
            "quantity": 150,
            "reserved": 24,
            "inbound": 50,
            "fulfillable": 126,
        },
    ]


def get_mock_response(endpoint: str, params: dict = None) -> dict:
    params = params or {}
    if endpoint == "products":
        data = get_mock_products()
    elif endpoint == "orders":
        data = get_mock_orders(days=params.get("days", 30))
    elif endpoint == "advertising":
        data = get_mock_advertising()
    elif endpoint == "inventory":
        data = get_mock_inventory()
    else:
        raise ValueError(f"Unsupported endpoint: {endpoint}")
    return {"code": 0, "data": data, "endpoint": endpoint}

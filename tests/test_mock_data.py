import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from amazon_api.mock import (  # noqa: E402
    get_mock_advertising,
    get_mock_inventory,
    get_mock_orders,
    get_mock_products,
    get_mock_response,
)


def test_mock_products_count_and_fields():
    products = get_mock_products()
    assert len(products) >= 3
    for item in products:
        assert {"asin", "title", "price", "bsr_rank", "category", "review_count", "rating"} <= set(item)


def test_mock_orders_count_and_fields():
    orders = get_mock_orders()
    assert len(orders) >= 30
    for item in orders:
        assert {"order_id", "asin", "quantity", "price", "order_date", "status"} <= set(item)


def test_mock_advertising_count_and_fields():
    ads = get_mock_advertising()
    assert len(ads) >= 5
    for item in ads:
        assert {"campaign_id", "name", "budget", "spend", "impressions", "clicks", "acos"} <= set(item)


def test_mock_inventory_count_and_fields():
    inventory = get_mock_inventory()
    assert len(inventory) >= 3
    for item in inventory:
        assert {"sku", "asin", "quantity", "reserved", "inbound", "fulfillable"} <= set(item)


def test_get_mock_response_routes_correctly():
    assert get_mock_response("products")["endpoint"] == "products"
    assert len(get_mock_response("orders", {"days": 30})["data"]) >= 30
    assert len(get_mock_response("advertising")["data"]) >= 5
    assert len(get_mock_response("inventory")["data"]) >= 3


def test_mock_json_files_match_basic_expectations():
    products = json.loads((ROOT / "data" / "mock" / "products.json").read_text(encoding="utf-8"))
    orders = json.loads((ROOT / "data" / "mock" / "orders.json").read_text(encoding="utf-8"))
    assert len(products) >= 3
    assert len(orders) >= 30

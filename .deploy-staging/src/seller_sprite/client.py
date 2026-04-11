"""卖家精灵 (Seller Sprite) 客户端模块.

架构:
    SellerSpriteBase      — ABC，定义4个数据采集方法
    MockSellerSpriteClient — Mock实现，返回宠物用品类目模拟数据
    get_client()          — 工厂函数，通过 SELLER_SPRITE_USE_MOCK 控制实例

功能特性:
    - 缓存层：模块级 dict，键 (method_name, args_tuple)，值 (result, timestamp)
      相同查询24小时内返回缓存（loguru 日志显示 "cache hit"）
    - 错误重试：指数退避 time.sleep(2**attempt)，最多3次
      SELLER_SPRITE_MOCK_ERROR=true 时始终抛出异常
    - 所有操作写入 loguru 日志
"""

# pyright: reportMissingImports=false, reportMissingTypeArgument=false, reportGeneralTypeIssues=false, reportArgumentType=false

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

try:
    from loguru import logger
except ImportError:  # pragma: no cover — 无 loguru 时降级
    import logging as _logging

    class logger:  # type: ignore[no-redef]
        @staticmethod
        def info(msg, *args, **kwargs):
            _logging.info(msg.format(*args) if args else msg)

        @staticmethod
        def warning(msg, *args, **kwargs):
            _logging.warning(msg.format(*args) if args else msg)

        @staticmethod
        def error(msg, *args, **kwargs):
            _logging.error(msg.format(*args) if args else msg)

        @staticmethod
        def debug(msg, *args, **kwargs):
            _logging.debug(msg.format(*args) if args else msg)

# 限流模块（便于测试 patch）
from src.utils.rate_limiter import get_rate_limiter, RateLimitExceeded
from src.utils.api_priority import ApiPriority
from src.config import settings


# ---------------------------------------------------------------------------
# 缓存层：模块级字典，键 (method_name, args_tuple)，值 (result, timestamp)
# ---------------------------------------------------------------------------
_CACHE: dict[tuple, tuple[Any, datetime]] = {}
_CACHE_TTL = timedelta(hours=24)


def _cache_get(key: tuple) -> Optional[Any]:
    """从缓存中获取数据，过期则删除并返回 None。"""
    if key in _CACHE:
        result, ts = _CACHE[key]
        if datetime.utcnow() - ts < _CACHE_TTL:
            logger.info("cache hit | key={}", key)
            return result
        del _CACHE[key]
    return None


def _cache_set(key: tuple, result: Any) -> None:
    """将结果写入缓存。"""
    _CACHE[key] = (result, datetime.utcnow())
    logger.debug("cache set | key={}", key)


def clear_cache() -> None:
    """清空全部缓存（测试辅助函数）。"""
    _CACHE.clear()
    logger.info("seller_sprite cache cleared")


# ---------------------------------------------------------------------------
# 错误类
# ---------------------------------------------------------------------------
class SellerSpriteError(Exception):
    """卖家精灵客户端错误基类。"""


class SellerSpriteRateLimitError(SellerSpriteError):
    """API 速率限制错误。"""


class SellerSpriteApiError(SellerSpriteError):
    """API 调用失败（含 Mock 错误注入）。"""


# ---------------------------------------------------------------------------
# 重试装饰器（指数退避，最多3次）
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3


def _with_retry(func, *args, **kwargs):
    """执行 func(*args, **kwargs)，失败时指数退避重试最多 _MAX_RETRIES 次。

    重试策略：
        - 前 N-1 次失败后 sleep(2**attempt) 再重试
        - 第 N 次（最后一次）失败后直接 raise，不 sleep
    """
    last_exc: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except SellerSpriteError as exc:
            last_exc = exc
            is_last = attempt == _MAX_RETRIES - 1
            if is_last:
                logger.error("seller_sprite call failed after {} retries", _MAX_RETRIES)
                raise
            wait = 2 ** attempt
            logger.warning(
                "seller_sprite call failed (attempt {}/{}), retrying in {}s | error={}",
                attempt + 1,
                _MAX_RETRIES,
                wait,
                exc,
            )
            time.sleep(wait)
    logger.error("seller_sprite call failed after {} retries", _MAX_RETRIES)
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------
class SellerSpriteBase(ABC):
    """卖家精灵客户端抽象基类，定义4个数据采集方法。"""

    @abstractmethod
    def search_keyword(self, keyword: str, account_id: str = "default") -> dict:
        """搜索关键词数据.

        Args:
            keyword: 搜索关键词，例如 "dog leash"

        Returns:
            dict with keys:
                keyword (str), search_volume (int), competition (float 0-1),
                trend (list[int] 12个月月度数据), top_asins (list[str]),
                avg_price (float), click_share (float)
        """

    @abstractmethod
    def get_asin_data(self, asin: str, account_id: str = "default") -> dict:
        """获取ASIN商品数据.

        Args:
            asin: Amazon ASIN编号，例如 "B08XXX"

        Returns:
            dict with keys:
                asin (str), title (str), rating (float), review_count (int),
                price (float), bsr_rank (int), monthly_sales (int),
                category (str), keywords (list[str])
        """

    @abstractmethod
    def get_category_data(self, category: str, account_id: str = "default") -> dict:
        """获取类目市场数据.

        Args:
            category: 类目名称，例如 "pet supplies"

        Returns:
            dict with keys:
                category (str), market_size_usd (float), top_sellers (list[dict]),
                price_distribution (dict), avg_review_count (int),
                growth_rate (float)
        """

    @abstractmethod
    def reverse_lookup(self, asin: str, account_id: str = "default") -> dict:
        """反查ASIN的关键词列表.

        Args:
            asin: Amazon ASIN编号

        Returns:
            dict with keys:
                asin (str), keywords (list[dict]) — 每个 dict 含
                    keyword (str), search_volume (int), rank (int)
        """


# ---------------------------------------------------------------------------
# Mock 数据层：宠物用品类目真实感数据
# ---------------------------------------------------------------------------

_MOCK_KEYWORD_DATA: dict[str, dict] = {
    "dog leash": {
        "keyword": "dog leash",
        "search_volume": 45000,
        "competition": 0.72,
        "trend": [38000, 40000, 42000, 43000, 44000, 45000, 46000, 47000, 45500, 44000, 43500, 45000],
        "top_asins": ["B08DKH4T9Q", "B07XVZW8FM", "B09L3JTPKR"],
        "avg_price": 15.99,
        "click_share": 0.68,
    },
    "cat tree": {
        "keyword": "cat tree",
        "search_volume": 32000,
        "competition": 0.65,
        "trend": [28000, 29000, 30000, 31000, 31500, 32000, 33000, 32500, 31000, 30500, 31000, 32000],
        "top_asins": ["B07CJZ6NNK", "B08Q7H5CPG", "B09RNHM8DJ"],
        "avg_price": 89.99,
        "click_share": 0.72,
    },
    "dog food": {
        "keyword": "dog food",
        "search_volume": 120000,
        "competition": 0.89,
        "trend": [115000, 116000, 118000, 119000, 120000, 121000, 122000, 120500, 119000, 118500, 119000, 120000],
        "top_asins": ["B07TKWTM4W", "B00S7DNXPM", "B0816BNCK7"],
        "avg_price": 42.99,
        "click_share": 0.55,
    },
    "pet bed": {
        "keyword": "pet bed",
        "search_volume": 28000,
        "competition": 0.61,
        "trend": [24000, 25000, 26000, 27000, 27500, 28000, 29000, 28500, 27000, 26500, 27000, 28000],
        "top_asins": ["B0PUDI001", "B08KH4T9Q2", "B07XVZ8FM1"],
        "avg_price": 34.99,
        "click_share": 0.64,
    },
}

_DEFAULT_KEYWORD_DATA = {
    "search_volume": 5000,
    "competition": 0.50,
    "trend": [4500, 4600, 4700, 4800, 4900, 5000, 5100, 5000, 4900, 4800, 4850, 5000],
    "top_asins": ["B08EXAMPLE1", "B08EXAMPLE2", "B08EXAMPLE3"],
    "avg_price": 24.99,
    "click_share": 0.60,
}

_MOCK_ASIN_DATA: dict[str, dict] = {
    "B0PUDI001": {
        "asin": "B0PUDI001",
        "title": "PUDIWIND 宠物记忆棉睡垫 - 机洗可拆卸",
        "rating": 4.6,
        "review_count": 186,
        "price": 29.99,
        "bsr_rank": 1523,
        "monthly_sales": 320,
        "category": "Pet Beds",
        "keywords": ["pet bed", "dog bed", "memory foam dog bed", "washable dog bed"],
    },
    "B0PUDI002": {
        "asin": "B0PUDI002",
        "title": "PUDIWIND 自动循环宠物饮水机 2.5L",
        "rating": 4.7,
        "review_count": 243,
        "price": 39.99,
        "bsr_rank": 884,
        "monthly_sales": 520,
        "category": "Pet Supplies",
        "keywords": ["cat water fountain", "pet fountain", "automatic cat water dispenser"],
    },
    "B08DKH4T9Q": {
        "asin": "B08DKH4T9Q",
        "title": "Heavy Duty Dog Leash - 6ft Nylon Lead",
        "rating": 4.5,
        "review_count": 8920,
        "price": 14.99,
        "bsr_rank": 234,
        "monthly_sales": 4500,
        "category": "Dog Leashes",
        "keywords": ["dog leash", "nylon dog leash", "heavy duty leash", "6ft dog leash"],
    },
}

_DEFAULT_ASIN_DATA = {
    "title": "Generic Pet Product",
    "rating": 4.2,
    "review_count": 150,
    "price": 19.99,
    "bsr_rank": 5000,
    "monthly_sales": 200,
    "category": "Pet Supplies",
    "keywords": ["pet supplies", "pet product"],
}

_MOCK_CATEGORY_DATA: dict[str, dict] = {
    "pet supplies": {
        "category": "pet supplies",
        "market_size_usd": 12_500_000_000.0,
        "top_sellers": [
            {"seller_name": "KONG Company", "market_share": 0.08, "asin_count": 156},
            {"seller_name": "Petmate", "market_share": 0.06, "asin_count": 243},
            {"seller_name": "Frisco", "market_share": 0.05, "asin_count": 387},
            {"seller_name": "AmazonBasics Pet", "market_share": 0.04, "asin_count": 98},
        ],
        "price_distribution": {
            "under_10": 0.18,
            "10_to_25": 0.32,
            "25_to_50": 0.28,
            "50_to_100": 0.15,
            "over_100": 0.07,
        },
        "avg_review_count": 342,
        "growth_rate": 0.12,
    },
    "dog leashes": {
        "category": "dog leashes",
        "market_size_usd": 450_000_000.0,
        "top_sellers": [
            {"seller_name": "Ruffwear", "market_share": 0.12, "asin_count": 45},
            {"seller_name": "EzyDog", "market_share": 0.08, "asin_count": 32},
        ],
        "price_distribution": {
            "under_10": 0.25,
            "10_to_25": 0.55,
            "25_to_50": 0.15,
            "50_to_100": 0.04,
            "over_100": 0.01,
        },
        "avg_review_count": 1250,
        "growth_rate": 0.08,
    },
}

_DEFAULT_CATEGORY_DATA = {
    "market_size_usd": 100_000_000.0,
    "top_sellers": [
        {"seller_name": "TopSeller1", "market_share": 0.10, "asin_count": 50},
    ],
    "price_distribution": {
        "under_10": 0.20,
        "10_to_25": 0.40,
        "25_to_50": 0.25,
        "50_to_100": 0.10,
        "over_100": 0.05,
    },
    "avg_review_count": 200,
    "growth_rate": 0.10,
}

_MOCK_REVERSE_LOOKUP: dict[str, list[dict]] = {
    "B0PUDI001": [
        {"keyword": "pet bed", "search_volume": 28000, "rank": 12},
        {"keyword": "dog bed", "search_volume": 56000, "rank": 23},
        {"keyword": "memory foam dog bed", "search_volume": 8500, "rank": 5},
        {"keyword": "washable dog bed", "search_volume": 12000, "rank": 8},
        {"keyword": "orthopedic dog bed", "search_volume": 18000, "rank": 31},
    ],
    "B0PUDI002": [
        {"keyword": "cat water fountain", "search_volume": 22000, "rank": 7},
        {"keyword": "pet fountain", "search_volume": 15000, "rank": 11},
        {"keyword": "automatic cat water dispenser", "search_volume": 9500, "rank": 4},
        {"keyword": "dog water fountain", "search_volume": 18000, "rank": 19},
    ],
    "B08DKH4T9Q": [
        {"keyword": "dog leash", "search_volume": 45000, "rank": 2},
        {"keyword": "nylon dog leash", "search_volume": 12000, "rank": 1},
        {"keyword": "heavy duty leash", "search_volume": 8800, "rank": 3},
        {"keyword": "6ft dog leash", "search_volume": 5500, "rank": 1},
    ],
}

_DEFAULT_REVERSE_KEYWORDS = [
    {"keyword": "pet supplies", "search_volume": 120000, "rank": 50},
    {"keyword": "pet product", "search_volume": 45000, "rank": 35},
]


# ---------------------------------------------------------------------------
# Mock 客户端实现
# ---------------------------------------------------------------------------
class MockSellerSpriteClient(SellerSpriteBase):
    """卖家精灵 Mock 客户端 — 返回宠物用品类目模拟数据.

    环境变量:
        SELLER_SPRITE_MOCK_ERROR=true — 所有调用始终抛出 SellerSpriteApiError（测试错误重试）
    """

    def _check_mock_error(self) -> None:
        """若 SELLER_SPRITE_MOCK_ERROR=true，抛出模拟错误。"""
        if os.environ.get("SELLER_SPRITE_MOCK_ERROR", "").lower() == "true":
            raise SellerSpriteApiError("Mock error injected via SELLER_SPRITE_MOCK_ERROR=true")

    def search_keyword(self, keyword: str, account_id: str = "default") -> dict:
        """返回关键词搜索数据（含缓存 & 错误注入 & 限流）。"""
        # 限流检查
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(
            api_group="seller_sprite",
            account_id=account_id,
            priority=ApiPriority.BATCH,
        )

        cache_key = ("search_keyword", keyword.lower())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        def _do():
            self._check_mock_error()
            kw_lower = keyword.lower()
            if kw_lower in _MOCK_KEYWORD_DATA:
                result = dict(_MOCK_KEYWORD_DATA[kw_lower])
            else:
                result = dict(_DEFAULT_KEYWORD_DATA)
                result["keyword"] = keyword
            logger.info("seller_sprite search_keyword | keyword={} search_volume={}", keyword, result["search_volume"])
            return result

        result = _with_retry(_do)
        _cache_set(cache_key, result)
        return result

    def get_asin_data(self, asin: str, account_id: str = "default") -> dict:
        """返回ASIN商品数据（含缓存 & 错误注入 & 限流）。"""
        # 限流检查
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(
            api_group="seller_sprite",
            account_id=account_id,
            priority=ApiPriority.BATCH,
        )

        cache_key = ("get_asin_data", asin.upper())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        def _do():
            self._check_mock_error()
            asin_upper = asin.upper()
            if asin_upper in _MOCK_ASIN_DATA:
                result = dict(_MOCK_ASIN_DATA[asin_upper])
            else:
                result = dict(_DEFAULT_ASIN_DATA)
                result["asin"] = asin
            logger.info(
                "seller_sprite get_asin_data | asin={} bsr_rank={} monthly_sales={}",
                asin,
                result["bsr_rank"],
                result["monthly_sales"],
            )
            return result

        result = _with_retry(_do)
        _cache_set(cache_key, result)
        return result

    def get_category_data(self, category: str, account_id: str = "default") -> dict:
        """返回类目市场数据（含缓存 & 错误注入 & 限流）。"""
        # 限流检查
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(
            api_group="seller_sprite",
            account_id=account_id,
            priority=ApiPriority.BATCH,
        )

        cache_key = ("get_category_data", category.lower())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        def _do():
            self._check_mock_error()
            cat_lower = category.lower()
            if cat_lower in _MOCK_CATEGORY_DATA:
                result = dict(_MOCK_CATEGORY_DATA[cat_lower])
            else:
                result = dict(_DEFAULT_CATEGORY_DATA)
                result["category"] = category
            logger.info(
                "seller_sprite get_category_data | category={} market_size_usd={}",
                category,
                result["market_size_usd"],
            )
            return result

        result = _with_retry(_do)
        _cache_set(cache_key, result)
        return result

    def reverse_lookup(self, asin: str, account_id: str = "default") -> dict:
        """反查ASIN关键词列表（含缓存 & 错误注入 & 限流）。"""
        # 限流检查
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(
            api_group="seller_sprite",
            account_id=account_id,
            priority=ApiPriority.BATCH,
        )

        cache_key = ("reverse_lookup", asin.upper())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        def _do():
            self._check_mock_error()
            asin_upper = asin.upper()
            if asin_upper in _MOCK_REVERSE_LOOKUP:
                keywords = _MOCK_REVERSE_LOOKUP[asin_upper]
            else:
                keywords = _DEFAULT_REVERSE_KEYWORDS
            result = {"asin": asin, "keywords": keywords}
            logger.info(
                "seller_sprite reverse_lookup | asin={} keyword_count={}",
                asin,
                len(keywords),
            )
            return result

        result = _with_retry(_do)
        _cache_set(cache_key, result)
        return result


# ---------------------------------------------------------------------------
# 真实客户端实现
# ---------------------------------------------------------------------------


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _first_non_empty(*values: Any, default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                return value
        else:
            text = str(value)
            if text:
                return text
    return default


def _normalize_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _extract_record(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        for key in ("items", "keywords", "rows", "results", "list", "data"):
            value = data.get(key)
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict):
                    return first
            if isinstance(value, dict) and value:
                return value
        return data
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return first
    return {}


def _extract_items(data: Any) -> list[Any]:
    if isinstance(data, dict):
        for key in ("items", "keywords", "rows", "results", "list", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return []
    if isinstance(data, list):
        return data
    return []


class RealSellerSpriteClient(SellerSpriteBase):
    """Seller Sprite MCP (Streamable HTTP) 真实客户端。

    通过 MCP 协议调用卖家精灵数据服务，而非 REST API。
    MCP 端点: https://mcp.sellersprite.com/mcp
    认证方式: secret-key 请求头
    """

    def __init__(self) -> None:
        from src.seller_sprite.mcp_client import MCPToolClient

        self.api_key = os.environ.get("SELLER_SPRITE_API_KEY") or settings.SELLER_SPRITE_API_KEY
        self.mcp_endpoint = settings.SELLER_SPRITE_MCP_ENDPOINT
        self._mcp = MCPToolClient(
            endpoint=self.mcp_endpoint,
            secret_key=self.api_key,
            timeout=120.0,
        )

    def _call_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """调用 MCP 工具并提取 data 字段。

        MCP 工具返回格式: {"code": "OK", "message": "...", "data": {...}}
        与 REST API 响应格式一致。
        """
        from src.seller_sprite.mcp_client import MCPError

        def _do_call() -> Any:
            try:
                result = self._mcp.call_tool_safe(tool_name, arguments)
            except MCPError as exc:
                raise SellerSpriteApiError(f"MCP error: {exc}") from exc
            except httpx.HTTPError as exc:
                raise SellerSpriteApiError(f"MCP HTTP error: {exc}") from exc

            # MCP 工具返回 {code, message, data} — 与 REST 一致
            if isinstance(result, dict):
                code = result.get("code")
                message = result.get("message", "")
                if code == "ERROR_VISIT_MAX":
                    raise SellerSpriteRateLimitError(f"MCP rate limit: {code} - {message}")
                if code and code != "OK":
                    raise SellerSpriteApiError(f"MCP tool error: {code} - {message}")
                return result.get("data", result)
            return result

        return _with_retry(_do_call)

    def _map_keyword_result(self, keyword: str, data: Any) -> dict:
        item = _extract_record(data)
        search_volume = _safe_int(item.get("searches") or item.get("searchVolume") or item.get("search_volume"))
        trend = _normalize_list(
            item.get("trend")
            or item.get("monthlyTrend")
            or item.get("trendList")
            or item.get("history")
        )
        if not trend:
            trend = [search_volume] * 12
        top_asins_source = _normalize_list(item.get("relationAsinList") or item.get("araAsinList") or item.get("topAsins"))
        top_asins: list[str] = []
        for entry in top_asins_source:
            if isinstance(entry, dict):
                asin_value = _first_non_empty(entry.get("asin"), entry.get("ASIN"), entry.get("id"))
            else:
                asin_value = _first_non_empty(entry)
            if asin_value:
                top_asins.append(asin_value)
        return {
            "keyword": _first_non_empty(item.get("keywords"), item.get("keyword"), keyword, default=keyword),
            "search_volume": search_volume,
            "competition": _safe_float(item.get("competition") or item.get("purchaseRate") or item.get("supplyDemandRatio")),
            "trend": [int(x) if isinstance(x, (int, float, str)) and str(x).strip() else 0 for x in trend][:12],
            "top_asins": top_asins,
            "avg_price": _safe_float(item.get("avgPrice") or item.get("avg_price") or item.get("price")),
            "click_share": _safe_float(item.get("araClickRate") or item.get("clickShare") or item.get("araShareRate")),
        }

    def _map_asin_result(self, asin: str, data: Any) -> dict:
        item = _extract_record(data)
        keywords_source = _normalize_list(item.get("keywords") or item.get("keywordList") or item.get("relatedKeywords"))
        keywords: list[str] = []
        for entry in keywords_source:
            if isinstance(entry, dict):
                keyword_value = _first_non_empty(entry.get("keyword"), entry.get("words"), entry.get("text"))
            else:
                keyword_value = _first_non_empty(entry)
            if keyword_value:
                keywords.append(keyword_value)
        return {
            "asin": _first_non_empty(item.get("asin"), asin, default=asin),
            "title": _first_non_empty(item.get("title"), item.get("name"), item.get("productTitle")),
            "rating": _safe_float(item.get("rating") or item.get("avgRating") or item.get("reviewRating")),
            "review_count": _safe_int(item.get("reviewCount") or item.get("ratings") or item.get("review_count")),
            "price": _safe_float(item.get("price") or item.get("avgPrice") or item.get("currentPrice")),
            "bsr_rank": _safe_int(item.get("bsrRank") or item.get("bsr") or item.get("rank")),
            "monthly_sales": _safe_int(item.get("monthlySales") or item.get("sales") or item.get("predictedSales")),
            "category": _first_non_empty(item.get("category"), item.get("categoryName"), item.get("nodeName")),
            "keywords": keywords,
        }

    def _map_category_result(self, category: str, data: Any) -> dict:
        item = _extract_record(data)
        top_sellers_source = _normalize_list(item.get("topSellers") or item.get("sellerList") or item.get("brandList"))
        top_sellers: list[dict[str, Any]] = []
        for entry in top_sellers_source:
            if not isinstance(entry, dict):
                continue
            top_sellers.append(
                {
                    "seller_name": _first_non_empty(entry.get("seller_name"), entry.get("sellerName"), entry.get("name"), entry.get("brandName")),
                    "market_share": _safe_float(entry.get("market_share") or entry.get("marketShare") or entry.get("ratio") or entry.get("share")),
                    "asin_count": _safe_int(entry.get("asin_count") or entry.get("asinCount") or entry.get("productCount")),
                }
            )

        price_distribution = item.get("priceDistribution") or item.get("price_distribution") or {}
        if isinstance(price_distribution, list):
            mapped_distribution: dict[str, float] = {}
            for idx, entry in enumerate(price_distribution):
                if isinstance(entry, dict):
                    key = _first_non_empty(entry.get("range"), entry.get("name"), entry.get("label"), default=f"bucket_{idx}")
                    mapped_distribution[key] = _safe_float(entry.get("ratio") or entry.get("value") or entry.get("percent"))
            price_distribution = mapped_distribution
        elif not isinstance(price_distribution, dict):
            price_distribution = {}

        return {
            "category": _first_non_empty(item.get("category"), item.get("nodeName"), item.get("name"), item.get("label"), category, default=category),
            "market_size_usd": _safe_float(item.get("marketSizeUsd") or item.get("marketSize") or item.get("marketValue") or item.get("totalValue")),
            "top_sellers": top_sellers,
            "price_distribution": price_distribution,
            "avg_review_count": _safe_int(item.get("avgReviewCount") or item.get("reviewCountAvg") or item.get("avgReviews")),
            "growth_rate": _safe_float(item.get("growthRate") or item.get("marketGrowthRate") or item.get("growth")),
        }

    def _map_reverse_lookup_result(self, asin: str, data: Any) -> dict:
        items = _extract_items(data)
        keywords: list[dict[str, Any]] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            keywords.append(
                {
                    "keyword": _first_non_empty(entry.get("keyword"), entry.get("keywords"), entry.get("text")),
                    "search_volume": _safe_int(entry.get("searchVolume") or entry.get("searches") or entry.get("volume") or entry.get("search_volume")),
                    "rank": _safe_int(entry.get("rank") or entry.get("position") or entry.get("keywordRank")),
                }
            )
        return {
            "asin": _first_non_empty(asin, default=asin),
            "keywords": keywords,
        }

    def search_keyword(self, keyword: str, account_id: str = "default") -> dict:
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(api_group="seller_sprite", account_id=account_id, priority=ApiPriority.BATCH)

        cache_key = ("search_keyword", keyword.lower())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._call_mcp_tool("keyword_research", {"marketplace": "US", "keywords": keyword})
        result = self._map_keyword_result(keyword, data)
        logger.info("seller_sprite search_keyword | keyword={} search_volume={}", keyword, result["search_volume"])
        _cache_set(cache_key, result)
        return result

    def get_asin_data(self, asin: str, account_id: str = "default") -> dict:
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(api_group="seller_sprite", account_id=account_id, priority=ApiPriority.BATCH)

        cache_key = ("get_asin_data", asin.upper())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._call_mcp_tool("asin_detail", {"marketplace": "US", "asin": asin})
        result = self._map_asin_result(asin, data)
        logger.info("seller_sprite get_asin_data | asin={} bsr_rank={} monthly_sales={}", asin, result["bsr_rank"], result["monthly_sales"])
        _cache_set(cache_key, result)
        return result

    def get_category_data(self, category: str, account_id: str = "default") -> dict:
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(api_group="seller_sprite", account_id=account_id, priority=ApiPriority.BATCH)

        cache_key = ("get_category_data", category.lower())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._call_mcp_tool("product_node", {"marketplace": "US", "keyword": category})
        result = self._map_category_result(category, data)
        logger.info("seller_sprite get_category_data | category={} market_size_usd={}", category, result["market_size_usd"])
        _cache_set(cache_key, result)
        return result

    def reverse_lookup(self, asin: str, account_id: str = "default") -> dict:
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(api_group="seller_sprite", account_id=account_id, priority=ApiPriority.BATCH)

        cache_key = ("reverse_lookup", asin.upper())
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._call_mcp_tool("traffic_keyword", {"marketplace": "US", "asin": asin})
        result = self._map_reverse_lookup_result(asin, data)
        logger.info("seller_sprite reverse_lookup | asin={} keyword_count={}", asin, len(result["keywords"]))
        _cache_set(cache_key, result)
        return result


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------
def get_client() -> SellerSpriteBase:
    """工厂函数：返回卖家精灵客户端实例.

    环境变量:
        SELLER_SPRITE_USE_MOCK=true  (默认) — 返回 MockSellerSpriteClient
        SELLER_SPRITE_USE_MOCK=false         — 返回真实客户端（阶段B实现）

    Returns:
        SellerSpriteBase 实例
    """
    # 优先读取环境变量（覆盖 settings 默认值，方便测试）
    use_mock_env = os.environ.get("SELLER_SPRITE_USE_MOCK", "").lower()
    if use_mock_env in ("true", "1", "yes"):
        use_mock = True
    elif use_mock_env in ("false", "0", "no"):
        use_mock = False
    else:
        # 回退到 pydantic settings
        try:
            from src.config import settings
            use_mock = settings.SELLER_SPRITE_USE_MOCK
        except Exception:
            use_mock = True

    if use_mock:
        logger.info("seller_sprite get_client | mode=mock")
        return MockSellerSpriteClient()

    logger.info("seller_sprite get_client | mode=real")
    return RealSellerSpriteClient()

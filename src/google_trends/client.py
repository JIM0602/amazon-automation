"""Google Trends 客户端模块 (基于 SerpApi).

架构:
    GoogleTrendsClient    — 异步客户端，通过 SerpApi 获取 Google Trends 数据
    get_trends_client()   — 工厂函数，返回配置好的客户端或 None（未启用时）

功能特性:
    - 缓存层：模块级 dict，键 (method_name, args_tuple)，值 (result, timestamp)
      相同查询 24 小时内返回缓存（loguru 日志显示 "cache hit"）
    - 速率限制：简单 datetime 跟踪，每分钟最多 10 次请求
    - 优雅降级：API 调用失败时返回空/默认结果，不抛出异常
    - HTTP 调用使用 httpx.AsyncClient
"""

# pyright: reportMissingImports=false, reportMissingTypeArgument=false

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

try:
    from loguru import logger
except ImportError:  # pragma: no cover — 无 loguru 时降级
    import logging as _logging

    logger = _logging.getLogger(__name__)  # type: ignore[assignment]

from src.google_trends.models import (
    RegionalInterest,
    RelatedQuery,
    TrendData,
    TrendPoint,
)

# ---------------------------------------------------------------------------
# SerpApi 端点
# ---------------------------------------------------------------------------
_SERPAPI_ENDPOINT = "https://serpapi.com/search.json"

# ---------------------------------------------------------------------------
# 缓存层：模块级字典，键 (method_name, args_tuple)，值 (result, timestamp)
# ---------------------------------------------------------------------------
_CACHE: dict[tuple[str, ...], tuple[Any, datetime]] = {}
_CACHE_TTL = timedelta(hours=24)


def _cache_get(key: tuple[str, ...]) -> Any | None:
    """从缓存中获取数据，过期则删除并返回 None。"""
    if key in _CACHE:
        result, ts = _CACHE[key]
        if datetime.utcnow() - ts < _CACHE_TTL:
            logger.info("google_trends cache hit | key=%s", key)
            return result
        del _CACHE[key]
    return None


def _cache_set(key: tuple[str, ...], result: Any) -> None:
    """将结果写入缓存。"""
    _CACHE[key] = (result, datetime.utcnow())
    logger.debug("google_trends cache set | key=%s", key)


def clear_cache() -> None:
    """清空全部缓存（测试辅助函数）。"""
    _CACHE.clear()
    logger.info("google_trends cache cleared")


# ---------------------------------------------------------------------------
# Google Trends 客户端
# ---------------------------------------------------------------------------
class GoogleTrendsClient:
    """通过 SerpApi 访问 Google Trends 数据的异步客户端.

    特性:
        - 所有方法均为 async，使用 httpx.AsyncClient 发起 HTTP 请求
        - 内置 24 小时缓存，避免重复请求
        - 每分钟最多 10 次请求的速率限制
        - API 失败时优雅降级，返回空结果而非抛出异常

    示例::

        client = get_trends_client()
        if client:
            data = await client.get_interest_over_time(["dog leash"])
    """

    def __init__(self, api_key: str) -> None:
        """初始化 Google Trends 客户端.

        Args:
            api_key: SerpApi 的 API 密钥。
        """
        self._api_key = api_key
        self._request_timestamps: list[datetime] = []
        self._rate_limit_max = 10
        self._rate_limit_window = timedelta(minutes=1)

    def _check_rate_limit(self) -> bool:
        """检查是否超出速率限制.

        清理过期的时间戳记录，判断当前窗口内的请求数是否在限制范围内。

        Returns:
            True 表示可以继续请求，False 表示应等待。
        """
        now = datetime.utcnow()
        cutoff = now - self._rate_limit_window
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > cutoff
        ]
        if len(self._request_timestamps) >= self._rate_limit_max:
            logger.warning(
                "google_trends rate limit reached | %d requests in last minute",
                len(self._request_timestamps),
            )
            return False
        self._request_timestamps.append(now)
        return True

    async def _request(self, params: dict[str, Any]) -> Optional[dict[str, Any]]:
        """向 SerpApi 发起 HTTP GET 请求.

        Args:
            params: 查询参数字典（不含 api_key，会自动添加）。

        Returns:
            JSON 响应字典，失败时返回 None。
        """
        if not self._check_rate_limit():
            logger.warning("google_trends request skipped due to rate limit")
            return None

        params["api_key"] = self._api_key
        params["engine"] = "google_trends"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(_SERPAPI_ENDPOINT, params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "google_trends API HTTP error | status=%d url=%s",
                exc.response.status_code,
                exc.request.url,
            )
            return None
        except httpx.RequestError as exc:
            logger.error(
                "google_trends API request error | error=%s",
                str(exc),
            )
            return None
        except Exception as exc:
            logger.error(
                "google_trends API unexpected error | error=%s",
                str(exc),
            )
            return None

    async def get_interest_over_time(
        self,
        keywords: list[str],
        geo: str = "US",
        timeframe: str = "today 12-m",
    ) -> TrendData:
        """获取关键词的搜索兴趣随时间变化数据.

        Args:
            keywords: 关键词列表（SerpApi 支持最多 5 个关键词比较）。
            geo: 地区代码，如 'US'、'GB'。
            timeframe: 时间范围，如 'today 12-m'、'today 3-m'。

        Returns:
            TrendData 对象。API 失败时返回空的 interest_over_time 列表。
        """
        joined_keywords = ",".join(keywords)
        cache_key = ("interest_over_time", joined_keywords, geo, timeframe)
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        data = await self._request({
            "q": joined_keywords,
            "geo": geo,
            "date": timeframe,
            "data_type": "TIMESERIES",
        })

        points: list[TrendPoint] = []
        if data:
            timeline_data = data.get("interest_over_time", {})
            timeline_list = timeline_data.get("timeline_data", [])
            for entry in timeline_list:
                date_str = entry.get("date", "")
                values = entry.get("values", [])
                interest = 0
                if values and isinstance(values, list):
                    raw = values[0].get("extracted_value", 0)
                    interest = int(raw) if raw is not None else 0
                points.append(TrendPoint(date=date_str, interest=interest))

        result = TrendData(
            keyword=joined_keywords,
            timeframe=timeframe,
            geo=geo,
            interest_over_time=points,
        )

        _cache_set(cache_key, result)
        logger.info(
            "google_trends get_interest_over_time | keywords=%s geo=%s points=%d",
            joined_keywords,
            geo,
            len(points),
        )
        return result

    async def get_related_queries(
        self,
        keyword: str,
        geo: str = "US",
    ) -> list[RelatedQuery]:
        """获取与关键词相关的搜索查询.

        Args:
            keyword: 目标关键词。
            geo: 地区代码。

        Returns:
            RelatedQuery 列表。API 失败时返回空列表。
        """
        cache_key = ("related_queries", keyword, geo)
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        data = await self._request({
            "q": keyword,
            "geo": geo,
            "data_type": "RELATED_QUERIES",
        })

        queries: list[RelatedQuery] = []
        if data:
            related = data.get("related_queries", {})

            # 处理 "rising" 查询
            for entry in related.get("rising", []):
                query_text = entry.get("query", "")
                value = entry.get("extracted_value", 0)
                queries.append(RelatedQuery(
                    query=query_text,
                    value=int(value) if value is not None else 0,
                    rising=True,
                ))

            # 处理 "top" 查询
            for entry in related.get("top", []):
                query_text = entry.get("query", "")
                value = entry.get("extracted_value", 0)
                queries.append(RelatedQuery(
                    query=query_text,
                    value=int(value) if value is not None else 0,
                    rising=False,
                ))

        _cache_set(cache_key, queries)
        logger.info(
            "google_trends get_related_queries | keyword=%s geo=%s count=%d",
            keyword,
            geo,
            len(queries),
        )
        return queries

    async def get_regional_interest(
        self,
        keyword: str,
    ) -> list[RegionalInterest]:
        """获取关键词在各区域的搜索兴趣分布.

        Args:
            keyword: 目标关键词。

        Returns:
            RegionalInterest 列表。API 失败时返回空列表。
        """
        cache_key = ("regional_interest", keyword)
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        data = await self._request({
            "q": keyword,
            "data_type": "GEO_MAP",
        })

        regions: list[RegionalInterest] = []
        if data:
            geo_data = data.get("interest_by_region", [])
            for entry in geo_data:
                region_name = entry.get("location", "")
                value = entry.get("extracted_value", 0)
                regions.append(RegionalInterest(
                    region=region_name,
                    interest=int(value) if value is not None else 0,
                ))

        _cache_set(cache_key, regions)
        logger.info(
            "google_trends get_regional_interest | keyword=%s regions=%d",
            keyword,
            len(regions),
        )
        return regions


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------
def get_trends_client() -> Optional[GoogleTrendsClient]:
    """工厂函数：返回配置好的 GoogleTrendsClient 或 None.

    读取 src/config.py 中的 GOOGLE_TRENDS_ENABLED 和 GOOGLE_TRENDS_API_KEY 配置。
    当功能未启用或 API 密钥未设置时，返回 None 表示 Google Trends 不可用。

    使用方式::

        client = get_trends_client()
        if client:
            data = await client.get_interest_over_time(["keyword"])
        else:
            # Google Trends 不可用，跳过或使用备选数据源
            pass

    Returns:
        配置好的 GoogleTrendsClient 实例，或 None（功能未启用/密钥缺失）。
    """
    try:
        from src.config import settings
    except Exception:
        logger.warning("google_trends config unavailable, returning None")
        return None

    if not getattr(settings, "GOOGLE_TRENDS_ENABLED", False):
        logger.debug("google_trends disabled via config")
        return None

    api_key = getattr(settings, "GOOGLE_TRENDS_API_KEY", None)
    if not api_key:
        logger.warning("google_trends enabled but GOOGLE_TRENDS_API_KEY not set")
        return None

    logger.info("google_trends client initialized")
    return GoogleTrendsClient(api_key=api_key)

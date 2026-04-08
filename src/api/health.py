"""Health check endpoints for external services."""
from __future__ import annotations

import asyncio
import importlib
import time
from typing import Any, Dict

from fastapi import APIRouter
from sqlalchemy import text

from src.config import settings
from src.db.connection import get_engine

router = APIRouter(prefix="/api/health", tags=["health"])

_VALID_SERVICES = {"openai", "database", "seller-sprite", "ads-api", "sp-api", "feishu", "all"}


def _result(service: str, status: str, latency_ms: int, detail: str | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"service": service, "status": status, "latency_ms": latency_ms}
    if detail:
        payload["detail"] = detail
    return payload


def _latency_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


async def _check_openai() -> Dict[str, Any]:
    start = time.perf_counter()
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return _result("openai", "not_configured", _latency_ms(start))

    try:
        openai_module = importlib.import_module("openai")
        client = openai_module.OpenAI(api_key=api_key)
        await asyncio.to_thread(client.models.list)
        return _result("openai", "ok", _latency_ms(start))
    except Exception as exc:
        return _result("openai", "error", _latency_ms(start), str(exc))


async def _check_database() -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        def _run_query() -> None:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

        await asyncio.to_thread(_run_query)
        return _result("database", "ok", _latency_ms(start))
    except Exception as exc:
        return _result("database", "error", _latency_ms(start), str(exc))


def _check_configured(service: str, keys: tuple[str, ...]) -> Dict[str, Any]:
    start = time.perf_counter()
    for key in keys:
        value = getattr(settings, key, None)
        if value:
            return _result(service, "ok", _latency_ms(start))
    return _result(service, "not_configured", _latency_ms(start))


async def _check_service(service: str) -> Dict[str, Any]:
    if service == "openai":
        return await _check_openai()
    if service == "database":
        return await _check_database()
    if service == "seller-sprite":
        return _check_configured(service, ("SELLER_SPRITE_API_KEY",))
    if service == "ads-api":
        return _check_configured(service, ("AMAZON_ADS_CLIENT_ID",))
    if service == "sp-api":
        return _check_configured(service, ("AMAZON_SP_API_CLIENT_ID", "AMAZON_SP_API_REFRESH_TOKEN"))
    if service == "feishu":
        return _check_configured(service, ("FEISHU_APP_ID", "FEISHU_APP_SECRET"))

    return {"service": service, "status": "error", "latency_ms": 0, "detail": "unknown service"}


@router.get("/{service}")
async def health_check(service: str) -> Dict[str, Any]:
    if service not in _VALID_SERVICES:
        return {"service": service, "status": "error", "latency_ms": 0, "detail": "unknown service"}

    if service == "all":
        checks = await asyncio.gather(
            _check_service("openai"),
            _check_service("database"),
            _check_service("seller-sprite"),
            _check_service("ads-api"),
            _check_service("sp-api"),
            _check_service("feishu"),
        )
        statuses = [item["status"] for item in checks]
        if any(status == "error" for status in statuses):
            overall_status = "error"
        elif any(status == "not_configured" for status in statuses):
            overall_status = "degraded"
        else:
            overall_status = "ok"
        return {"overall_status": overall_status, "services": checks}

    return await _check_service(service)

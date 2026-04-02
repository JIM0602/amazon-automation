"""LLM 响应缓存模块。

功能:
  - compute_cache_key()     — 根据 prompt/context/model 计算哈希键
  - get_cached_response()   — 查询缓存（支持 TTL 过期）
  - set_cached_response()   — 写入缓存
  - record_cache_hit()      — 记录命中统计
  - get_cache_stats()       — 获取缓存命中率和节省的Token统计
  - cleanup_expired_cache() — 清理过期缓存条目
  - is_cacheable()          — 判断请求是否可缓存（实时数据/超大响应排除）

设计原则:
  - 不缓存含实时数据的查询（如"今日销量"等关键词）
  - 不缓存超过 1MB 的响应
  - 默认 TTL 24 小时
  - 数据库存储，预留 Redis 接口

Redis 扩展接口（预留）:
  - 可在 settings 中配置 REDIS_URL 启用 Redis 作为缓存后端
  - 当前实现使用 DB 存储，Redis 接口在未来版本中实现
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging as _logging
    logger = _logging.getLogger(__name__)  # type: ignore[assignment]

# 模块级懒加载 db 相关（便于测试 patch）
try:
    from src.db.connection import db_session
except Exception:  # pragma: no cover
    db_session = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 默认缓存 TTL（秒）
DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24小时

# 最大可缓存响应大小（字节）
MAX_CACHEABLE_RESPONSE_BYTES = 1 * 1024 * 1024  # 1MB

# 实时数据关键词（包含这些词的请求不缓存）
_REALTIME_KEYWORDS = [
    "今日销量",
    "today's sales",
    "today sales",
    "实时",
    "real-time",
    "realtime",
    "当前库存",
    "current inventory",
    "最新价格",
    "latest price",
    "当前价格",
    "current price",
    "此刻",
    "right now",
    "live data",
    "实时数据",
]


# ---------------------------------------------------------------------------
# 哈希计算
# ---------------------------------------------------------------------------

def compute_cache_key(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """计算请求的缓存键（SHA-256 哈希）。

    Args:
        messages: OpenAI 格式消息列表
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数

    Returns:
        十六进制 SHA-256 哈希字符串（64位）
    """
    # 构造确定性的序列化字符串
    key_data = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # 使用 sort_keys=True 保证键序稳定
    serialized = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_prompt_hash(messages: List[Dict[str, Any]]) -> str:
    """单独计算 prompt（消息内容）的哈希。

    Args:
        messages: 消息列表

    Returns:
        十六进制 SHA-256 哈希字符串
    """
    serialized = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 可缓存性检查
# ---------------------------------------------------------------------------

def is_cacheable(
    messages: List[Dict[str, Any]],
    response_content: Optional[str] = None,
) -> bool:
    """判断请求/响应是否可以被缓存。

    排除条件:
      1. 消息中包含实时数据关键词
      2. 响应内容超过 1MB

    Args:
        messages: 消息列表
        response_content: 响应内容（可选，用于大小检查）

    Returns:
        True 表示可缓存，False 表示不可缓存
    """
    # 检查实时数据关键词
    full_text = " ".join(
        msg.get("content", "") for msg in messages if isinstance(msg.get("content"), str)
    ).lower()

    for keyword in _REALTIME_KEYWORDS:
        if keyword.lower() in full_text:
            logger.debug(f"跳过缓存：检测到实时数据关键词 {keyword!r}")
            return False

    # 检查响应大小
    if response_content is not None:
        size_bytes = len(response_content.encode("utf-8"))
        if size_bytes > MAX_CACHEABLE_RESPONSE_BYTES:
            logger.debug(f"跳过缓存：响应过大 {size_bytes} bytes > {MAX_CACHEABLE_RESPONSE_BYTES}")
            return False

    return True


# ---------------------------------------------------------------------------
# 缓存读取
# ---------------------------------------------------------------------------

def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """从缓存中查询响应。

    Args:
        cache_key: 缓存键（SHA-256 哈希）

    Returns:
        缓存命中时返回响应字典，未命中或已过期返回 None
    """
    try:
        from src.db.models import LlmCache
        from sqlalchemy import and_

        now = datetime.now(tz=timezone.utc)

        with db_session() as session:
            entry = session.query(LlmCache).filter(
                and_(
                    LlmCache.cache_key == cache_key,
                    LlmCache.expires_at > now,
                )
            ).first()

            if entry is None:
                return None

            # 反序列化响应
            response_data = entry.response_json
            if isinstance(response_data, str):
                response_data = json.loads(response_data)

            logger.debug(f"缓存命中: key={cache_key[:16]}...")
            return response_data

    except Exception as e:
        logger.warning(f"查询缓存失败（返回 None）: {e}")
        return None


# ---------------------------------------------------------------------------
# 缓存写入
# ---------------------------------------------------------------------------

def set_cached_response(
    cache_key: str,
    messages: List[Dict[str, Any]],
    model: str,
    response: Dict[str, Any],
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    """将响应写入缓存。

    Args:
        cache_key: 缓存键
        messages: 原始消息列表（用于计算 prompt_hash）
        model: 模型名称
        response: 要缓存的响应字典
        ttl_seconds: 缓存有效期（秒），默认 24 小时

    Returns:
        True 表示写入成功，False 表示失败
    """
    try:
        from src.db.models import LlmCache

        now = datetime.now(tz=timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        prompt_hash = compute_prompt_hash(messages)

        with db_session() as session:
            # 检查是否已存在（upsert 语义）
            existing = session.query(LlmCache).filter(
                LlmCache.cache_key == cache_key
            ).first()

            if existing:
                # 更新现有条目
                existing.response_json = response
                existing.expires_at = expires_at
                existing.created_at = now
            else:
                # 创建新条目
                entry = LlmCache(
                    cache_key=cache_key,
                    prompt_hash=prompt_hash,
                    response_json=response,
                    model=model,
                    created_at=now,
                    expires_at=expires_at,
                    hit_count=0,
                )
                session.add(entry)

            session.commit()
            logger.debug(f"缓存写入成功: key={cache_key[:16]}..., expires={expires_at.isoformat()}")
            return True

    except Exception as e:
        logger.warning(f"写入缓存失败（非阻塞）: {e}")
        return False


# ---------------------------------------------------------------------------
# 命中计数
# ---------------------------------------------------------------------------

def record_cache_hit(cache_key: str) -> None:
    """记录一次缓存命中，更新 hit_count。

    Args:
        cache_key: 缓存键
    """
    try:
        from src.db.models import LlmCache

        with db_session() as session:
            entry = session.query(LlmCache).filter(
                LlmCache.cache_key == cache_key
            ).first()

            if entry:
                entry.hit_count = (entry.hit_count or 0) + 1
                session.commit()
                logger.debug(f"缓存命中计数 +1: key={cache_key[:16]}..., hits={entry.hit_count}")

    except Exception as e:
        logger.warning(f"更新缓存命中计数失败（非阻塞）: {e}")


# ---------------------------------------------------------------------------
# 缓存统计
# ---------------------------------------------------------------------------

def get_cache_stats() -> Dict[str, Any]:
    """获取缓存使用统计。

    Returns:
        {
            "total_entries": int,       — 总缓存条目数
            "active_entries": int,      — 有效（未过期）条目数
            "expired_entries": int,     — 已过期条目数
            "total_hits": int,          — 总命中次数
            "hit_rate": float,          — 命中率（0-1）
            "total_llm_calls": int,     — 总 LLM 调用次数（命中 + 未命中）
            "estimated_saved_tokens": int, — 估算节省的 token 数
            "estimated_saved_cost_usd": float, — 估算节省的费用（USD）
        }
    """
    try:
        from src.db.models import LlmCache, AgentRun
        from sqlalchemy import func, and_

        now = datetime.now(tz=timezone.utc)

        with db_session() as session:
            # 总条目数
            total_entries = session.query(func.count(LlmCache.cache_key)).scalar() or 0

            # 有效条目数
            active_entries = session.query(func.count(LlmCache.cache_key)).filter(
                LlmCache.expires_at > now
            ).scalar() or 0

            expired_entries = total_entries - active_entries

            # 总命中次数
            total_hits = session.query(
                func.coalesce(func.sum(LlmCache.hit_count), 0)
            ).scalar() or 0
            total_hits = int(total_hits)

            # 总 LLM 调用次数（从 agent_runs 获取）
            total_llm_calls_db = session.query(func.count(AgentRun.id)).filter(
                AgentRun.agent_type == "llm_call"
            ).scalar() or 0

            # 总调用次数 = 实际调用 + 缓存命中
            total_llm_calls = int(total_llm_calls_db) + total_hits

            # 命中率
            hit_rate = (total_hits / total_llm_calls) if total_llm_calls > 0 else 0.0

            # 估算节省的 token 数（从缓存条目的响应数据中提取）
            # 获取所有有命中记录的缓存条目的响应数据
            hit_entries = session.query(LlmCache).filter(
                LlmCache.hit_count > 0
            ).all()

            estimated_saved_tokens = 0
            estimated_saved_cost_usd = 0.0

            for entry in hit_entries:
                resp = entry.response_json
                if isinstance(resp, str):
                    try:
                        resp = json.loads(resp)
                    except Exception:
                        continue
                if isinstance(resp, dict):
                    in_tokens = resp.get("input_tokens", 0) or 0
                    out_tokens = resp.get("output_tokens", 0) or 0
                    hits = entry.hit_count or 0
                    total_tokens = (in_tokens + out_tokens) * hits
                    estimated_saved_tokens += total_tokens

                    # 估算节省费用
                    cost_per_call = resp.get("cost_usd", 0.0) or 0.0
                    estimated_saved_cost_usd += cost_per_call * hits

            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "total_hits": total_hits,
                "hit_rate": hit_rate,
                "total_llm_calls": total_llm_calls,
                "estimated_saved_tokens": estimated_saved_tokens,
                "estimated_saved_cost_usd": estimated_saved_cost_usd,
            }

    except Exception as e:
        logger.warning(f"获取缓存统计失败: {e}")
        return {
            "total_entries": 0,
            "active_entries": 0,
            "expired_entries": 0,
            "total_hits": 0,
            "hit_rate": 0.0,
            "total_llm_calls": 0,
            "estimated_saved_tokens": 0,
            "estimated_saved_cost_usd": 0.0,
        }


# ---------------------------------------------------------------------------
# 过期缓存清理
# ---------------------------------------------------------------------------

def cleanup_expired_cache() -> int:
    """清理所有已过期的缓存条目。

    Returns:
        删除的条目数量
    """
    try:
        from src.db.models import LlmCache

        now = datetime.now(tz=timezone.utc)

        with db_session() as session:
            deleted = session.query(LlmCache).filter(
                LlmCache.expires_at <= now
            ).delete(synchronize_session=False)
            session.commit()
            logger.info(f"清理过期缓存完成：删除 {deleted} 条记录")
            return deleted

    except Exception as e:
        logger.warning(f"清理过期缓存失败: {e}")
        return 0

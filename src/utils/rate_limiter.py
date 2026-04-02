"""统一限流控制器模块。

基于令牌桶算法（Token Bucket）实现多维度限流：
  - 按 API 组（api_group）
  - 按账号（account_id）
  - 按优先级（priority）

限流触发行为：
  - acquire() 默认模式：返回 RateLimitResult，超限时 allowed=False, status_code=429
  - acquire_or_wait() 模式：排队等待直到令牌可用（阻塞）
  - acquire_or_raise() 模式：超限时直接抛出 RateLimitExceeded 异常

设计约束：
  - 纯内存实现，无 Redis 依赖
  - 单机限流，不支持分布式
  - 线程安全（threading.Lock）

令牌桶算法：
  - 每个桶有容量 capacity 和速率 rate (tokens/second)
  - 每次调用消耗 1 个令牌（可配置）
  - burst: 允许突发到 capacity 个令牌
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging as _logging
    logger = _logging.getLogger(__name__)  # type: ignore[assignment]

from src.utils.api_priority import ApiPriority


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------
class RateLimitExceeded(Exception):
    """限流触发时抛出，HTTP 语义为 429 Too Many Requests。"""

    def __init__(
        self,
        api_group: str,
        account_id: str,
        priority: ApiPriority,
        retry_after: float = 0.0,
    ):
        self.api_group = api_group
        self.account_id = account_id
        self.priority = priority
        self.retry_after = retry_after
        self.status_code = 429
        super().__init__(
            f"Rate limit exceeded: api_group={api_group!r} "
            f"account={account_id!r} priority={priority.value!r} "
            f"retry_after={retry_after:.2f}s"
        )


# ---------------------------------------------------------------------------
# 限流结果
# ---------------------------------------------------------------------------
@dataclass
class RateLimitResult:
    """acquire() 的返回结果。

    Attributes:
        allowed:       是否允许通过
        status_code:   HTTP 状态码（200=允许, 429=限流）
        tokens_left:   当前令牌桶剩余令牌数
        retry_after:   建议重试等待时间（秒），仅在 allowed=False 时有意义
        api_group:     API 分组
        account_id:    账号 ID
        priority:      优先级
    """
    allowed: bool
    status_code: int
    tokens_left: float
    retry_after: float
    api_group: str
    account_id: str
    priority: ApiPriority


# ---------------------------------------------------------------------------
# 令牌桶
# ---------------------------------------------------------------------------
class TokenBucket:
    """令牌桶实现。

    Args:
        rate:     令牌填充速率（tokens/second）
        capacity: 桶容量（最大 burst 数）
    """

    def __init__(self, rate: float, capacity: float):
        if rate <= 0:
            raise ValueError(f"rate must be > 0, got {rate}")
        if capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {capacity}")

        self.rate = rate
        self.capacity = capacity
        self._tokens: float = capacity  # 初始满桶
        self._last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """根据时间差补充令牌（内部调用，调用前须持锁）。"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        added = elapsed * self.rate
        self._tokens = min(self.capacity, self._tokens + added)
        self._last_refill = now

    def consume(self, tokens: float = 1.0) -> tuple[bool, float, float]:
        """尝试消耗令牌。

        Args:
            tokens: 消耗令牌数，默认 1.0

        Returns:
            tuple[allowed: bool, tokens_left: float, retry_after: float]
              - allowed: 是否成功消耗
              - tokens_left: 消耗后剩余令牌数
              - retry_after: 若不允许，预计需要等待的秒数
        """
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True, self._tokens, 0.0
            else:
                # 计算需要等待的时间
                deficit = tokens - self._tokens
                retry_after = deficit / self.rate
                return False, self._tokens, retry_after

    def wait_and_consume(self, tokens: float = 1.0, timeout: float = 30.0) -> bool:
        """阻塞等待直到有足够令牌，然后消耗。

        Args:
            tokens:  消耗令牌数
            timeout: 最大等待秒数，超时后返回 False

        Returns:
            bool: 是否成功消耗（False 表示超时）
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            allowed, _, retry_after = self.consume(tokens)
            if allowed:
                return True
            # 等待（最多等到 deadline）
            sleep_time = min(retry_after, deadline - time.monotonic(), 0.1)
            if sleep_time > 0:
                time.sleep(sleep_time)
        return False

    @property
    def tokens(self) -> float:
        """当前令牌数（近似值，读取时会先补充）。"""
        with self._lock:
            self._refill()
            return self._tokens


# ---------------------------------------------------------------------------
# 限流控制器（全局单例）
# ---------------------------------------------------------------------------
@dataclass
class BucketConfig:
    """令牌桶配置。

    Attributes:
        rate:     令牌填充速率（tokens/second）
        capacity: 桶容量（burst 上限）
    """
    rate: float
    capacity: float


# 默认令牌桶配置（按 API 组）
_DEFAULT_BUCKET_CONFIGS: dict[str, BucketConfig] = {
    "llm": BucketConfig(rate=2.0, capacity=10.0),          # LLM: 2 req/s, burst 10
    "seller_sprite": BucketConfig(rate=5.0, capacity=20.0), # 卖家精灵: 5 req/s, burst 20
    "risk_control": BucketConfig(rate=10.0, capacity=50.0), # 风控: 10 req/s, burst 50
    "ad_execution": BucketConfig(rate=5.0, capacity=25.0),  # 广告: 5 req/s, burst 25
    "market_research": BucketConfig(rate=1.0, capacity=5.0), # 市场调研: 1 req/s, burst 5
    "default": BucketConfig(rate=3.0, capacity=15.0),       # 默认: 3 req/s, burst 15
}


class RateLimiter:
    """统一限流控制器。

    按 (api_group, account_id) 维度管理令牌桶，同时考虑优先级权重。

    Usage::

        limiter = RateLimiter()

        # 尝试获取令牌（不阻塞）
        result = limiter.acquire(api_group="llm", account_id="account_001")
        if not result.allowed:
            return {"error": "rate limit exceeded"}, 429

        # 排队等待
        result = limiter.acquire_or_wait(api_group="seller_sprite", account_id="default")

        # 超限时抛出异常
        limiter.acquire_or_raise(api_group="llm", account_id="account_001")
    """

    def __init__(
        self,
        bucket_configs: Optional[dict[str, BucketConfig]] = None,
    ):
        """初始化限流控制器。

        Args:
            bucket_configs: 自定义令牌桶配置，键为 api_group，值为 BucketConfig
        """
        self._configs = bucket_configs or dict(_DEFAULT_BUCKET_CONFIGS)
        # {(api_group, account_id): TokenBucket}
        self._buckets: dict[tuple[str, str], TokenBucket] = {}
        self._lock = threading.Lock()

        # 统计指标
        self._stats: dict[str, int] = {
            "total_requests": 0,
            "allowed_requests": 0,
            "throttled_requests": 0,
        }
        self._stats_lock = threading.Lock()

    def _get_bucket(self, api_group: str, account_id: str) -> TokenBucket:
        """获取或创建令牌桶（懒加载）。"""
        key = (api_group, account_id)
        with self._lock:
            if key not in self._buckets:
                config = self._configs.get(api_group) or self._configs.get("default")
                if config is None:
                    config = BucketConfig(rate=3.0, capacity=15.0)
                self._buckets[key] = TokenBucket(
                    rate=config.rate,
                    capacity=config.capacity,
                )
                logger.debug(
                    f"rate_limiter: created bucket api_group={api_group!r} "
                    f"account={account_id!r} rate={config.rate}/s capacity={config.capacity}"
                )
            return self._buckets[key]

    def _priority_tokens(self, priority: ApiPriority, tokens: float = 1.0) -> float:
        """根据优先级权重计算实际消耗令牌数。

        高优先级消耗更少的虚拟令牌（更容易通过），低优先级消耗更多。

        Args:
            priority: 调用优先级
            tokens:   基础消耗令牌数

        Returns:
            实际消耗令牌数（按权重调整）
        """
        # 权重越高（critical=1.0），实际消耗越少（1/1.0=1）
        # 权重越低（batch=0.3），实际消耗越多（1/0.3≈3.33）
        return tokens / priority.weight

    def acquire(
        self,
        api_group: str,
        account_id: str = "default",
        priority: Optional[ApiPriority] = None,
        tokens: float = 1.0,
    ) -> RateLimitResult:
        """尝试获取令牌（非阻塞）。

        Args:
            api_group:  API 分组，如 "llm"、"seller_sprite"
            account_id: 账号 ID，默认 "default"
            priority:   调用优先级，影响实际消耗令牌数
            tokens:     基础消耗令牌数，默认 1.0

        Returns:
            RateLimitResult，allowed=True 表示允许通过
        """
        if priority is None:
            priority = ApiPriority.NORMAL

        bucket = self._get_bucket(api_group, account_id)
        actual_tokens = self._priority_tokens(priority, tokens)
        allowed, tokens_left, retry_after = bucket.consume(actual_tokens)

        with self._stats_lock:
            self._stats["total_requests"] += 1
            if allowed:
                self._stats["allowed_requests"] += 1
            else:
                self._stats["throttled_requests"] += 1

        result = RateLimitResult(
            allowed=allowed,
            status_code=200 if allowed else 429,
            tokens_left=tokens_left,
            retry_after=retry_after,
            api_group=api_group,
            account_id=account_id,
            priority=priority,
        )

        if not allowed:
            logger.warning(
                f"rate_limiter: throttled api_group={api_group!r} account={account_id!r} "
                f"priority={priority.value!r} retry_after={retry_after:.2f}s"
            )

        return result

    def acquire_or_wait(
        self,
        api_group: str,
        account_id: str = "default",
        priority: Optional[ApiPriority] = None,
        tokens: float = 1.0,
        timeout: float = 30.0,
    ) -> RateLimitResult:
        """排队等待直到令牌可用（阻塞）。

        Args:
            api_group:  API 分组
            account_id: 账号 ID
            priority:   调用优先级
            tokens:     基础消耗令牌数
            timeout:    最大等待秒数，超时后返回 429

        Returns:
            RateLimitResult，超时时 allowed=False
        """
        if priority is None:
            priority = ApiPriority.NORMAL

        bucket = self._get_bucket(api_group, account_id)
        actual_tokens = self._priority_tokens(priority, tokens)
        success = bucket.wait_and_consume(actual_tokens, timeout=timeout)

        with self._stats_lock:
            self._stats["total_requests"] += 1
            if success:
                self._stats["allowed_requests"] += 1
            else:
                self._stats["throttled_requests"] += 1

        if success:
            return RateLimitResult(
                allowed=True,
                status_code=200,
                tokens_left=bucket.tokens,
                retry_after=0.0,
                api_group=api_group,
                account_id=account_id,
                priority=priority,
            )
        else:
            logger.warning(
                f"rate_limiter: wait timeout api_group={api_group!r} "
                f"account={account_id!r} timeout={timeout}s"
            )
            return RateLimitResult(
                allowed=False,
                status_code=429,
                tokens_left=bucket.tokens,
                retry_after=timeout,
                api_group=api_group,
                account_id=account_id,
                priority=priority,
            )

    def acquire_or_raise(
        self,
        api_group: str,
        account_id: str = "default",
        priority: Optional[ApiPriority] = None,
        tokens: float = 1.0,
    ) -> RateLimitResult:
        """尝试获取令牌，失败时抛出 RateLimitExceeded。

        Args:
            api_group:  API 分组
            account_id: 账号 ID
            priority:   调用优先级
            tokens:     基础消耗令牌数

        Returns:
            RateLimitResult（allowed=True）

        Raises:
            RateLimitExceeded: 令牌不足时抛出（status_code=429）
        """
        result = self.acquire(
            api_group=api_group,
            account_id=account_id,
            priority=priority,
            tokens=tokens,
        )
        if not result.allowed:
            raise RateLimitExceeded(
                api_group=api_group,
                account_id=account_id,
                priority=result.priority,
                retry_after=result.retry_after,
            )
        return result

    def get_stats(self) -> dict[str, int]:
        """获取限流统计指标。

        Returns:
            dict with keys: total_requests, allowed_requests, throttled_requests
        """
        with self._stats_lock:
            return dict(self._stats)

    def reset_stats(self) -> None:
        """重置统计指标（测试用）。"""
        with self._stats_lock:
            self._stats = {
                "total_requests": 0,
                "allowed_requests": 0,
                "throttled_requests": 0,
            }

    def get_bucket_tokens(self, api_group: str, account_id: str = "default") -> float:
        """获取指定桶的当前令牌数（用于监控/测试）。

        Returns:
            float: 当前令牌数（-1 表示桶不存在）
        """
        key = (api_group, account_id)
        with self._lock:
            bucket = self._buckets.get(key)
        if bucket is None:
            return -1.0
        return bucket.tokens

    def reset_bucket(self, api_group: str, account_id: str = "default") -> None:
        """重置指定令牌桶（测试用）。"""
        key = (api_group, account_id)
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
_global_limiter: Optional[RateLimiter] = None
_global_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """获取全局限流控制器单例。

    Returns:
        RateLimiter 实例（懒初始化）
    """
    global _global_limiter
    if _global_limiter is None:
        with _global_limiter_lock:
            if _global_limiter is None:
                _global_limiter = RateLimiter()
                logger.info("rate_limiter: global instance initialized")
    return _global_limiter


def reset_global_limiter() -> None:
    """重置全局限流控制器（测试用）。"""
    global _global_limiter
    with _global_limiter_lock:
        _global_limiter = None

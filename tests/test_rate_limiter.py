"""限流模块 (src/utils/rate_limiter.py & src/utils/api_priority.py) 的单元测试。

测试覆盖：
  1. TokenBucket 令牌桶算法
  2. ApiPriority 优先级枚举
  3. RateLimiter 限流控制器（acquire/acquire_or_wait/acquire_or_raise）
  4. 优先级权重影响
  5. 限流触发时返回 429 或排队等待
  6. 统计指标
"""
from __future__ import annotations

import time
import threading
from unittest.mock import patch, MagicMock

import pytest

from src.utils.rate_limiter import (
    TokenBucket,
    RateLimiter,
    RateLimitResult,
    RateLimitExceeded,
    BucketConfig,
    get_rate_limiter,
    reset_global_limiter,
)
from src.utils.api_priority import ApiPriority, get_priority, API_GROUP_PRIORITY


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def reset_limiter():
    """每个测试后重置全局限流器单例，防止状态污染。"""
    yield
    reset_global_limiter()


@pytest.fixture
def fast_bucket():
    """创建一个高速令牌桶（rate=100/s，capacity=10），便于测试。"""
    return TokenBucket(rate=100.0, capacity=10.0)


@pytest.fixture
def slow_bucket():
    """创建一个极慢令牌桶（rate=0.1/s，capacity=2），便于测试限流。"""
    return TokenBucket(rate=0.1, capacity=2.0)


@pytest.fixture
def limiter():
    """创建带自定义配置的限流器（小容量，便于测试触发限流）。"""
    configs = {
        "llm": BucketConfig(rate=100.0, capacity=5.0),
        "seller_sprite": BucketConfig(rate=100.0, capacity=3.0),
        "tight": BucketConfig(rate=0.1, capacity=2.0),
        "default": BucketConfig(rate=100.0, capacity=10.0),
    }
    return RateLimiter(bucket_configs=configs)


# ===========================================================================
# TokenBucket 测试
# ===========================================================================

class TestTokenBucket:
    """测试令牌桶基础功能。"""

    def test_initial_tokens_full(self, fast_bucket):
        """初始状态桶是满的。"""
        assert fast_bucket.tokens == pytest.approx(10.0, abs=0.01)

    def test_consume_single_token(self, fast_bucket):
        """消耗 1 个令牌成功。"""
        allowed, tokens_left, retry_after = fast_bucket.consume(1.0)
        assert allowed is True
        assert tokens_left == pytest.approx(9.0, abs=0.01)
        assert retry_after == 0.0

    def test_consume_all_tokens(self, fast_bucket):
        """消耗所有令牌成功。"""
        allowed, tokens_left, _ = fast_bucket.consume(10.0)
        assert allowed is True
        assert tokens_left == pytest.approx(0.0, abs=0.01)

    def test_consume_exceeds_capacity_returns_429(self, slow_bucket):
        """消耗超过剩余令牌时，返回 allowed=False。"""
        # 先耗尽令牌
        slow_bucket.consume(2.0)
        allowed, tokens_left, retry_after = slow_bucket.consume(1.0)
        assert allowed is False
        assert retry_after > 0.0

    def test_retry_after_is_positive_on_throttle(self, slow_bucket):
        """限流时 retry_after > 0。"""
        slow_bucket.consume(2.0)  # 耗尽
        _, _, retry_after = slow_bucket.consume(1.0)
        assert retry_after > 0.0

    def test_tokens_refill_over_time(self):
        """令牌会随时间补充。"""
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        # 耗尽桶
        bucket.consume(10.0)
        assert bucket.tokens == pytest.approx(0.0, abs=0.1)

        # 等待 0.2 秒，预计补充 2 个令牌
        time.sleep(0.2)
        tokens = bucket.tokens
        assert tokens >= 1.5  # 最少补充 1.5 个（考虑误差）

    def test_tokens_do_not_exceed_capacity(self):
        """令牌数不超过容量。"""
        bucket = TokenBucket(rate=100.0, capacity=5.0)
        time.sleep(0.1)  # 等待补充
        assert bucket.tokens <= 5.0 + 0.01  # 允许微小浮点误差

    def test_invalid_rate_raises(self):
        """rate <= 0 应抛出 ValueError。"""
        with pytest.raises(ValueError, match="rate must be > 0"):
            TokenBucket(rate=0, capacity=10.0)

    def test_invalid_capacity_raises(self):
        """capacity <= 0 应抛出 ValueError。"""
        with pytest.raises(ValueError, match="capacity must be > 0"):
            TokenBucket(rate=1.0, capacity=0)

    def test_wait_and_consume_success(self):
        """wait_and_consume 在有令牌时立即返回 True。"""
        bucket = TokenBucket(rate=10.0, capacity=5.0)
        result = bucket.wait_and_consume(1.0, timeout=1.0)
        assert result is True

    def test_wait_and_consume_timeout(self):
        """wait_and_consume 超时后返回 False。"""
        bucket = TokenBucket(rate=0.01, capacity=1.0)
        bucket.consume(1.0)  # 耗尽
        start = time.monotonic()
        result = bucket.wait_and_consume(1.0, timeout=0.3)
        elapsed = time.monotonic() - start
        assert result is False
        assert elapsed >= 0.2  # 至少等待了 0.2 秒

    def test_thread_safety(self):
        """并发消耗令牌，总消耗量不超过容量（使用极慢补充速率确保无回补）。"""
        # rate=0.001/s（极慢），capacity=10，在短时间内令牌几乎不会回补
        bucket = TokenBucket(rate=0.001, capacity=10.0)
        results = []
        lock = threading.Lock()

        def consume():
            allowed, _, _ = bucket.consume(1.0)
            with lock:
                results.append(allowed)

        threads = [threading.Thread(target=consume) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed_count = sum(1 for r in results if r)
        # 初始容量 10，极慢速率，20个线程中最多 10 个允许通过
        assert allowed_count <= 10


# ===========================================================================
# ApiPriority 测试
# ===========================================================================

class TestApiPriority:
    """测试 API 优先级枚举。"""

    def test_priority_weights(self):
        """优先级权重正确。"""
        assert ApiPriority.CRITICAL.weight == 1.0
        assert ApiPriority.NORMAL.weight == 0.6
        assert ApiPriority.BATCH.weight == 0.3

    def test_priority_order(self):
        """优先级排序：critical < normal < batch。"""
        assert ApiPriority.CRITICAL.order < ApiPriority.NORMAL.order
        assert ApiPriority.NORMAL.order < ApiPriority.BATCH.order

    def test_priority_values(self):
        """枚举值正确。"""
        assert ApiPriority.CRITICAL.value == "critical"
        assert ApiPriority.NORMAL.value == "normal"
        assert ApiPriority.BATCH.value == "batch"

    def test_get_priority_known_groups(self):
        """已知 API 组返回正确优先级。"""
        assert get_priority("llm") == ApiPriority.NORMAL
        assert get_priority("seller_sprite") == ApiPriority.BATCH
        assert get_priority("risk_control") == ApiPriority.CRITICAL
        assert get_priority("ad_execution") == ApiPriority.NORMAL
        assert get_priority("market_research") == ApiPriority.BATCH

    def test_get_priority_unknown_group_defaults_to_batch(self):
        """未知 API 组默认返回 BATCH。"""
        result = get_priority("unknown_group_xyz")
        assert result == ApiPriority.BATCH

    def test_get_priority_case_insensitive(self):
        """大小写不敏感。"""
        assert get_priority("LLM") == ApiPriority.NORMAL
        assert get_priority("SELLER_SPRITE") == ApiPriority.BATCH

    def test_api_group_priority_mapping(self):
        """API_GROUP_PRIORITY 映射包含关键分组。"""
        assert "llm" in API_GROUP_PRIORITY
        assert "seller_sprite" in API_GROUP_PRIORITY
        assert "risk_control" in API_GROUP_PRIORITY
        assert "emergency_pricing" in API_GROUP_PRIORITY
        assert "market_research" in API_GROUP_PRIORITY


# ===========================================================================
# RateLimiter 测试
# ===========================================================================

class TestRateLimiter:
    """测试限流控制器 acquire() 接口。"""

    def test_acquire_allowed(self, limiter):
        """正常情况下 acquire 返回 allowed=True。"""
        result = limiter.acquire(api_group="llm", account_id="acc1")
        assert result.allowed is True
        assert result.status_code == 200
        assert result.tokens_left >= 0.0

    def test_acquire_returns_429_on_throttle(self, limiter):
        """令牌耗尽时 acquire 返回 allowed=False, status_code=429。"""
        # 耗尽 tight 桶（capacity=2）
        for _ in range(10):
            limiter.acquire(
                api_group="tight",
                account_id="acc1",
                priority=ApiPriority.CRITICAL,  # weight=1.0，不放大消耗
            )
        result = limiter.acquire(
            api_group="tight",
            account_id="acc1",
            priority=ApiPriority.CRITICAL,
        )
        assert result.allowed is False
        assert result.status_code == 429
        assert result.retry_after > 0.0

    def test_acquire_result_contains_metadata(self, limiter):
        """acquire 结果包含完整元数据。"""
        result = limiter.acquire(
            api_group="llm",
            account_id="account_001",
            priority=ApiPriority.NORMAL,
        )
        assert result.api_group == "llm"
        assert result.account_id == "account_001"
        assert result.priority == ApiPriority.NORMAL

    def test_acquire_different_accounts_independent(self, limiter):
        """不同账号的令牌桶相互独立。"""
        # 耗尽 acc1 的 llm 桶（capacity=5，CRITICAL weight=1.0，每次消耗1令牌）
        for _ in range(5):
            limiter.acquire(
                api_group="llm",
                account_id="acc1",
                priority=ApiPriority.CRITICAL,
            )
        # acc1 被限流
        result_acc1 = limiter.acquire(
            api_group="llm",
            account_id="acc1",
            priority=ApiPriority.CRITICAL,
        )
        assert result_acc1.allowed is False
        # acc2 不受影响，初始满桶可以通过
        result_acc2 = limiter.acquire(
            api_group="llm",
            account_id="acc2",
            priority=ApiPriority.CRITICAL,
        )
        assert result_acc2.allowed is True

    def test_acquire_stats_tracked(self, limiter):
        """统计指标被正确跟踪。"""
        limiter.reset_stats()
        # 5 次允许的请求
        for _ in range(5):
            limiter.acquire(api_group="llm", account_id="stats_test", priority=ApiPriority.CRITICAL)

        stats = limiter.get_stats()
        assert stats["total_requests"] == 5
        assert stats["allowed_requests"] == 5
        assert stats["throttled_requests"] == 0

    def test_throttled_request_counted_in_stats(self, limiter):
        """被限流的请求被计入统计。"""
        limiter.reset_stats()
        # 耗尽桶
        for _ in range(20):
            limiter.acquire(api_group="tight", account_id="stats2", priority=ApiPriority.CRITICAL)
        stats = limiter.get_stats()
        assert stats["throttled_requests"] > 0
        assert stats["total_requests"] == stats["allowed_requests"] + stats["throttled_requests"]

    def test_reset_bucket(self, limiter):
        """重置令牌桶后，新桶从满容量开始。"""
        # 先耗尽
        for _ in range(20):
            limiter.acquire(api_group="tight", account_id="reset_test", priority=ApiPriority.CRITICAL)
        result_throttled = limiter.acquire(api_group="tight", account_id="reset_test", priority=ApiPriority.CRITICAL)

        # 重置
        limiter.reset_bucket("tight", "reset_test")

        # 重置后应该可以通过
        result_after = limiter.acquire(api_group="tight", account_id="reset_test", priority=ApiPriority.CRITICAL)
        assert result_after.allowed is True

    def test_get_bucket_tokens_before_creation(self, limiter):
        """未创建的桶返回 -1。"""
        tokens = limiter.get_bucket_tokens("nonexistent", "nobody")
        assert tokens == -1.0

    def test_get_bucket_tokens_after_creation(self, limiter):
        """创建后的桶返回实际令牌数。"""
        limiter.acquire(api_group="llm", account_id="tok_test")
        tokens = limiter.get_bucket_tokens("llm", "tok_test")
        assert tokens >= 0.0


# ===========================================================================
# 优先级权重影响测试
# ===========================================================================

class TestPriorityWeights:
    """测试优先级对实际令牌消耗的影响。"""

    def test_critical_consumes_less_than_batch(self, limiter):
        """CRITICAL 比 BATCH 消耗更少令牌。"""
        # 使用 tight 桶（capacity=2）
        # CRITICAL weight=1.0 → 消耗 1/1.0=1 令牌
        # BATCH weight=0.3 → 消耗 1/0.3≈3.33 令牌

        # 先对 acc_critical 做 CRITICAL 请求
        results_critical = []
        for _ in range(5):
            r = limiter.acquire(api_group="tight", account_id="acc_critical", priority=ApiPriority.CRITICAL)
            results_critical.append(r.allowed)

        # 对 acc_batch 做 BATCH 请求
        results_batch = []
        for _ in range(5):
            r = limiter.acquire(api_group="tight", account_id="acc_batch", priority=ApiPriority.BATCH)
            results_batch.append(r.allowed)

        # CRITICAL 允许更多请求通过（消耗少）
        critical_allowed = sum(1 for r in results_critical if r)
        batch_allowed = sum(1 for r in results_batch if r)
        assert critical_allowed > batch_allowed

    def test_normal_priority_allowed_count_between_critical_and_batch(self, limiter):
        """NORMAL 优先级允许量介于 CRITICAL 和 BATCH 之间。"""
        groups = {
            "critical": ApiPriority.CRITICAL,
            "normal": ApiPriority.NORMAL,
            "batch": ApiPriority.BATCH,
        }
        allowed_counts = {}
        for name, prio in groups.items():
            count = 0
            for _ in range(10):
                r = limiter.acquire(api_group="tight", account_id=f"prio_{name}", priority=prio)
                if r.allowed:
                    count += 1
            allowed_counts[name] = count

        # CRITICAL 允许最多，BATCH 最少
        assert allowed_counts["critical"] >= allowed_counts["normal"]
        assert allowed_counts["normal"] >= allowed_counts["batch"]


# ===========================================================================
# acquire_or_raise 测试
# ===========================================================================

class TestAcquireOrRaise:
    """测试 acquire_or_raise 接口。"""

    def test_acquire_or_raise_success(self, limiter):
        """有令牌时不抛出异常，返回 RateLimitResult。"""
        result = limiter.acquire_or_raise(api_group="llm", account_id="raise_test")
        assert isinstance(result, RateLimitResult)
        assert result.allowed is True

    def test_acquire_or_raise_throttled_raises_exception(self, limiter):
        """令牌耗尽时抛出 RateLimitExceeded。"""
        # 耗尽 tight 桶
        for _ in range(20):
            try:
                limiter.acquire_or_raise(
                    api_group="tight",
                    account_id="raise_acc",
                    priority=ApiPriority.CRITICAL,
                )
            except RateLimitExceeded:
                break

        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.acquire_or_raise(
                api_group="tight",
                account_id="raise_acc",
                priority=ApiPriority.CRITICAL,
            )

        exc = exc_info.value
        assert exc.status_code == 429
        assert exc.api_group == "tight"
        assert exc.account_id == "raise_acc"
        assert exc.priority == ApiPriority.CRITICAL
        assert exc.retry_after >= 0.0

    def test_rate_limit_exceeded_message(self, limiter):
        """RateLimitExceeded 异常消息包含关键信息。"""
        for _ in range(20):
            try:
                limiter.acquire_or_raise(
                    api_group="tight",
                    account_id="msg_test",
                    priority=ApiPriority.NORMAL,
                )
            except RateLimitExceeded:
                break

        try:
            limiter.acquire_or_raise(
                api_group="tight",
                account_id="msg_test",
                priority=ApiPriority.NORMAL,
            )
        except RateLimitExceeded as exc:
            assert "tight" in str(exc)
            assert "msg_test" in str(exc)
            assert "normal" in str(exc)


# ===========================================================================
# acquire_or_wait 测试
# ===========================================================================

class TestAcquireOrWait:
    """测试 acquire_or_wait 阻塞等待接口。"""

    def test_acquire_or_wait_success_immediately(self, limiter):
        """有令牌时立即返回 allowed=True。"""
        result = limiter.acquire_or_wait(api_group="llm", account_id="wait_test", timeout=1.0)
        assert result.allowed is True
        assert result.status_code == 200

    def test_acquire_or_wait_timeout_returns_429(self):
        """等待超时后返回 429。"""
        configs = {"tight": BucketConfig(rate=0.01, capacity=1.0)}
        lim = RateLimiter(bucket_configs=configs)
        lim.acquire(api_group="tight", account_id="wait_timeout", priority=ApiPriority.CRITICAL)  # 耗尽

        start = time.monotonic()
        result = lim.acquire_or_wait(
            api_group="tight",
            account_id="wait_timeout",
            priority=ApiPriority.CRITICAL,
            timeout=0.3,
        )
        elapsed = time.monotonic() - start

        assert result.allowed is False
        assert result.status_code == 429
        assert elapsed >= 0.2  # 至少等待了约 timeout 时间

    def test_acquire_or_wait_succeeds_after_refill(self):
        """等待令牌补充后成功获取。"""
        configs = {"fast_refill": BucketConfig(rate=20.0, capacity=1.0)}
        lim = RateLimiter(bucket_configs=configs)
        lim.acquire(api_group="fast_refill", account_id="refill_test", priority=ApiPriority.CRITICAL)  # 耗尽

        # 等待 0.2 秒后应能补充令牌（rate=20/s，0.2s=4 tokens）
        result = lim.acquire_or_wait(
            api_group="fast_refill",
            account_id="refill_test",
            priority=ApiPriority.CRITICAL,
            timeout=1.0,
        )
        assert result.allowed is True


# ===========================================================================
# 全局单例测试
# ===========================================================================

class TestGlobalSingleton:
    """测试全局限流器单例。"""

    def test_get_rate_limiter_returns_same_instance(self):
        """get_rate_limiter() 多次调用返回同一实例。"""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_reset_global_limiter_creates_new_instance(self):
        """reset_global_limiter() 后获取的是新实例。"""
        limiter1 = get_rate_limiter()
        reset_global_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is not limiter2


# ===========================================================================
# 审计日志集成测试
# ===========================================================================

class TestRateLimitAudit:
    """测试限流事件的审计日志记录。"""

    def test_log_rate_limit_event_throttled(self):
        """log_rate_limit_event 在限流时写入正确数据。"""
        from contextlib import contextmanager
        from unittest.mock import MagicMock, patch

        mock_session = MagicMock()

        @contextmanager
        def mock_db_session():
            yield mock_session

        with patch("src.utils.audit.db_session", mock_db_session):
            from src.utils.audit import log_rate_limit_event
            log_rate_limit_event(
                api_group="llm",
                account_id="acc1",
                priority="normal",
                allowed=False,
                tokens_left=0.0,
                retry_after=2.5,
            )

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.action == "rate_limit_throttled"
        assert added.post_state["api_group"] == "llm"
        assert added.post_state["allowed"] is False
        assert added.post_state["retry_after"] == 2.5

    def test_log_rate_limit_event_allowed(self):
        """log_rate_limit_event 在允许时写入正确数据。"""
        from contextlib import contextmanager
        from unittest.mock import MagicMock, patch

        mock_session = MagicMock()

        @contextmanager
        def mock_db_session():
            yield mock_session

        with patch("src.utils.audit.db_session", mock_db_session):
            from src.utils.audit import log_rate_limit_event
            log_rate_limit_event(
                api_group="seller_sprite",
                account_id="acc2",
                priority="batch",
                allowed=True,
                tokens_left=5.0,
                retry_after=0.0,
            )

        added = mock_session.add.call_args[0][0]
        assert added.action == "rate_limit_allowed"
        assert added.post_state["allowed"] is True
        assert added.post_state["tokens_left"] == 5.0


# ===========================================================================
# LLM 客户端集成测试
# ===========================================================================

class TestLLMClientRateLimit:
    """测试 LLM 客户端集成限流。"""

    def test_llm_chat_throttled_raises_rate_limit_exceeded(self):
        """LLM chat 被限流时抛出 RateLimitExceeded。"""
        from unittest.mock import patch, MagicMock

        # 创建一个耗尽的限流器 mock
        mock_limiter = MagicMock()
        mock_limiter.acquire_or_raise.side_effect = RateLimitExceeded(
            api_group="llm",
            account_id="default",
            priority=ApiPriority.NORMAL,
            retry_after=5.0,
        )

        with patch("src.llm.client.get_rate_limiter", return_value=mock_limiter):
            from src.llm.client import chat
            with pytest.raises(RateLimitExceeded) as exc_info:
                chat(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "test"}],
                )
            assert exc_info.value.status_code == 429

    def test_llm_chat_passes_priority_to_limiter(self):
        """LLM chat 将 priority 参数传递给限流器。"""
        mock_limiter = MagicMock()
        mock_result = RateLimitResult(
            allowed=True, status_code=200, tokens_left=9.0,
            retry_after=0.0, api_group="llm", account_id="default",
            priority=ApiPriority.CRITICAL,
        )
        mock_limiter.acquire_or_raise.return_value = mock_result

        # mock check_daily_limit
        mock_status = {"exceeded": False, "warning": False, "daily_cost": 0.0, "limit": 50.0, "percentage": 0.0}

        with patch("src.llm.client.get_rate_limiter", return_value=mock_limiter), \
             patch("src.llm.client.check_daily_limit", return_value=mock_status), \
             patch("src.llm.client._call_llm_api", return_value={
                 "content": "ok", "model": "gpt-4o-mini",
                 "input_tokens": 10, "output_tokens": 5,
             }), \
             patch("src.llm.client._record_agent_run"):
            from src.llm.client import chat
            chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
                priority=ApiPriority.CRITICAL,
                account_id="special_account",
            )

        mock_limiter.acquire_or_raise.assert_called_once_with(
            api_group="llm",
            account_id="special_account",
            priority=ApiPriority.CRITICAL,
        )


# ===========================================================================
# SellerSprite 客户端集成测试
# ===========================================================================

class TestSellerSpriteRateLimit:
    """测试 SellerSprite 客户端集成限流。"""

    def test_seller_sprite_throttled_raises_rate_limit_exceeded(self):
        """SellerSprite 被限流时抛出 RateLimitExceeded。"""
        from unittest.mock import patch, MagicMock
        from src.seller_sprite.client import MockSellerSpriteClient

        mock_limiter = MagicMock()
        mock_limiter.acquire_or_raise.side_effect = RateLimitExceeded(
            api_group="seller_sprite",
            account_id="default",
            priority=ApiPriority.BATCH,
            retry_after=10.0,
        )

        with patch("src.seller_sprite.client.get_rate_limiter", return_value=mock_limiter):
            client = MockSellerSpriteClient()
            with pytest.raises(RateLimitExceeded):
                client.search_keyword("dog leash")

    def test_seller_sprite_passes_account_id(self):
        """SellerSprite 方法将 account_id 传递给限流器。"""
        mock_limiter = MagicMock()
        mock_result = RateLimitResult(
            allowed=True, status_code=200, tokens_left=9.0,
            retry_after=0.0, api_group="seller_sprite", account_id="my_account",
            priority=ApiPriority.BATCH,
        )
        mock_limiter.acquire_or_raise.return_value = mock_result

        from src.seller_sprite.client import MockSellerSpriteClient, clear_cache
        clear_cache()

        with patch("src.seller_sprite.client.get_rate_limiter", return_value=mock_limiter):
            client = MockSellerSpriteClient()
            client.search_keyword("dog leash", account_id="my_account")

        mock_limiter.acquire_or_raise.assert_called_once_with(
            api_group="seller_sprite",
            account_id="my_account",
            priority=ApiPriority.BATCH,
        )

"""LLM 模块测试。

运行方式:
    pytest tests/test_llm.py --mock-external-apis -v
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_session():
    """Mock db_session 上下文管理器，避免真实数据库连接。"""
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    with patch("src.llm.client.db_session", return_value=mock_session) as mock_ctx:
        yield mock_session


@pytest.fixture
def mock_settings():
    """Mock settings 以提供测试配置。"""
    mock_cfg = MagicMock()
    mock_cfg.MAX_DAILY_LLM_COST_USD = 50.0
    mock_cfg.FEISHU_TEST_CHAT_ID = None
    mock_cfg.OPENAI_API_KEY = "test-api-key"
    return mock_cfg


@pytest.fixture
def mock_llm_api_response():
    """标准 mock LLM API 响应。"""
    return {
        "content": "This is a test response from the LLM.",
        "model": "gpt-4o-mini",
        "input_tokens": 50,
        "output_tokens": 20,
    }


# ---------------------------------------------------------------------------
# 测试：filter_pii
# ---------------------------------------------------------------------------

class TestFilterPii:
    """验证 PII 过滤功能。"""

    def test_email_redaction(self):
        from src.llm.cost_monitor import filter_pii
        text = "联系我：user@example.com，谢谢"
        result = filter_pii(text)
        assert "[REDACTED_EMAIL]" in result
        assert "user@example.com" not in result

    def test_multiple_emails(self):
        from src.llm.cost_monitor import filter_pii
        text = "发送到 admin@test.org 和 user@domain.co.uk"
        result = filter_pii(text)
        assert result.count("[REDACTED_EMAIL]") == 2
        assert "@" not in result.replace("[REDACTED_EMAIL]", "")

    def test_phone_us_dash_format(self):
        from src.llm.cost_monitor import filter_pii
        text = "电话：555-123-4567"
        result = filter_pii(text)
        assert "[REDACTED_PHONE]" in result
        assert "555-123-4567" not in result

    def test_phone_us_parenthesis_format(self):
        from src.llm.cost_monitor import filter_pii
        text = "电话：(555) 123-4567"
        result = filter_pii(text)
        assert "[REDACTED_PHONE]" in result

    def test_phone_international_format(self):
        from src.llm.cost_monitor import filter_pii
        text = "电话：+1-555-123-4567"
        result = filter_pii(text)
        assert "[REDACTED_PHONE]" in result

    def test_credit_card_redaction(self):
        from src.llm.cost_monitor import filter_pii
        text = "卡号：4111-1111-1111-1111"
        result = filter_pii(text)
        assert "[REDACTED_CARD]" in result
        assert "4111-1111-1111-1111" not in result

    def test_credit_card_space_separated(self):
        from src.llm.cost_monitor import filter_pii
        text = "卡号：4111 1111 1111 1111"
        result = filter_pii(text)
        assert "[REDACTED_CARD]" in result

    def test_no_pii_text_unchanged(self):
        from src.llm.cost_monitor import filter_pii
        text = "这是一段普通文本，没有敏感信息。"
        result = filter_pii(text)
        assert result == text

    def test_combined_pii(self):
        from src.llm.cost_monitor import filter_pii
        text = "联系：john@example.com，电话：555-123-4567，卡号：4111-1111-1111-1111"
        result = filter_pii(text)
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_PHONE]" in result
        assert "[REDACTED_CARD]" in result
        assert "john@example.com" not in result

    def test_filter_pii_returns_string(self):
        from src.llm.cost_monitor import filter_pii
        result = filter_pii("hello world")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 测试：_calculate_cost
# ---------------------------------------------------------------------------

class TestCalculateCost:
    """验证费用计算准确性。"""

    def test_gpt4o_mini_cost(self):
        from src.llm.client import _calculate_cost
        # 1000 input tokens * $0.00015/1K + 1000 output tokens * $0.00060/1K
        cost = _calculate_cost("gpt-4o-mini", 1000, 1000)
        assert abs(cost - 0.00075) < 1e-8

    def test_gpt4o_cost(self):
        from src.llm.client import _calculate_cost
        # 1000 input * 0.005 + 1000 output * 0.015 = 0.02
        cost = _calculate_cost("gpt-4o", 1000, 1000)
        assert abs(cost - 0.020) < 1e-8

    def test_claude_3_5_sonnet_cost(self):
        from src.llm.client import _calculate_cost
        # 1000 input * 0.003 + 1000 output * 0.015 = 0.018
        cost = _calculate_cost("claude-3-5-sonnet", 1000, 1000)
        assert abs(cost - 0.018) < 1e-8

    def test_claude_3_haiku_cost(self):
        from src.llm.client import _calculate_cost
        # 1000 input * 0.00025 + 1000 output * 0.00125 = 0.0015
        cost = _calculate_cost("claude-3-haiku", 1000, 1000)
        assert abs(cost - 0.00150) < 1e-8

    def test_zero_tokens_cost_is_zero(self):
        from src.llm.client import _calculate_cost
        cost = _calculate_cost("gpt-4o-mini", 0, 0)
        assert cost == 0.0

    def test_cost_is_float(self):
        from src.llm.client import _calculate_cost
        cost = _calculate_cost("gpt-4o-mini", 500, 200)
        assert isinstance(cost, float)


# ---------------------------------------------------------------------------
# 测试：check_daily_limit
# ---------------------------------------------------------------------------

class TestCheckDailyLimit:
    """验证每日费用上限检查逻辑。"""

    def test_check_daily_limit_under_limit(self):
        from src.llm.cost_monitor import check_daily_limit
        with patch("src.llm.cost_monitor.get_daily_cost", return_value=10.0), \
             patch("src.llm.cost_monitor.settings") as mock_settings:
            mock_settings.MAX_DAILY_LLM_COST_USD = 50.0
            result = check_daily_limit()

        assert result["daily_cost"] == 10.0
        assert result["limit"] == 50.0
        assert abs(result["percentage"] - 20.0) < 0.01
        assert result["exceeded"] is False
        assert result["warning"] is False

    def test_check_daily_limit_warning_at_80_percent(self):
        from src.llm.cost_monitor import check_daily_limit
        with patch("src.llm.cost_monitor.get_daily_cost", return_value=40.0), \
             patch("src.llm.cost_monitor.settings") as mock_settings:
            mock_settings.MAX_DAILY_LLM_COST_USD = 50.0
            result = check_daily_limit()

        assert result["warning"] is True
        assert result["exceeded"] is False

    def test_check_daily_limit_exceeded_at_100_percent(self):
        from src.llm.cost_monitor import check_daily_limit
        with patch("src.llm.cost_monitor.get_daily_cost", return_value=50.0), \
             patch("src.llm.cost_monitor.settings") as mock_settings:
            mock_settings.MAX_DAILY_LLM_COST_USD = 50.0
            result = check_daily_limit()

        assert result["exceeded"] is True
        assert result["warning"] is True

    def test_check_daily_limit_over_100_percent(self):
        from src.llm.cost_monitor import check_daily_limit
        with patch("src.llm.cost_monitor.get_daily_cost", return_value=60.0), \
             patch("src.llm.cost_monitor.settings") as mock_settings:
            mock_settings.MAX_DAILY_LLM_COST_USD = 50.0
            result = check_daily_limit()

        assert result["exceeded"] is True
        assert result["percentage"] > 100.0

    def test_check_daily_limit_returns_all_keys(self):
        from src.llm.cost_monitor import check_daily_limit
        with patch("src.llm.cost_monitor.get_daily_cost", return_value=5.0), \
             patch("src.llm.cost_monitor.settings") as mock_settings:
            mock_settings.MAX_DAILY_LLM_COST_USD = 50.0
            result = check_daily_limit()

        assert "daily_cost" in result
        assert "limit" in result
        assert "percentage" in result
        assert "exceeded" in result
        assert "warning" in result


# ---------------------------------------------------------------------------
# 测试：chat() 主接口
# ---------------------------------------------------------------------------

class TestChat:
    """验证 chat() 主接口功能。"""

    def test_chat_returns_correct_keys(self, mock_llm_api_response):
        from src.llm.client import chat

        with patch("src.llm.client._call_llm_api", return_value=mock_llm_api_response), \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 0.0, "limit": 50.0,
                 "percentage": 0.0, "exceeded": False, "warning": False
             }), \
             patch("src.llm.client._record_agent_run"):
            result = chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )

        assert "content" in result
        assert "model" in result
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert "cost_usd" in result

    def test_chat_returns_correct_types(self, mock_llm_api_response):
        from src.llm.client import chat

        with patch("src.llm.client._call_llm_api", return_value=mock_llm_api_response), \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 0.0, "limit": 50.0,
                 "percentage": 0.0, "exceeded": False, "warning": False
             }), \
             patch("src.llm.client._record_agent_run"):
            result = chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )

        assert isinstance(result["content"], str)
        assert isinstance(result["model"], str)
        assert isinstance(result["input_tokens"], int)
        assert isinstance(result["output_tokens"], int)
        assert isinstance(result["cost_usd"], float)

    def test_chat_pii_filtered_before_api_call(self):
        """验证 PII 在发送给 LLM 之前已被过滤。"""
        from src.llm.client import chat

        captured_messages = []

        def capture_api_call(model, messages, temperature, max_tokens):
            captured_messages.extend(messages)
            return {
                "content": "response",
                "model": model,
                "input_tokens": 10,
                "output_tokens": 5,
            }

        with patch("src.llm.client._call_llm_api", side_effect=capture_api_call), \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 0.0, "limit": 50.0,
                 "percentage": 0.0, "exceeded": False, "warning": False
             }), \
             patch("src.llm.client._record_agent_run"):
            chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "我的邮箱是 test@example.com"}],
            )

        assert len(captured_messages) == 1
        # PII 应该已被过滤
        assert "test@example.com" not in captured_messages[0]["content"]
        assert "[REDACTED_EMAIL]" in captured_messages[0]["content"]

    def test_chat_raises_daily_cost_limit_exceeded(self):
        """超出每日上限时应抛出 DailyCostLimitExceeded。"""
        from src.llm.client import chat, DailyCostLimitExceeded

        with patch("src.llm.client.check_daily_limit", return_value={
            "daily_cost": 55.0, "limit": 50.0,
            "percentage": 110.0, "exceeded": True, "warning": True
        }):
            with pytest.raises(DailyCostLimitExceeded) as exc_info:
                chat(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "test"}],
                )

        assert exc_info.value.daily_cost == 55.0
        assert exc_info.value.limit == 50.0

    def test_chat_does_not_call_api_when_limit_exceeded(self):
        """超出上限时不应调用实际 API。"""
        from src.llm.client import chat, DailyCostLimitExceeded

        with patch("src.llm.client.check_daily_limit", return_value={
            "daily_cost": 55.0, "limit": 50.0,
            "percentage": 110.0, "exceeded": True, "warning": True
        }), patch("src.llm.client._call_llm_api") as mock_api:
            with pytest.raises(DailyCostLimitExceeded):
                chat(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "test"}],
                )
            mock_api.assert_not_called()

    def test_chat_records_agent_run(self, mock_llm_api_response):
        """验证 chat() 调用后会记录 agent_runs。"""
        from src.llm.client import chat

        with patch("src.llm.client._call_llm_api", return_value=mock_llm_api_response), \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 0.0, "limit": 50.0,
                 "percentage": 0.0, "exceeded": False, "warning": False
             }), \
             patch("src.llm.client._record_agent_run") as mock_record:
            chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args
        assert call_kwargs[1]["model"] == "gpt-4o-mini"
        assert isinstance(call_kwargs[1]["cost_usd"], float)

    def test_chat_db_failure_does_not_raise(self, mock_llm_api_response):
        """数据库写入失败时不应影响 LLM 调用结果。"""
        from src.llm.client import chat

        def failing_record(*args, **kwargs):
            raise RuntimeError("数据库连接失败")

        with patch("src.llm.client._call_llm_api", return_value=mock_llm_api_response), \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 0.0, "limit": 50.0,
                 "percentage": 0.0, "exceeded": False, "warning": False
             }), \
             patch("src.llm.client._record_agent_run", side_effect=failing_record):
            # 应该正常返回，不抛出异常
            result = chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )

        assert result["content"] == mock_llm_api_response["content"]

    def test_chat_cost_calculated_correctly(self, mock_llm_api_response):
        """验证费用计算正确。"""
        from src.llm.client import chat

        with patch("src.llm.client._call_llm_api", return_value=mock_llm_api_response), \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 0.0, "limit": 50.0,
                 "percentage": 0.0, "exceeded": False, "warning": False
             }), \
             patch("src.llm.client._record_agent_run"):
            result = chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )

        # input_tokens=50, output_tokens=20
        # cost = (50/1000 * 0.00015) + (20/1000 * 0.00060)
        expected_cost = (50 / 1000 * 0.00015) + (20 / 1000 * 0.00060)
        assert abs(result["cost_usd"] - expected_cost) < 1e-10

    def test_chat_sends_feishu_warning_at_80_percent(self, mock_llm_api_response):
        """当费用达到 80% 时应发送飞书预警。"""
        from src.llm.client import chat

        with patch("src.llm.client._call_llm_api", return_value=mock_llm_api_response), \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 40.0, "limit": 50.0,
                 "percentage": 80.0, "exceeded": False, "warning": True
             }), \
             patch("src.llm.client.send_feishu_warning") as mock_warn, \
             patch("src.llm.client._record_agent_run"):
            chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )

        mock_warn.assert_called_once_with(80.0)

    def test_chat_default_parameters(self, mock_llm_api_response):
        """验证默认参数 temperature=0.7, max_tokens=2000。"""
        from src.llm.client import chat

        with patch("src.llm.client._call_llm_api", return_value=mock_llm_api_response) as mock_api, \
             patch("src.llm.client.check_daily_limit", return_value={
                 "daily_cost": 0.0, "limit": 50.0,
                 "percentage": 0.0, "exceeded": False, "warning": False
             }), \
             patch("src.llm.client._record_agent_run"):
            chat(model="gpt-4o-mini", messages=[{"role": "user", "content": "test"}])

        call_kwargs = mock_api.call_args[1]
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 2000


# ---------------------------------------------------------------------------
# 测试：DailyCostLimitExceeded 异常
# ---------------------------------------------------------------------------

class TestDailyCostLimitExceeded:
    """验证 DailyCostLimitExceeded 异常类。"""

    def test_exception_is_subclass_of_exception(self):
        from src.llm.client import DailyCostLimitExceeded
        assert issubclass(DailyCostLimitExceeded, Exception)

    def test_exception_stores_cost_and_limit(self):
        from src.llm.client import DailyCostLimitExceeded
        exc = DailyCostLimitExceeded(daily_cost=55.0, limit=50.0)
        assert exc.daily_cost == 55.0
        assert exc.limit == 50.0

    def test_exception_message_contains_cost(self):
        from src.llm.client import DailyCostLimitExceeded
        exc = DailyCostLimitExceeded(daily_cost=55.0, limit=50.0)
        assert "55" in str(exc)
        assert "50" in str(exc)


# ---------------------------------------------------------------------------
# 测试：_record_agent_run
# ---------------------------------------------------------------------------

class TestRecordAgentRun:
    """验证 agent_runs 写入功能。"""

    def test_record_agent_run_writes_correct_fields(self):
        from src.llm.client import _record_agent_run

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        started = datetime.now(tz=timezone.utc)
        finished = datetime.now(tz=timezone.utc)

        with patch("src.llm.client.db_session", return_value=mock_session), \
             patch("src.llm.client.AgentRun") as mock_agent_run:
            _record_agent_run(
                model="gpt-4o-mini",
                content="Test response content",
                cost_usd=0.001,
                started_at=started,
                finished_at=finished,
            )

        mock_agent_run.assert_called_once()
        call_kwargs = mock_agent_run.call_args[1]
        assert call_kwargs["agent_type"] == "llm_call"
        assert call_kwargs["status"] == "completed"
        assert call_kwargs["input_summary"] == "gpt-4o-mini"
        assert call_kwargs["output_summary"] == "Test response content"
        assert call_kwargs["cost_usd"] == 0.001

    def test_record_agent_run_truncates_output_to_100_chars(self):
        from src.llm.client import _record_agent_run

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        long_content = "A" * 200
        started = datetime.now(tz=timezone.utc)

        with patch("src.llm.client.db_session", return_value=mock_session), \
             patch("src.llm.client.AgentRun") as mock_agent_run:
            _record_agent_run(
                model="gpt-4o",
                content=long_content,
                cost_usd=0.05,
                started_at=started,
                finished_at=started,
            )

        call_kwargs = mock_agent_run.call_args[1]
        assert len(call_kwargs["output_summary"]) == 100

    def test_record_agent_run_db_failure_does_not_raise(self):
        """数据库失败时不应传播异常。"""
        from src.llm.client import _record_agent_run

        started = datetime.now(tz=timezone.utc)

        with patch("src.llm.client.db_session", side_effect=RuntimeError("DB error")):
            # 不应抛出异常
            _record_agent_run(
                model="gpt-4o-mini",
                content="test",
                cost_usd=0.001,
                started_at=started,
                finished_at=started,
            )


# ---------------------------------------------------------------------------
# 测试：send_feishu_warning
# ---------------------------------------------------------------------------

class TestSendFeishuWarning:
    """验证飞书预警发送。"""

    def test_feishu_warning_logs_when_no_chat_id(self):
        from src.llm.cost_monitor import send_feishu_warning

        with patch("src.llm.cost_monitor.settings") as mock_settings:
            mock_settings.FEISHU_TEST_CHAT_ID = None
            # 不应抛出异常
            send_feishu_warning(80.0)

    def test_feishu_warning_handles_bot_exception(self):
        from src.llm.cost_monitor import send_feishu_warning

        with patch("src.llm.cost_monitor.settings") as mock_settings, \
             patch("src.llm.cost_monitor.get_bot", side_effect=RuntimeError("连接失败")):
            mock_settings.FEISHU_TEST_CHAT_ID = "test_chat_id"
            # 不应抛出异常
            send_feishu_warning(85.0)


# ---------------------------------------------------------------------------
# 测试：包导入
# ---------------------------------------------------------------------------

class TestPackageImports:
    """验证包级别导入正常。"""

    def test_import_chat_from_package(self):
        from src.llm import chat
        assert callable(chat)

    def test_import_daily_cost_limit_exceeded(self):
        from src.llm import DailyCostLimitExceeded
        assert issubclass(DailyCostLimitExceeded, Exception)

    def test_import_filter_pii(self):
        from src.llm import filter_pii
        assert callable(filter_pii)

    def test_import_get_daily_cost(self):
        from src.llm import get_daily_cost
        assert callable(get_daily_cost)

    def test_import_check_daily_limit(self):
        from src.llm import check_daily_limit
        assert callable(check_daily_limit)

    def test_import_from_client_module(self):
        from src.llm.client import chat, DailyCostLimitExceeded, _calculate_cost
        assert callable(chat)
        assert callable(_calculate_cost)

    def test_import_from_cost_monitor_module(self):
        from src.llm.cost_monitor import filter_pii, get_daily_cost, check_daily_limit, send_feishu_warning
        assert all(callable(f) for f in [filter_pii, get_daily_cost, check_daily_limit, send_feishu_warning])

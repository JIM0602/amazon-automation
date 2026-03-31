"""审计日志模块 (src/utils/audit.py) 的单元测试。

使用 SQLite in-memory DB 和 mock db_session 进行测试。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """返回一个 mock Session 对象。"""
    session = MagicMock()
    return session


@pytest.fixture
def mock_db_session(mock_session):
    """Mock db_session 上下文管理器，yield mock_session。"""
    from contextlib import contextmanager

    @contextmanager
    def _mock_db_session():
        yield mock_session

    with patch("src.utils.audit.db_session", _mock_db_session):
        yield mock_session


# ---------------------------------------------------------------------------
# 测试 log_action
# ---------------------------------------------------------------------------

class TestLogAction:
    def test_log_action_basic(self, mock_db_session):
        """log_action 应写入一条 AuditLog 记录。"""
        from src.utils.audit import log_action
        from src.db.models import AuditLog

        log_action("test_action", "test_actor")

        mock_db_session.add.assert_called_once()
        added_obj = mock_db_session.add.call_args[0][0]
        assert isinstance(added_obj, AuditLog)
        assert added_obj.action == "test_action"
        assert added_obj.actor == "test_actor"
        assert added_obj.pre_state is None
        assert added_obj.post_state is None
        mock_db_session.commit.assert_called_once()

    def test_log_action_with_states(self, mock_db_session):
        """log_action 支持 pre_state 和 post_state。"""
        from src.utils.audit import log_action
        from src.db.models import AuditLog

        pre = {"price": 100}
        post = {"price": 200}
        log_action("price_updated", "agent:pricing", pre_state=pre, post_state=post)

        added_obj = mock_db_session.add.call_args[0][0]
        assert added_obj.pre_state == {"price": 100}
        assert added_obj.post_state == {"price": 200}

    def test_log_action_non_blocking_on_error(self):
        """log_action 失败时不抛出异常（非阻塞）。"""
        from contextlib import contextmanager

        @contextmanager
        def _failing_db_session():
            raise RuntimeError("DB 连接失败")
            yield  # pragma: no cover

        with patch("src.utils.audit.db_session", _failing_db_session):
            # 不应抛出任何异常
            from src.utils.audit import log_action
            log_action("test", "actor")  # 必须静默忽略


# ---------------------------------------------------------------------------
# 测试 get_recent_logs
# ---------------------------------------------------------------------------

class TestGetRecentLogs:
    def test_get_recent_logs_returns_list(self, mock_db_session):
        """get_recent_logs 应返回列表。"""
        from src.utils.audit import get_recent_logs
        import uuid
        from datetime import datetime, timezone

        # mock 查询结果
        mock_log = MagicMock()
        mock_log.id = uuid.uuid4()
        mock_log.action = "test_action"
        mock_log.actor = "system"
        mock_log.pre_state = None
        mock_log.post_state = {"result": "ok"}
        mock_log.created_at = datetime(2026, 3, 31, 10, 0, 0, tzinfo=timezone.utc)

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_log]
        mock_db_session.query.return_value = mock_query

        result = get_recent_logs(limit=10)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["action"] == "test_action"
        assert result[0]["actor"] == "system"
        assert result[0]["post_state"] == {"result": "ok"}
        assert "id" in result[0]
        assert "created_at" in result[0]

    def test_get_recent_logs_passes_limit(self, mock_db_session):
        """get_recent_logs 应将 limit 传递给查询。"""
        from src.utils.audit import get_recent_logs

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        get_recent_logs(limit=25)
        mock_query.limit.assert_called_with(25)

    def test_get_recent_logs_returns_empty_on_error(self):
        """get_recent_logs DB 失败时返回空列表。"""
        from contextlib import contextmanager

        @contextmanager
        def _failing_db_session():
            raise RuntimeError("DB 错误")
            yield  # pragma: no cover

        with patch("src.utils.audit.db_session", _failing_db_session):
            from src.utils.audit import get_recent_logs
            result = get_recent_logs()
            assert result == []


# ---------------------------------------------------------------------------
# 测试 audit_decorator
# ---------------------------------------------------------------------------

class TestAuditDecorator:
    def test_audit_decorator_logs_on_success(self, mock_db_session):
        """audit_decorator 在函数成功执行后记录日志。"""
        from src.utils.audit import audit_decorator, log_action
        from src.db.models import AuditLog

        @audit_decorator("test_decorated", actor="agent:test")
        def my_func(x: int) -> int:
            return x * 2

        result = my_func(5)
        assert result == 10

        # 应调用 session.add 写入一条审计日志
        mock_db_session.add.assert_called_once()
        added_obj = mock_db_session.add.call_args[0][0]
        assert added_obj.action == "test_decorated"
        assert added_obj.actor == "agent:test"
        assert added_obj.post_state is not None

    def test_audit_decorator_logs_on_exception(self, mock_db_session):
        """audit_decorator 在函数抛出异常时也记录日志，且异常继续向上传播。"""
        from src.utils.audit import audit_decorator
        from src.db.models import AuditLog

        @audit_decorator("failing_action", actor="system")
        def failing_func():
            raise ValueError("测试错误")

        with pytest.raises(ValueError, match="测试错误"):
            failing_func()

        # 仍然应该写入审计日志
        mock_db_session.add.assert_called_once()
        added_obj = mock_db_session.add.call_args[0][0]
        assert added_obj.post_state["error_type"] == "ValueError"
        assert "测试错误" in added_obj.post_state["error"]

    def test_audit_decorator_preserves_function_metadata(self):
        """audit_decorator 应保留原函数的元数据（functools.wraps）。"""
        from src.utils.audit import audit_decorator

        @audit_decorator("some_action")
        def my_named_func():
            """原始函数文档。"""
            pass

        assert my_named_func.__name__ == "my_named_func"
        assert my_named_func.__doc__ == "原始函数文档。"

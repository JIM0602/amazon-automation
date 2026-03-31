"""紧急停机模块 (src/utils/killswitch.py) 的单元测试。

使用 mock db_session 测试所有核心逻辑。
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_session_with_config(config_dict: dict):
    """创建一个模拟 db_session，session.get() 返回对应的 SystemConfig mock。"""
    def _mock_get(model_class, key):
        if key not in config_dict:
            return None
        val = config_dict[key]
        cfg = MagicMock()
        cfg.value = val
        return cfg

    session = MagicMock()
    session.get.side_effect = _mock_get

    @contextmanager
    def mock_db_session():
        yield session

    return mock_db_session, session


# ---------------------------------------------------------------------------
# 测试 SystemStoppedError
# ---------------------------------------------------------------------------

class TestSystemStoppedError:
    def test_is_exception(self):
        from src.utils.killswitch import SystemStoppedError
        err = SystemStoppedError("测试停机")
        assert isinstance(err, Exception)
        assert err.reason == "测试停机"
        assert "测试停机" in str(err)

    def test_default_message(self):
        from src.utils.killswitch import SystemStoppedError
        err = SystemStoppedError()
        assert err.reason == "系统已紧急停机"


# ---------------------------------------------------------------------------
# 测试 is_stopped
# ---------------------------------------------------------------------------

class TestIsStopped:
    def test_is_stopped_true_string(self):
        """当 system_config.emergency_stop = 'true' 时返回 True。"""
        mock_ctx, _ = _make_db_session_with_config({"emergency_stop": "true"})
        with patch("src.utils.killswitch.db_session", mock_ctx):
            from src.utils.killswitch import is_stopped
            assert is_stopped() is True

    def test_is_stopped_false_string(self):
        """当 system_config.emergency_stop = 'false' 时返回 False。"""
        mock_ctx, _ = _make_db_session_with_config({"emergency_stop": "false"})
        with patch("src.utils.killswitch.db_session", mock_ctx):
            from src.utils.killswitch import is_stopped
            assert is_stopped() is False

    def test_is_stopped_true_bool(self):
        """当 system_config.emergency_stop = True（布尔）时返回 True。"""
        mock_ctx, _ = _make_db_session_with_config({"emergency_stop": True})
        with patch("src.utils.killswitch.db_session", mock_ctx):
            from src.utils.killswitch import is_stopped
            assert is_stopped() is True

    def test_is_stopped_not_configured(self):
        """当 system_config 中无 emergency_stop 记录时返回 False。"""
        mock_ctx, _ = _make_db_session_with_config({})
        with patch("src.utils.killswitch.db_session", mock_ctx):
            from src.utils.killswitch import is_stopped
            assert is_stopped() is False

    def test_is_stopped_db_error_returns_false(self):
        """DB 查询失败时默认返回 False（安全降级）。"""
        @contextmanager
        def failing_ctx():
            raise RuntimeError("DB 断开")
            yield  # pragma: no cover

        with patch("src.utils.killswitch.db_session", failing_ctx):
            from src.utils.killswitch import is_stopped
            assert is_stopped() is False

    def test_is_stopped_reads_db_every_time(self):
        """每次调用 is_stopped() 都应查询 DB（不缓存）。"""
        call_count = 0

        @contextmanager
        def counting_ctx():
            nonlocal call_count
            call_count += 1
            session = MagicMock()
            session.get.return_value = None
            yield session

        with patch("src.utils.killswitch.db_session", counting_ctx):
            from src.utils.killswitch import is_stopped
            is_stopped()
            is_stopped()
            is_stopped()
            assert call_count == 3


# ---------------------------------------------------------------------------
# 测试 activate_stop
# ---------------------------------------------------------------------------

class TestActivateStop:
    def test_activate_stop_writes_config(self):
        """activate_stop 应写入 emergency_stop=true 及相关元数据。"""
        session = MagicMock()
        session.get.return_value = None  # 配置不存在，触发 insert

        @contextmanager
        def mock_ctx():
            yield session

        with patch("src.utils.killswitch.db_session", mock_ctx), \
             patch("src.utils.killswitch._pause_all_jobs"), \
             patch("src.utils.killswitch._send_feishu_notification"), \
             patch("src.utils.audit.db_session", mock_ctx):  # audit 也 mock
            from src.utils.killswitch import activate_stop
            activate_stop(reason="测试停机", triggered_by="test_user")

        # 应调用 session.add 写入多条配置 + audit log
        assert session.add.call_count >= 1  # 至少写入了 emergency_stop 配置

    def test_activate_stop_pauses_scheduler(self):
        """activate_stop 应调用 _pause_all_jobs。"""
        session = MagicMock()
        session.get.return_value = None

        @contextmanager
        def mock_ctx():
            yield session

        with patch("src.utils.killswitch.db_session", mock_ctx), \
             patch("src.utils.killswitch._pause_all_jobs") as mock_pause, \
             patch("src.utils.killswitch._send_feishu_notification"), \
             patch("src.utils.audit.db_session", mock_ctx):
            from src.utils.killswitch import activate_stop
            activate_stop(reason="测试停机", triggered_by="test_user")
            mock_pause.assert_called_once()

    def test_activate_stop_records_audit_log(self):
        """activate_stop 应记录 emergency_stop_activated 审计日志。"""
        session = MagicMock()
        session.get.return_value = None

        @contextmanager
        def mock_ctx():
            yield session

        with patch("src.utils.killswitch.db_session", mock_ctx), \
             patch("src.utils.killswitch._pause_all_jobs"), \
             patch("src.utils.killswitch._send_feishu_notification"), \
             patch("src.utils.audit.db_session", mock_ctx):
            from src.utils.killswitch import activate_stop
            from src.db.models import AuditLog
            activate_stop(reason="系统异常", triggered_by="admin")

        added_objects = [c[0][0] for c in session.add.call_args_list]
        audit_logs = [obj for obj in added_objects if isinstance(obj, AuditLog)]
        assert len(audit_logs) >= 1
        assert audit_logs[0].action == "emergency_stop_activated"
        assert audit_logs[0].actor == "admin"


# ---------------------------------------------------------------------------
# 测试 deactivate_stop
# ---------------------------------------------------------------------------

class TestDeactivateStop:
    def test_deactivate_stop_writes_config(self):
        """deactivate_stop 应将 emergency_stop 更新为 false。"""
        existing_cfg = MagicMock()
        existing_cfg.value = "true"

        session = MagicMock()
        def _get(cls, key):
            if key == "emergency_stop":
                return existing_cfg
            return None
        session.get.side_effect = _get

        @contextmanager
        def mock_ctx():
            yield session

        with patch("src.utils.killswitch.db_session", mock_ctx), \
             patch("src.utils.killswitch._resume_all_jobs"), \
             patch("src.utils.audit.db_session", mock_ctx):
            from src.utils.killswitch import deactivate_stop
            deactivate_stop(triggered_by="admin")

        # existing_cfg.value 应被设置为 "false"
        assert existing_cfg.value == "false"

    def test_deactivate_stop_resumes_scheduler(self):
        """deactivate_stop 应调用 _resume_all_jobs。"""
        session = MagicMock()
        session.get.return_value = None

        @contextmanager
        def mock_ctx():
            yield session

        with patch("src.utils.killswitch.db_session", mock_ctx), \
             patch("src.utils.killswitch._resume_all_jobs") as mock_resume, \
             patch("src.utils.audit.db_session", mock_ctx):
            from src.utils.killswitch import deactivate_stop
            deactivate_stop(triggered_by="admin")
            mock_resume.assert_called_once()

    def test_deactivate_stop_records_audit_log(self):
        """deactivate_stop 应记录 emergency_stop_deactivated 审计日志。"""
        session = MagicMock()
        session.get.return_value = None

        @contextmanager
        def mock_ctx():
            yield session

        with patch("src.utils.killswitch.db_session", mock_ctx), \
             patch("src.utils.killswitch._resume_all_jobs"), \
             patch("src.utils.audit.db_session", mock_ctx):
            from src.utils.killswitch import deactivate_stop
            from src.db.models import AuditLog
            deactivate_stop(triggered_by="admin")

        added_objects = [c[0][0] for c in session.add.call_args_list]
        audit_logs = [obj for obj in added_objects if isinstance(obj, AuditLog)]
        assert len(audit_logs) >= 1
        assert audit_logs[0].action == "emergency_stop_deactivated"


# ---------------------------------------------------------------------------
# 测试 check_killswitch 装饰器
# ---------------------------------------------------------------------------

class TestCheckKillswitch:
    def test_check_killswitch_allows_when_not_stopped(self):
        """系统正常时，check_killswitch 装饰器不应阻止函数执行。"""
        with patch("src.utils.killswitch.is_stopped", return_value=False):
            from src.utils.killswitch import check_killswitch

            @check_killswitch()
            def my_action():
                return "executed"

            result = my_action()
            assert result == "executed"

    def test_check_killswitch_raises_when_stopped(self):
        """系统停机时，check_killswitch 装饰器应 raise SystemStoppedError。"""
        with patch("src.utils.killswitch.is_stopped", return_value=True), \
             patch("src.utils.killswitch._get_stop_info", return_value={"reason": "测试停机"}):
            from src.utils.killswitch import check_killswitch, SystemStoppedError

            @check_killswitch()
            def my_action():
                return "should not execute"  # pragma: no cover

            with pytest.raises(SystemStoppedError) as exc_info:
                my_action()
            assert "停机" in str(exc_info.value)

    def test_check_killswitch_preserves_function_metadata(self):
        """check_killswitch 应保留原函数元数据（functools.wraps）。"""
        from src.utils.killswitch import check_killswitch

        @check_killswitch()
        def my_agent_action():
            """Agent 动作的文档。"""
            pass

        assert my_agent_action.__name__ == "my_agent_action"
        assert my_agent_action.__doc__ == "Agent 动作的文档。"

    def test_check_killswitch_error_includes_function_name(self):
        """SystemStoppedError 的消息中应包含被阻止的函数名。"""
        with patch("src.utils.killswitch.is_stopped", return_value=True), \
             patch("src.utils.killswitch._get_stop_info", return_value={"reason": "手动停机"}):
            from src.utils.killswitch import check_killswitch, SystemStoppedError

            @check_killswitch()
            def run_pricing_agent():
                pass  # pragma: no cover

            with pytest.raises(SystemStoppedError) as exc_info:
                run_pricing_agent()
            assert "run_pricing_agent" in str(exc_info.value)

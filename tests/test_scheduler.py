"""调度器模块单元测试 — 全部使用 unittest.mock，不启动真实后台线程。"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient


# ============================================================================ #
#  Helpers / Fixtures
# ============================================================================ #

_DEFAULT_NEXT_RUN = datetime.datetime(2026, 4, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)

def _make_mock_job(job_id: str, next_run_time=_DEFAULT_NEXT_RUN):
    """创建一个模拟的 APScheduler Job 对象。

    next_run_time 默认值为 2026-04-01 09:00 UTC；
    传 None 可模拟已暂停的任务（无下次执行时间）。
    """
    job = MagicMock()
    job.id = job_id
    job.next_run_time = next_run_time  # 显式赋值，支持 None
    job.trigger = MagicMock()
    job.trigger.__str__ = lambda self: "cron[hour='9', minute='0']"
    return job


@pytest.fixture(autouse=True)
def reset_scheduler_singleton():
    """每个测试前后重置调度器单例，防止跨测试污染。"""
    import src.scheduler as sched_module
    sched_module._scheduler = None
    yield
    sched_module._scheduler = None


@pytest.fixture()
def mock_apscheduler_available():
    """Mock APScheduler 为可用状态。"""
    mock_scheduler = MagicMock()
    mock_scheduler.running = False

    with patch("src.scheduler._APSCHEDULER_AVAILABLE", True), \
         patch("src.scheduler.BackgroundScheduler", return_value=mock_scheduler), \
         patch("src.scheduler.MemoryJobStore"), \
         patch("src.scheduler.ThreadPoolExecutor"):
        yield mock_scheduler


@pytest.fixture()
def mock_apscheduler_unavailable():
    """Mock APScheduler 为不可用状态（未安装）。"""
    with patch("src.scheduler._APSCHEDULER_AVAILABLE", False):
        yield


@pytest.fixture()
def client():
    """创建 FastAPI TestClient（mock 飞书设置）。"""
    import src.feishu.bot_handler as bh
    bh._bot_instance = None
    mock_bot = MagicMock()
    mock_bot.parse_webhook_event.side_effect = lambda body, headers: __import__("json").loads(body)
    bh._bot_instance = mock_bot

    from src.api.main import app
    return TestClient(app)


# ============================================================================ #
#  config.py — SCHEDULED_JOBS
# ============================================================================ #

class TestScheduledJobsConfig:
    def test_has_three_jobs(self):
        """SCHEDULED_JOBS 应有3个任务。"""
        from src.scheduler.config import SCHEDULED_JOBS
        assert len(SCHEDULED_JOBS) == 3

    def test_job_ids(self):
        """3个任务 id 应为 daily_report、selection_analysis、llm_cost_report。"""
        from src.scheduler.config import SCHEDULED_JOBS
        ids = [j["id"] for j in SCHEDULED_JOBS]
        assert "daily_report" in ids
        assert "selection_analysis" in ids
        assert "llm_cost_report" in ids

    def test_daily_report_cron(self):
        """daily_report 应在 09:00 运行。"""
        from src.scheduler.config import SCHEDULED_JOBS
        job = next(j for j in SCHEDULED_JOBS if j["id"] == "daily_report")
        assert job["trigger"] == "cron"
        assert job["hour"] == 9
        assert job["minute"] == 0

    def test_selection_analysis_cron(self):
        """selection_analysis 应在周一 10:00 运行。"""
        from src.scheduler.config import SCHEDULED_JOBS
        job = next(j for j in SCHEDULED_JOBS if j["id"] == "selection_analysis")
        assert job["trigger"] == "cron"
        assert job["day_of_week"] == "mon"
        assert job["hour"] == 10
        assert job["minute"] == 0

    def test_llm_cost_report_cron(self):
        """llm_cost_report 应在 23:00 运行。"""
        from src.scheduler.config import SCHEDULED_JOBS
        job = next(j for j in SCHEDULED_JOBS if j["id"] == "llm_cost_report")
        assert job["trigger"] == "cron"
        assert job["hour"] == 23
        assert job["minute"] == 0

    def test_all_jobs_have_description(self):
        """所有任务应有 description 字段。"""
        from src.scheduler.config import SCHEDULED_JOBS
        for job in SCHEDULED_JOBS:
            assert "description" in job
            assert len(job["description"]) > 0

    def test_all_jobs_have_func(self):
        """所有任务应有 func 字段。"""
        from src.scheduler.config import SCHEDULED_JOBS
        for job in SCHEDULED_JOBS:
            assert "func" in job
            assert "src.scheduler.jobs" in job["func"]


# ============================================================================ #
#  jobs.py — 任务函数
# ============================================================================ #

class TestJobFunctions:
    def _mock_db(self):
        """创建模拟的 db_session 上下文管理器。"""
        from contextlib import contextmanager
        mock_session = MagicMock()

        @contextmanager
        def _mock_session():
            yield mock_session

        return _mock_session, mock_session

    def test_run_daily_report_returns_ok(self):
        """run_daily_report 正常执行应返回 status=ok。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm):
            from src.scheduler.jobs import run_daily_report
            result = run_daily_report()

        assert result["status"] == "ok"
        assert result["job_id"] == "daily_report"

    def test_run_selection_analysis_returns_ok(self):
        """run_selection_analysis 正常执行应返回 status=ok。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm):
            from src.scheduler.jobs import run_selection_analysis
            result = run_selection_analysis()

        assert result["status"] == "ok"
        assert result["job_id"] == "selection_analysis"

    def test_run_llm_cost_report_returns_ok(self):
        """run_llm_cost_report 正常执行应返回 status=ok。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm):
            from src.scheduler.jobs import run_llm_cost_report
            result = run_llm_cost_report()

        assert result["status"] == "ok"
        assert result["job_id"] == "llm_cost_report"

    def test_run_daily_report_logs_started(self, caplog):
        """run_daily_report 应记录 'daily_report started' 日志。"""
        import logging
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm):
            with caplog.at_level(logging.INFO, logger="src.scheduler.jobs"):
                from src.scheduler.jobs import run_daily_report
                run_daily_report()

        assert any("daily_report started" in r.message for r in caplog.records)

    def test_run_selection_analysis_logs_started(self, caplog):
        """run_selection_analysis 应记录 'selection_analysis started' 日志。"""
        import logging
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm):
            with caplog.at_level(logging.INFO, logger="src.scheduler.jobs"):
                from src.scheduler.jobs import run_selection_analysis
                run_selection_analysis()

        assert any("selection_analysis started" in r.message for r in caplog.records)

    def test_run_llm_cost_report_logs_started(self, caplog):
        """run_llm_cost_report 应记录 'llm_cost_report started' 日志。"""
        import logging
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm):
            with caplog.at_level(logging.INFO, logger="src.scheduler.jobs"):
                from src.scheduler.jobs import run_llm_cost_report
                run_llm_cost_report()

        assert any("llm_cost_report started" in r.message for r in caplog.records)

    def test_run_daily_report_writes_agent_run(self):
        """run_daily_report 应向数据库写入 AgentRun 记录。"""
        mock_cm, mock_session = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm):
            from src.scheduler.jobs import run_daily_report
            run_daily_report()

        # session.add 应被调用（AgentRun + AuditLog = 2次）
        assert mock_session.add.call_count == 2
        assert mock_session.commit.called

    def test_run_daily_report_writes_audit_log(self):
        """run_daily_report 应向数据库写入 AuditLog 记录（action=scheduler_job_run）。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = self._mock_db()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.scheduler.jobs.db_session", mock_cm):
            from src.scheduler.jobs import run_daily_report
            run_daily_report()

        audit_logs = [obj for obj in added_objects if isinstance(obj, AuditLog)]
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "scheduler_job_run"
        assert audit_logs[0].actor == "scheduler"
        assert audit_logs[0].post_state["job_id"] == "daily_report"

    def test_job_does_not_crash_on_db_error(self):
        """数据库写入失败时，任务函数不应抛出异常（只记录警告）。"""
        from contextlib import contextmanager

        @contextmanager
        def _bad_session():
            session = MagicMock()
            session.add.side_effect = RuntimeError("数据库连接失败")
            yield session

        with patch("src.scheduler.jobs.db_session", _bad_session):
            from src.scheduler.jobs import run_daily_report
            # 不应抛出异常
            result = run_daily_report()

        # 任务本身成功，只是 db 记录失败
        assert "job_id" in result


# ============================================================================ #
#  scheduler/__init__.py — 调度器单例
# ============================================================================ #

class TestGetScheduler:
    def test_returns_none_when_apscheduler_unavailable(self, mock_apscheduler_unavailable):
        """APScheduler 不可用时 get_scheduler 应返回 None。"""
        from src.scheduler import get_scheduler
        result = get_scheduler()
        assert result is None

    def test_returns_scheduler_instance(self, mock_apscheduler_available):
        """APScheduler 可用时 get_scheduler 应返回调度器实例。"""
        from src.scheduler import get_scheduler
        result = get_scheduler()
        assert result is not None

    def test_returns_same_instance_on_second_call(self, mock_apscheduler_available):
        """多次调用 get_scheduler 应返回同一实例（单例）。"""
        from src.scheduler import get_scheduler
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2


class TestStartScheduler:
    def test_returns_false_when_apscheduler_unavailable(self, mock_apscheduler_unavailable):
        """APScheduler 不可用时 start_scheduler 应返回 False。"""
        from src.scheduler import start_scheduler
        result = start_scheduler()
        assert result is False

    def test_loads_all_three_jobs(self, mock_apscheduler_available):
        """start_scheduler 应加载全部3个任务。"""
        from src.scheduler import start_scheduler
        mock_apscheduler_available.running = False
        result = start_scheduler()

        assert result is True
        # add_job 应被调用3次
        assert mock_apscheduler_available.add_job.call_count == 3

    def test_calls_scheduler_start(self, mock_apscheduler_available):
        """start_scheduler 应调用调度器的 start() 方法。"""
        from src.scheduler import start_scheduler
        mock_apscheduler_available.running = False
        start_scheduler()
        mock_apscheduler_available.start.assert_called_once()

    def test_skips_if_already_running(self, mock_apscheduler_available):
        """调度器已运行时 start_scheduler 应跳过，不重复调用 start()。"""
        from src.scheduler import start_scheduler
        mock_apscheduler_available.running = True
        result = start_scheduler()
        assert result is True
        mock_apscheduler_available.start.assert_not_called()


class TestShutdownScheduler:
    def test_shutdown_when_running(self, mock_apscheduler_available):
        """调度器运行中时 shutdown_scheduler 应调用 shutdown()。"""
        from src.scheduler import get_scheduler, shutdown_scheduler
        # 先触发 lazy 初始化
        get_scheduler()
        mock_apscheduler_available.running = True

        shutdown_scheduler()
        mock_apscheduler_available.shutdown.assert_called_once_with(wait=True)

    def test_shutdown_noop_when_not_started(self):
        """未启动时 shutdown_scheduler 不应抛异常。"""
        from src.scheduler import shutdown_scheduler
        # _scheduler 为 None，应静默执行
        shutdown_scheduler()

    def test_resets_singleton_after_shutdown(self, mock_apscheduler_available):
        """shutdown 后单例应重置为 None。"""
        import src.scheduler as sched_module
        from src.scheduler import get_scheduler, shutdown_scheduler

        get_scheduler()
        assert sched_module._scheduler is not None

        mock_apscheduler_available.running = True
        shutdown_scheduler()
        assert sched_module._scheduler is None


# ============================================================================ #
#  FastAPI 路由测试
# ============================================================================ #

class TestSchedulerAPIUnavailable:
    def test_list_jobs_503_when_unavailable(self, client, mock_apscheduler_unavailable):
        """APScheduler 不可用时 GET /api/scheduler/jobs 应返回 503。"""
        resp = client.get("/api/scheduler/jobs")
        assert resp.status_code == 503

    def test_pause_503_when_unavailable(self, client, mock_apscheduler_unavailable):
        """APScheduler 不可用时 POST /api/scheduler/jobs/{id}/pause 应返回 503。"""
        resp = client.post("/api/scheduler/jobs/daily_report/pause")
        assert resp.status_code == 503

    def test_resume_503_when_unavailable(self, client, mock_apscheduler_unavailable):
        """APScheduler 不可用时 POST /api/scheduler/jobs/{id}/resume 应返回 503。"""
        resp = client.post("/api/scheduler/jobs/daily_report/resume")
        assert resp.status_code == 503

    def test_trigger_503_when_unavailable(self, client, mock_apscheduler_unavailable):
        """APScheduler 不可用时 POST /api/scheduler/trigger/{id} 应返回 503。"""
        resp = client.post("/api/scheduler/trigger/daily_report")
        assert resp.status_code == 503


class TestSchedulerAPIAvailable:
    @pytest.fixture(autouse=True)
    def setup_mock_scheduler(self, mock_apscheduler_available):
        """为 API 测试注入 mock 调度器实例。"""
        import src.scheduler as sched_module
        sched_module._scheduler = mock_apscheduler_available
        self.mock_scheduler = mock_apscheduler_available

    def test_list_jobs_returns_list(self, client):
        """GET /api/scheduler/jobs 应返回 JSON 数组。"""
        mock_job = _make_mock_job("daily_report")
        self.mock_scheduler.get_jobs.return_value = [mock_job]

        resp = client.get("/api/scheduler/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_jobs_includes_id_and_next_run(self, client):
        """GET /api/scheduler/jobs 的结果应包含 id 和 next_run_time。"""
        mock_job = _make_mock_job("daily_report")
        self.mock_scheduler.get_jobs.return_value = [mock_job]

        resp = client.get("/api/scheduler/jobs")
        job_data = resp.json()[0]
        assert job_data["id"] == "daily_report"
        assert "next_run_time" in job_data

    def test_list_jobs_includes_description(self, client):
        """GET /api/scheduler/jobs 的结果应包含 description。"""
        mock_job = _make_mock_job("daily_report")
        self.mock_scheduler.get_jobs.return_value = [mock_job]

        resp = client.get("/api/scheduler/jobs")
        job_data = resp.json()[0]
        assert "description" in job_data
        assert len(job_data["description"]) > 0

    def test_pause_job_success(self, client):
        """POST /api/scheduler/jobs/{id}/pause 成功时应返回 status=paused。"""
        self.mock_scheduler.pause_job.return_value = None

        resp = client.post("/api/scheduler/jobs/daily_report/pause")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paused"
        assert data["job_id"] == "daily_report"

    def test_pause_job_not_found(self, client):
        """暂停不存在的任务应返回 404。"""
        self.mock_scheduler.pause_job.side_effect = Exception("Job not found")

        resp = client.post("/api/scheduler/jobs/nonexistent/pause")
        assert resp.status_code == 404

    def test_resume_job_success(self, client):
        """POST /api/scheduler/jobs/{id}/resume 成功时应返回 status=resumed。"""
        self.mock_scheduler.resume_job.return_value = None

        resp = client.post("/api/scheduler/jobs/daily_report/resume")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resumed"
        assert data["job_id"] == "daily_report"

    def test_resume_job_not_found(self, client):
        """恢复不存在的任务应返回 404。"""
        self.mock_scheduler.resume_job.side_effect = Exception("Job not found")

        resp = client.post("/api/scheduler/jobs/nonexistent/resume")
        assert resp.status_code == 404

    def test_trigger_job_success(self, client):
        """POST /api/scheduler/trigger/{id} 成功时应返回 status=triggered。"""
        mock_job = _make_mock_job("daily_report")
        self.mock_scheduler.get_job.return_value = mock_job

        resp = client.post("/api/scheduler/trigger/daily_report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "triggered"
        assert data["job_id"] == "daily_report"

    def test_trigger_job_not_found(self, client):
        """触发不存在的任务应返回 404。"""
        self.mock_scheduler.get_job.return_value = None

        resp = client.post("/api/scheduler/trigger/nonexistent")
        assert resp.status_code == 404

    def test_list_multiple_jobs(self, client):
        """GET /api/scheduler/jobs 应能返回多个任务。"""
        jobs = [
            _make_mock_job("daily_report"),
            _make_mock_job("selection_analysis"),
            _make_mock_job("llm_cost_report"),
        ]
        self.mock_scheduler.get_jobs.return_value = jobs

        resp = client.get("/api/scheduler/jobs")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_list_jobs_with_none_next_run(self, client):
        """next_run_time 为 None 的任务（已暂停）应正确序列化。"""
        mock_job = _make_mock_job("daily_report", next_run_time=None)
        self.mock_scheduler.get_jobs.return_value = [mock_job]

        resp = client.get("/api/scheduler/jobs")
        assert resp.status_code == 200
        job_data = resp.json()[0]
        assert job_data["next_run_time"] is None

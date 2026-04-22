from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest


class _Trigger:
    def __str__(self) -> str:
        return "cron[hour='9', minute='0']"


def _make_mock_job(job_id: str, next_run_time: datetime.datetime | None) -> MagicMock:
    job = MagicMock()
    job.id = job_id
    job.next_run_time = next_run_time
    job.trigger = _Trigger()
    return job


@pytest.fixture()
def mock_scheduler(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    import src.scheduler as sched_module

    scheduler = MagicMock()
    scheduler.running = True
    scheduler.get_jobs.return_value = [
        _make_mock_job(
            "daily_report",
            datetime.datetime(2026, 4, 1, 9, 0, 0, tzinfo=datetime.timezone.utc),
        )
    ]

    def pause_job(job_id: str) -> None:
        if job_id != "daily_report":
            raise Exception("Job not found")

    def resume_job(job_id: str) -> None:
        if job_id != "daily_report":
            raise Exception("Job not found")

    def get_job(job_id: str):
        if job_id == "daily_report":
            return _make_mock_job(
                "daily_report",
                datetime.datetime(2026, 4, 1, 9, 0, 0, tzinfo=datetime.timezone.utc),
            )
        return None

    scheduler.pause_job.side_effect = pause_job
    scheduler.resume_job.side_effect = resume_job
    scheduler.get_job.side_effect = get_job

    monkeypatch.setattr(sched_module, "_APSCHEDULER_AVAILABLE", True, raising=False)
    monkeypatch.setattr(sched_module, "_scheduler", scheduler, raising=False)
    return scheduler


def test_scheduler_jobs_contract(client, boss_headers, mock_scheduler: MagicMock) -> None:
    response = client.get("/api/scheduler/jobs", headers=boss_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["id"] == "daily_report"
    assert data[0]["description"] == "每日09:00发送数据日报到飞书"
    assert data[0]["trigger"] == "cron[hour='9', minute='0']"
    assert data[0]["next_run_time"] == "2026-04-01T09:00:00+00:00"


def test_pause_scheduler_job_contract(client, boss_headers, mock_scheduler: MagicMock) -> None:
    response = client.post("/api/scheduler/jobs/daily_report/pause", headers=boss_headers)

    assert response.status_code == 200
    assert response.json() == {"status": "paused", "job_id": "daily_report"}


def test_resume_scheduler_job_contract(client, boss_headers, mock_scheduler: MagicMock) -> None:
    response = client.post("/api/scheduler/jobs/daily_report/resume", headers=boss_headers)

    assert response.status_code == 200
    assert response.json() == {"status": "resumed", "job_id": "daily_report"}


def test_trigger_scheduler_job_contract(client, boss_headers, mock_scheduler: MagicMock) -> None:
    response = client.post("/api/scheduler/trigger/daily_report", headers=boss_headers)

    assert response.status_code == 200
    assert response.json() == {"status": "triggered", "job_id": "daily_report"}


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/scheduler/jobs/unknown/pause", "post"),
        ("/api/scheduler/jobs/unknown/resume", "post"),
        ("/api/scheduler/trigger/unknown", "post"),
    ],
)
def test_invalid_job_id_returns_404(client, boss_headers, mock_scheduler: MagicMock, path: str, method: str) -> None:
    response = getattr(client, method)(path, headers=boss_headers)

    assert response.status_code == 404

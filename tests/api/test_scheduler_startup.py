from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_app_startup_loads_scheduled_jobs(monkeypatch) -> None:
    from src.api.main import app

    mock_start_scheduler = MagicMock(return_value=True)
    mock_setup_checkpointer = MagicMock()

    monkeypatch.setattr('src.scheduler.start_scheduler', mock_start_scheduler)
    monkeypatch.setattr('src.agents.checkpointer.setup_checkpointer', mock_setup_checkpointer)

    with TestClient(app, raise_server_exceptions=True):
        pass

    mock_start_scheduler.assert_called_once_with()

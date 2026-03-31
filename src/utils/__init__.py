"""Utilities package — audit logging and kill-switch helpers."""

from src.utils.audit import log_action, get_recent_logs, audit_decorator
from src.utils.killswitch import (
    is_stopped,
    activate_stop,
    deactivate_stop,
    check_killswitch,
    SystemStoppedError,
)

__all__ = [
    "log_action",
    "get_recent_logs",
    "audit_decorator",
    "is_stopped",
    "activate_stop",
    "deactivate_stop",
    "check_killswitch",
    "SystemStoppedError",
]

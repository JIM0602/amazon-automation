"""Utilities package — audit logging and kill-switch helpers."""

try:
    from src.utils.audit import log_action, get_recent_logs, audit_decorator
except Exception:  # pragma: no cover - keep utility submodules importable
    log_action = None
    get_recent_logs = None
    audit_decorator = None

try:
    from src.utils.killswitch import (
        is_stopped,
        activate_stop,
        deactivate_stop,
        check_killswitch,
        SystemStoppedError,
    )
except Exception:  # pragma: no cover - keep utility submodules importable
    is_stopped = None
    activate_stop = None
    deactivate_stop = None
    check_killswitch = None
    SystemStoppedError = None

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

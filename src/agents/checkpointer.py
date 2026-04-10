"""LangGraph PostgreSQL checkpointer for conversation state persistence."""
from __future__ import annotations

import logging
from importlib import import_module
from typing import Optional, Protocol, cast

from src.config import settings

logger = logging.getLogger(__name__)

_checkpointer: Optional[object] = None


class _PostgresSaver(Protocol):
    def setup(self) -> None: ...


def _normalize_database_url(db_url: str) -> str:
    """Normalize SQLAlchemy-style PostgreSQL URLs for LangGraph."""
    if "+psycopg2" in db_url:
        return db_url.replace("+psycopg2", "")
    if "+asyncpg" in db_url:
        return db_url.replace("+asyncpg", "")
    return db_url


def get_checkpointer() -> _PostgresSaver:
    """Return the singleton PostgresSaver instance.

    Creates it on first call. The checkpointer uses settings.DATABASE_URL
    to connect to the same PostgreSQL database used by the rest of the app.
    In langgraph-checkpoint-postgres >=3.x, ``from_conn_string`` returns a
    context manager; we call ``__enter__`` once so the singleton is a real
    PostgresSaver that can be reused across the process lifetime.
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = _create_saver()
    return cast(_PostgresSaver, _checkpointer)


def _create_saver() -> object:
    """Create a fresh PostgresSaver instance (handles context-manager API)."""
    db_url = _normalize_database_url(settings.DATABASE_URL)
    postgres_module = import_module("langgraph.checkpoint.postgres")
    saver_or_ctx = postgres_module.PostgresSaver.from_conn_string(db_url)
    # v3+ returns a context-manager; unwrap it
    if hasattr(saver_or_ctx, "__enter__"):
        saver_or_ctx = saver_or_ctx.__enter__()
    logger.info("LangGraph PostgresSaver checkpointer initialized")
    return saver_or_ctx


def setup_checkpointer() -> None:
    """Create checkpointer tables in the database.

    Uses a fresh ``psycopg.connect()`` call (not ``from_conn_string``) to
    avoid stale-connection issues in forked uvicorn workers.
    """
    import psycopg  # type: ignore[import-untyped]

    db_url = _normalize_database_url(settings.DATABASE_URL)
    postgres_module = import_module("langgraph.checkpoint.postgres")

    with psycopg.connect(db_url, autocommit=True) as conn:
        saver = postgres_module.PostgresSaver(conn)
        saver.setup()
        logger.info("Checkpointer tables created/verified")

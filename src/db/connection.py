"""Database connection pool using SQLAlchemy.

Reads DATABASE_URL from ``src.config.settings`` and exposes:
    - ``engine``        — the SQLAlchemy Engine (connection pool), lazily initialised
    - ``SessionLocal``  — a sessionmaker factory, lazily initialised
    - ``get_db()``      — FastAPI / dependency-injection compatible generator
    - ``get_engine()``  — explicit accessor that triggers lazy init
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Internal lazy state
# ---------------------------------------------------------------------------
_engine: Optional[Engine] = None
_SessionLocal = None  # type: ignore[assignment]


def _get_database_url() -> str:
    """Read DATABASE_URL from the application settings."""
    from src.config import settings  # noqa: PLC0415 — intentional lazy import

    return settings.DATABASE_URL


def _build_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine appropriate for the given URL.

    SQLite (used in testing) does not support pool_size / max_overflow,
    so those arguments are only passed for non-SQLite databases.
    """
    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        from sqlalchemy.pool import StaticPool

        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # heartbeat query before handing out connections
        pool_recycle=1800,    # recycle connections every 30 min
        echo=False,
    )


def get_engine() -> Engine:
    """Return (and lazily create) the global SQLAlchemy Engine."""
    global _engine
    if _engine is None:
        _engine = _build_engine(_get_database_url())
    return _engine


def get_session_local() -> sessionmaker:  # type: ignore[type-arg]
    """Return (and lazily create) the global sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


# ---------------------------------------------------------------------------
# Module-level aliases — lazily resolved on first access
# ---------------------------------------------------------------------------

class _LazyEngine:
    """Proxy that forwards attribute access to the real Engine on first use."""

    def __getattr__(self, name: str):
        return getattr(get_engine(), name)

    def connect(self, *args, **kwargs):
        return get_engine().connect(*args, **kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return repr(get_engine())


class _LazySessionMaker:
    """Proxy that forwards calls to the real sessionmaker on first use."""

    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(get_session_local(), name)

    def __repr__(self) -> str:  # pragma: no cover
        return repr(get_session_local())


engine: Engine = _LazyEngine()  # type: ignore[assignment]
SessionLocal = _LazySessionMaker()


# ---------------------------------------------------------------------------
# get_db() — FastAPI dependency / generator
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy Session and guarantee it is closed afterwards.

    Usage as FastAPI dependency::

        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = get_session_local()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context-manager wrapper around get_db() for non-FastAPI callers."""
    yield from get_db()


# ---------------------------------------------------------------------------
# Health check helper
# ---------------------------------------------------------------------------
def check_db_connection() -> bool:
    """Return True if a basic SELECT 1 succeeds, False otherwise."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover
        return False

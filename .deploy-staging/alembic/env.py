"""Alembic environment for Amazon AI automation system.

This module is loaded by Alembic to configure the migration environment.
It reads DATABASE_URL from the environment (via src.config.settings) and
references Base.metadata from src.db.models for autogenerate support.
"""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import os
import sys
from logging.config import fileConfig
from importlib import import_module

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so that src.* imports resolve
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ---------------------------------------------------------------------------
# Import application models so Alembic autogenerate can detect them
# ---------------------------------------------------------------------------
from src.db.models import *  # noqa: F401,F403,E402

# Register pgvector type with Alembic comparison if available
try:
    import_module("pgvector.sqlalchemy")
except Exception:
    pass  # pgvector not installed; migrations can still be generated without type comparison

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging if it exists
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Override sqlalchemy.url with the value from the environment / settings
# ---------------------------------------------------------------------------
def _get_db_url() -> str:
    """Read DATABASE_URL from environment or from src.config.settings."""
    # Prefer direct env var (works in Docker / CI without importing settings)
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # Fall back to pydantic-settings
    from src.config import settings  # noqa: PLC0415

    return settings.DATABASE_URL


config.set_main_option("sqlalchemy.url", _get_db_url())

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations (alembic upgrade head --sql)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an
    Engine is acceptable here as well.  By skipping the Engine creation we
    don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (alembic upgrade head)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

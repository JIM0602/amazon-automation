"""Unit tests for src.db — models, connection pool, and session helpers.

All tests use mocks and do NOT require a real PostgreSQL instance.
Run with: pytest tests/test_db.py --mock-external-apis -v
"""

import uuid
from datetime import datetime, date
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import types

import pytest


# ---------------------------------------------------------------------------
# Fixture: stub out pgvector so models.py can be imported without the package
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def stub_pgvector(monkeypatch):
    """Inject a minimal pgvector.sqlalchemy stub before models are imported."""
    from sqlalchemy.types import UserDefinedType

    class _Vector(UserDefinedType):
        def __init__(self, dim: int):
            self.dim = dim

        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

        class comparator_factory(UserDefinedType.Comparator):
            pass

    # Create fake module hierarchy
    pgvector_mod = types.ModuleType("pgvector")
    pgvector_sa_mod = types.ModuleType("pgvector.sqlalchemy")
    pgvector_sa_mod.Vector = _Vector
    pgvector_mod.sqlalchemy = pgvector_sa_mod

    monkeypatch.setitem(sys.modules, "pgvector", pgvector_mod)
    monkeypatch.setitem(sys.modules, "pgvector.sqlalchemy", pgvector_sa_mod)
    yield


# ---------------------------------------------------------------------------
# Fixture: mock settings so connection.py doesn't need a real .env
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Provide a fake settings object with a SQLite in-memory URL for testing."""
    fake_settings = MagicMock()
    fake_settings.DATABASE_URL = "sqlite://"  # in-memory SQLite for model tests
    monkeypatch.setattr("src.config.settings", fake_settings)
    yield fake_settings


# ---------------------------------------------------------------------------
# Fixture: SQLite in-memory engine for ORM tests (no PostgreSQL needed)
# ---------------------------------------------------------------------------
@pytest.fixture()
def sqlite_engine(stub_pgvector):
    """Return a SQLite in-memory engine with all tables created."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    # Import models AFTER pgvector stub is in place
    from src.db.models import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite doesn't support Vector columns natively — we need to handle DDL
    # by catching the error or using a text-based column for testing purposes.
    # Since Vector is a UserDefinedType with get_col_spec returning "vector(...)",
    # SQLite will just ignore it as an unknown type, which is fine for testing.
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def sqlite_session(sqlite_engine):
    """Yield a SQLAlchemy Session connected to the in-memory SQLite DB."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


# ===========================================================================
# Model import tests
# ===========================================================================

class TestModelImports:
    """Verify all 10 ORM model classes are importable and correctly named."""

    def test_all_models_importable(self, stub_pgvector):
        from src.db.models import (
            Base,
            Document,
            DocumentChunk,
            Product,
            ProductSelection,
            AgentRun,
            AgentTask,
            ApprovalRequest,
            DailyReport,
            SystemConfig,
            AuditLog,
        )
        assert Base is not None
        assert Document is not None
        assert DocumentChunk is not None
        assert Product is not None
        assert ProductSelection is not None
        assert AgentRun is not None
        assert AgentTask is not None
        assert ApprovalRequest is not None
        assert DailyReport is not None
        assert SystemConfig is not None
        assert AuditLog is not None

    def test_model_table_names(self, stub_pgvector):
        from src.db.models import (
            Document, DocumentChunk, Product, ProductSelection,
            AgentRun, AgentTask, ApprovalRequest, DailyReport,
            SystemConfig, AuditLog,
        )
        assert Document.__tablename__ == "documents"
        assert DocumentChunk.__tablename__ == "document_chunks"
        assert Product.__tablename__ == "products"
        assert ProductSelection.__tablename__ == "product_selection"
        assert AgentRun.__tablename__ == "agent_runs"
        assert AgentTask.__tablename__ == "agent_tasks"
        assert ApprovalRequest.__tablename__ == "approval_requests"
        assert DailyReport.__tablename__ == "daily_reports"
        assert SystemConfig.__tablename__ == "system_config"
        assert AuditLog.__tablename__ == "audit_logs"

    def test_ten_tables_in_metadata(self, stub_pgvector):
        from src.db.models import Base
        table_names = set(Base.metadata.tables.keys())
        expected = {
            "documents", "document_chunks", "products", "product_selection",
            "agent_runs", "agent_tasks", "approval_requests", "daily_reports",
            "system_config", "audit_logs",
        }
        assert expected == table_names, f"Missing tables: {expected - table_names}"


# ===========================================================================
# Column / schema tests
# ===========================================================================

class TestDocumentModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import Document
        cols = {c.name for c in Document.__table__.columns}
        assert {"id", "title", "content", "source", "category", "embedding", "created_at"} <= cols

    def test_embedding_dim(self, stub_pgvector):
        from src.db.models import Document
        col = Document.__table__.columns["embedding"]
        # Vector stub stores dim attribute
        assert col.type.dim == 1536

    def test_repr(self, stub_pgvector):
        from src.db.models import Document
        doc = Document(id=uuid.uuid4(), title="Test Doc")
        assert "Test Doc" in repr(doc)


class TestDocumentChunkModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import DocumentChunk
        cols = {c.name for c in DocumentChunk.__table__.columns}
        assert {"id", "document_id", "chunk_text", "chunk_embedding", "chunk_index", "created_at"} <= cols

    def test_fk_to_documents(self, stub_pgvector):
        from src.db.models import DocumentChunk
        fks = {fk.target_fullname for fk in DocumentChunk.__table__.foreign_keys}
        assert "documents.id" in fks


class TestProductModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import Product
        cols = {c.name for c in Product.__table__.columns}
        assert {"id", "sku", "name", "asin", "keywords", "status", "created_at"} <= cols

    def test_asin_nullable(self, stub_pgvector):
        from src.db.models import Product
        assert Product.__table__.columns["asin"].nullable is True

    def test_keywords_json(self, stub_pgvector):
        from src.db.models import Product
        from sqlalchemy import JSON
        assert isinstance(Product.__table__.columns["keywords"].type, JSON)


class TestProductSelectionModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import ProductSelection
        cols = {c.name for c in ProductSelection.__table__.columns}
        assert {"id", "candidate_asin", "reason", "score", "agent_run_id", "created_at"} <= cols

    def test_fk_to_agent_runs(self, stub_pgvector):
        from src.db.models import ProductSelection
        fks = {fk.target_fullname for fk in ProductSelection.__table__.foreign_keys}
        assert "agent_runs.id" in fks


class TestAgentRunModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import AgentRun
        cols = {c.name for c in AgentRun.__table__.columns}
        assert {"id", "agent_type", "status", "input_summary", "output_summary",
                "cost_usd", "started_at", "finished_at"} <= cols

    def test_finished_at_nullable(self, stub_pgvector):
        from src.db.models import AgentRun
        assert AgentRun.__table__.columns["finished_at"].nullable is True


class TestAgentTaskModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import AgentTask
        cols = {c.name for c in AgentTask.__table__.columns}
        assert {"id", "agent_type", "trigger_type", "payload", "status", "scheduled_at"} <= cols


class TestApprovalRequestModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import ApprovalRequest
        cols = {c.name for c in ApprovalRequest.__table__.columns}
        assert {"id", "agent_run_id", "action_type", "payload", "status", "approved_by", "created_at"} <= cols

    def test_approved_by_nullable(self, stub_pgvector):
        from src.db.models import ApprovalRequest
        assert ApprovalRequest.__table__.columns["approved_by"].nullable is True


class TestDailyReportModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import DailyReport
        cols = {c.name for c in DailyReport.__table__.columns}
        assert {"id", "report_date", "content_json", "sent_at"} <= cols

    def test_sent_at_nullable(self, stub_pgvector):
        from src.db.models import DailyReport
        assert DailyReport.__table__.columns["sent_at"].nullable is True


class TestSystemConfigModel:
    def test_key_is_primary_key(self, stub_pgvector):
        from src.db.models import SystemConfig
        pk_cols = [c.name for c in SystemConfig.__table__.primary_key]
        assert "key" in pk_cols

    def test_columns_present(self, stub_pgvector):
        from src.db.models import SystemConfig
        cols = {c.name for c in SystemConfig.__table__.columns}
        assert {"key", "value", "updated_at"} <= cols


class TestAuditLogModel:
    def test_columns_present(self, stub_pgvector):
        from src.db.models import AuditLog
        cols = {c.name for c in AuditLog.__table__.columns}
        assert {"id", "action", "actor", "pre_state", "post_state", "created_at"} <= cols

    def test_pre_post_state_nullable(self, stub_pgvector):
        from src.db.models import AuditLog
        assert AuditLog.__table__.columns["pre_state"].nullable is True
        assert AuditLog.__table__.columns["post_state"].nullable is True

    def test_no_agent_type_column(self, stub_pgvector):
        """audit_logs should NOT have agent_type (common mistake)."""
        from src.db.models import AuditLog
        cols = {c.name for c in AuditLog.__table__.columns}
        assert "agent_type" not in cols


# ===========================================================================
# CRUD round-trip tests (SQLite in-memory — no real PostgreSQL)
# ===========================================================================

class TestCRUDRoundTrip:
    """Test that models can be inserted and queried via SQLite in-memory."""

    def test_insert_and_query_document(self, sqlite_session):
        from src.db.models import Document
        doc = Document(
            id=uuid.uuid4(),
            title="Hello World",
            content="Some content",
            source="test",
            category="unit-test",
        )
        sqlite_session.add(doc)
        sqlite_session.commit()

        result = sqlite_session.query(Document).filter_by(title="Hello World").first()
        assert result is not None
        assert result.content == "Some content"

    def test_insert_and_query_agent_run(self, sqlite_session):
        from src.db.models import AgentRun
        run = AgentRun(
            id=uuid.uuid4(),
            agent_type="product_selection",
            status="success",
        )
        sqlite_session.add(run)
        sqlite_session.commit()

        result = sqlite_session.query(AgentRun).filter_by(agent_type="product_selection").first()
        assert result is not None
        assert result.status == "success"

    def test_insert_and_query_system_config(self, sqlite_session):
        from src.db.models import SystemConfig
        cfg = SystemConfig(key="max_daily_cost", value={"usd": 50.0})
        sqlite_session.add(cfg)
        sqlite_session.commit()

        result = sqlite_session.query(SystemConfig).filter_by(key="max_daily_cost").first()
        assert result is not None
        assert result.value == {"usd": 50.0}

    def test_insert_and_query_audit_log(self, sqlite_session):
        from src.db.models import AuditLog
        log = AuditLog(
            id=uuid.uuid4(),
            action="product.created",
            actor="system",
            pre_state=None,
            post_state={"sku": "TEST-001"},
        )
        sqlite_session.add(log)
        sqlite_session.commit()

        result = sqlite_session.query(AuditLog).filter_by(action="product.created").first()
        assert result is not None
        assert result.actor == "system"


# ===========================================================================
# Connection pool tests (fully mocked — no real DB)
# ===========================================================================

def _reset_connection_cache():
    """Reset the lazy-init cache inside src.db.connection so each test starts fresh."""
    import src.db.connection as conn_mod
    conn_mod._engine = None
    conn_mod._SessionLocal = None


class TestConnectionModule:
    """Verify connection.py wiring without a real PostgreSQL connection."""

    def test_get_database_url_reads_from_settings(self, mock_settings):
        """_get_database_url() should delegate to settings.DATABASE_URL."""
        mock_settings.DATABASE_URL = "sqlite://"  # use sqlite to avoid psycopg2 import
        import src.db.connection as conn_mod
        url = conn_mod._get_database_url()
        assert url == "sqlite://"

    def test_engine_is_proxy_object(self, stub_pgvector, mock_settings):
        """engine at module level is the _LazyEngine proxy (not None)."""
        import src.db.connection as conn_mod
        assert conn_mod.engine is not None

    def test_get_engine_returns_real_engine(self, stub_pgvector, mock_settings):
        """get_engine() should lazily build and return a real SQLAlchemy Engine."""
        from sqlalchemy.engine import Engine
        _reset_connection_cache()
        import src.db.connection as conn_mod
        eng = conn_mod.get_engine()
        assert isinstance(eng, Engine)

    def test_get_session_local_returns_sessionmaker(self, stub_pgvector, mock_settings):
        """get_session_local() should return a sessionmaker bound to the engine."""
        from sqlalchemy.orm import sessionmaker
        _reset_connection_cache()
        import src.db.connection as conn_mod
        sm = conn_mod.get_session_local()
        assert isinstance(sm, sessionmaker)

    def test_get_db_yields_session_and_closes(self, stub_pgvector, mock_settings):
        """get_db() generator should yield a session and close it on exhaustion."""
        _reset_connection_cache()
        import src.db.connection as conn_mod

        gen = conn_mod.get_db()
        session = next(gen)
        assert session is not None
        # Exhaust generator (triggers finally/close)
        try:
            next(gen)
        except StopIteration:
            pass

    def test_check_db_connection_returns_bool(self, stub_pgvector, mock_settings):
        """check_db_connection() should return True for SQLite in-memory."""
        _reset_connection_cache()
        import src.db.connection as conn_mod
        result = conn_mod.check_db_connection()
        assert isinstance(result, bool)
        assert result is True  # SQLite in-memory always succeeds


# ===========================================================================
# Package __init__ re-export test
# ===========================================================================

class TestPackageInit:
    def test_package_exports_base_and_models(self, stub_pgvector, mock_settings):
        """src.db.__init__ should re-export all 10 models + connection objects."""
        _reset_connection_cache()
        import src.db as db_pkg

        expected_exports = [
            "Base", "Document", "DocumentChunk", "Product", "ProductSelection",
            "AgentRun", "AgentTask", "ApprovalRequest", "DailyReport",
            "SystemConfig", "AuditLog", "engine", "SessionLocal", "get_db",
        ]
        for name in expected_exports:
            assert hasattr(db_pkg, name), f"src.db missing export: {name}"

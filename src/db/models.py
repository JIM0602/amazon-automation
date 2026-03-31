"""SQLAlchemy ORM models for the Amazon AI automation system.

Tables:
    documents           — knowledge base documents with vector embeddings
    document_chunks     — chunked text slices of documents with embeddings
    products            — tracked Amazon products / SKUs
    product_selection   — AI-selected product candidates
    agent_runs          — execution history for every agent invocation
    agent_tasks         — scheduled / queued agent task queue
    approval_requests   — human-in-the-loop approval workflow items
    daily_reports       — daily digest reports sent via Feishu
    system_config       — key-value store for runtime configuration
    audit_logs          — immutable audit trail for all state changes
"""

import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

# pgvector type — imported lazily so tests can mock it
try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover — pgvector not installed in test env
    from sqlalchemy.types import UserDefinedType

    class Vector(UserDefinedType):  # type: ignore[no-redef]
        """Fallback stub when pgvector is not installed."""

        def __init__(self, dim: int):
            self.dim = dim

        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

        class comparator_factory(UserDefinedType.Comparator):
            pass


Base = declarative_base()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small


def _uuid_pk():
    """Shorthand: UUID primary key defaulting to a new UUID4."""
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now_utc():
    """Server-side default for created_at / updated_at columns."""
    return func.now()


# ---------------------------------------------------------------------------
# Table 1: documents
# ---------------------------------------------------------------------------
class Document(Base):
    """Knowledge base documents ingested from various sources."""

    __tablename__ = "documents"

    id = _uuid_pk()
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(256), nullable=False)
    category = Column(String(128), nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document id={self.id!s} title={self.title!r}>"


# ---------------------------------------------------------------------------
# Table 2: document_chunks
# ---------------------------------------------------------------------------
class DocumentChunk(Base):
    """Chunked slices of documents, each with its own embedding vector."""

    __tablename__ = "document_chunks"

    id = _uuid_pk()
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_text = Column(Text, nullable=False)
    chunk_embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id!s} doc={self.document_id!s} idx={self.chunk_index}>"


# ---------------------------------------------------------------------------
# Table 3: products
# ---------------------------------------------------------------------------
class Product(Base):
    """Tracked Amazon products / internal SKUs."""

    __tablename__ = "products"

    id = _uuid_pk()
    sku = Column(String(128), nullable=False, unique=True, index=True)
    name = Column(String(512), nullable=False)
    asin = Column(String(16), nullable=True, index=True)
    keywords = Column(JSON, nullable=True)  # list[str]
    status = Column(String(64), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    def __repr__(self) -> str:
        return f"<Product id={self.id!s} sku={self.sku!r} asin={self.asin!r}>"


# ---------------------------------------------------------------------------
# Table 4: product_selection
# ---------------------------------------------------------------------------
class ProductSelection(Base):
    """AI-generated product selection candidates."""

    __tablename__ = "product_selection"

    id = _uuid_pk()
    candidate_asin = Column(String(16), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    agent_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    # Relationships
    agent_run = relationship("AgentRun", back_populates="product_selections")

    def __repr__(self) -> str:
        return f"<ProductSelection id={self.id!s} asin={self.candidate_asin!r} score={self.score}>"


# ---------------------------------------------------------------------------
# Table 5: agent_runs
# ---------------------------------------------------------------------------
class AgentRun(Base):
    """Execution history for every agent invocation."""

    __tablename__ = "agent_runs"

    id = _uuid_pk()
    agent_type = Column(String(128), nullable=False, index=True)
    status = Column(String(64), nullable=False, default="running")  # running/success/failed
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    cost_usd = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    product_selections = relationship("ProductSelection", back_populates="agent_run")
    approval_requests = relationship("ApprovalRequest", back_populates="agent_run")

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id!s} type={self.agent_type!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Table 6: agent_tasks
# ---------------------------------------------------------------------------
class AgentTask(Base):
    """Scheduled / queued tasks that trigger agent execution."""

    __tablename__ = "agent_tasks"

    id = _uuid_pk()
    agent_type = Column(String(128), nullable=False, index=True)
    trigger_type = Column(String(64), nullable=False)  # cron / event / manual
    payload = Column(JSON, nullable=True)
    status = Column(String(64), nullable=False, default="pending")  # pending/running/done/failed
    scheduled_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<AgentTask id={self.id!s} type={self.agent_type!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Table 7: approval_requests
# ---------------------------------------------------------------------------
class ApprovalRequest(Base):
    """Human-in-the-loop approval workflow items."""

    __tablename__ = "approval_requests"

    id = _uuid_pk()
    agent_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String(64), nullable=False, default="pending")  # pending/approved/rejected
    approved_by = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    # Relationships
    agent_run = relationship("AgentRun", back_populates="approval_requests")

    def __repr__(self) -> str:
        return f"<ApprovalRequest id={self.id!s} action={self.action_type!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Table 8: daily_reports
# ---------------------------------------------------------------------------
class DailyReport(Base):
    """Daily digest reports generated and sent via Feishu."""

    __tablename__ = "daily_reports"

    id = _uuid_pk()
    report_date = Column(Date, nullable=False, unique=True, index=True)
    content_json = Column(JSON, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<DailyReport id={self.id!s} date={self.report_date!s}>"


# ---------------------------------------------------------------------------
# Table 9: system_config
# ---------------------------------------------------------------------------
class SystemConfig(Base):
    """Key-value store for runtime configuration.  key is the PK."""

    __tablename__ = "system_config"

    key = Column(String(256), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=_now_utc(),
        onupdate=_now_utc(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SystemConfig key={self.key!r}>"


# ---------------------------------------------------------------------------
# Table 10: audit_logs
# ---------------------------------------------------------------------------
class AuditLog(Base):
    """Immutable audit trail for all state-changing operations."""

    __tablename__ = "audit_logs"

    id = _uuid_pk()
    action = Column(String(256), nullable=False, index=True)
    actor = Column(String(256), nullable=False)
    pre_state = Column(JSON, nullable=True)
    post_state = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id!s} action={self.action!r} actor={self.actor!r}>"

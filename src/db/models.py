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
    decisions           — T25 可追踪、可回滚的决策状态机记录
"""

import uuid
from datetime import datetime, date
from importlib import import_module
from typing import Any

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

from sqlalchemy.types import UserDefinedType

# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false


def _load_vector_type() -> Any:
    """Load pgvector if available, otherwise use a local fallback type."""
    try:
        return import_module("pgvector.sqlalchemy").Vector
    except Exception:  # pragma: no cover — pgvector may not be installed locally
        class Vector(UserDefinedType[Any]):
            """Fallback stub when pgvector is not installed."""

            def __init__(self, dim: int):
                self.dim = dim

            def get_col_spec(self, **kw: Any):
                return f"vector({self.dim})"

            class comparator_factory(UserDefinedType.Comparator[Any]):
                pass

        return Vector


Vector = _load_vector_type()


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
    return text("CURRENT_TIMESTAMP")


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

    # --- T24: RAG 元数据增强新增列 ---
    doc_type = Column(String(64), nullable=True, server_default="other", index=True)
    version = Column(String(64), nullable=True)
    effective_date = Column(Date, nullable=True)
    expires_date = Column(Date, nullable=True)
    priority = Column(Integer, nullable=False, server_default="5")

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

    # --- T24: RAG 元数据增强新增列（冗余字段，加速过滤，避免每次 JOIN）---
    doc_type = Column(String(64), nullable=True, server_default="other", index=True)

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
    brand_analytics_keywords = Column(JSON, nullable=True)
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
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=True,
    )
    is_chat_mode = Column(Boolean, default=False)
    status = Column(String(64), nullable=False, default="running")  # running/success/failed
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    cost_usd = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    result_json = Column(JSON, nullable=True)  # structured result dict (added T4)

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


# ---------------------------------------------------------------------------
# Table 11: llm_cache
# ---------------------------------------------------------------------------
class LlmCache(Base):
    """LLM 响应缓存，用于降低重复请求的 Token 成本。

    缓存键基于 prompt + model + 参数的 SHA-256 哈希计算。
    默认 TTL 为 24 小时，过期后自动失效（通过 expires_at 字段控制）。
    """

    __tablename__ = "llm_cache"

    cache_key = Column(String(64), primary_key=True)       # SHA-256 hex（64位）
    prompt_hash = Column(String(64), nullable=False, index=True)  # 仅消息内容哈希
    response_json = Column(JSON, nullable=False)           # 缓存的响应数据
    model = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    hit_count = Column(Integer, nullable=False, default=0)  # 命中次数

    def __repr__(self) -> str:
        return (
            f"<LlmCache key={self.cache_key[:16]!r}... model={self.model!r} "
            f"hits={self.hit_count} expires={self.expires_at!s}>"
        )


# ---------------------------------------------------------------------------
# Table 12: decisions  (T25 决策状态机)
# ---------------------------------------------------------------------------
class Decision(Base):
    """可追踪、可回滚的决策记录。

    状态流转：
        DRAFT → PENDING_APPROVAL → APPROVED → EXECUTING → SUCCEEDED
                                                        ↘ FAILED → ROLLED_BACK
                                ↘ REJECTED
    """

    __tablename__ = "decisions"

    id = _uuid_pk()
    decision_type = Column(String(128), nullable=False, index=True)   # pricing / advertising / listing 等
    agent_id = Column(String(256), nullable=False, index=True)         # 发起决策的 Agent
    payload = Column(JSON, nullable=False)                              # 决策内容
    status = Column(String(64), nullable=False, default="DRAFT", index=True)  # 当前状态
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=_now_utc(),
        nullable=False,
    )
    approved_by = Column(String(256), nullable=True)                   # 审批人
    approved_at = Column(DateTime(timezone=True), nullable=True)       # 审批时间
    executed_at = Column(DateTime(timezone=True), nullable=True)       # 执行时间
    result = Column(JSON, nullable=True)                               # 执行结果
    error_message = Column(Text, nullable=True)                        # 错误信息
    rollback_payload = Column(JSON, nullable=True)                     # 回滚数据

    def __repr__(self) -> str:
        return (
            f"<Decision id={self.id!s} type={self.decision_type!r} "
            f"status={self.status!r} agent={self.agent_id!r}>"
        )


# ---------------------------------------------------------------------------
# Table 13: conversations
# ---------------------------------------------------------------------------
class Conversation(Base):
    """Chat conversations grouped by user and agent type."""

    __tablename__ = "conversations"

    id = _uuid_pk()
    user_id = Column(String(256), nullable=False)
    agent_type = Column(String(128), nullable=False)
    title = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=_now_utc())
    metadata_json = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Conversation id={self.id!s} user_id={self.user_id!r} agent_type={self.agent_type!r}>"


# ---------------------------------------------------------------------------
# Table 14: chat_messages
# ---------------------------------------------------------------------------
class ChatMessage(Base):
    """Messages belonging to a conversation."""

    __tablename__ = "chat_messages"

    id = _uuid_pk()
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    conversation = relationship("Conversation", backref="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id!s} conversation_id={self.conversation_id!s} role={self.role!r}>"


# ---------------------------------------------------------------------------
# Table 15: keyword_libraries
# ---------------------------------------------------------------------------
class KeywordLibrary(Base):
    """Keyword research and categorization library."""

    __tablename__ = "keyword_libraries"

    id = _uuid_pk()
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True,
    )
    keyword = Column(String(512), nullable=False, index=True)
    search_volume = Column(Integer, nullable=True)
    relevance_tier = Column(String(32), nullable=True)
    source = Column(String(64), nullable=False)
    category = Column(String(128), nullable=True)
    monthly_rank = Column(Integer, nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    def __repr__(self) -> str:
        return f"<KeywordLibrary id={self.id!s} keyword={self.keyword!r} source={self.source!r}>"


# ---------------------------------------------------------------------------
# Table 16: ad_simulations
# ---------------------------------------------------------------------------
class AdSimulation(Base):
    """Stored ad campaign simulation results."""

    __tablename__ = "ad_simulations"

    id = _uuid_pk()
    campaign_id = Column(String(256), nullable=True)
    simulation_params = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    created_by = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    def __repr__(self) -> str:
        return f"<AdSimulation id={self.id!s} campaign_id={self.campaign_id!r}>"


# ---------------------------------------------------------------------------
# Table 17: ad_optimization_logs
# ---------------------------------------------------------------------------
class AdOptimizationLog(Base):
    """Change log for ad optimization actions."""

    __tablename__ = "ad_optimization_logs"

    id = _uuid_pk()
    campaign_id = Column(String(256), nullable=True)
    action_type = Column(String(128), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    applied = Column(Boolean, nullable=False, default=False)
    approved_by = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    def __repr__(self) -> str:
        return f"<AdOptimizationLog id={self.id!s} campaign_id={self.campaign_id!r} action={self.action_type!r}>"


# ---------------------------------------------------------------------------
# Table 18: kb_review_queue
# ---------------------------------------------------------------------------
class KBReviewQueue(Base):
    """Queue for content requiring knowledge-base review."""

    __tablename__ = "kb_review_queue"

    id = _uuid_pk()
    content = Column(Text, nullable=False)
    source = Column(String(256), nullable=True)
    agent_type = Column(String(128), nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    reviewer_id = Column(String(256), nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<KBReviewQueue id={self.id!s} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Table 19: auditor_logs
# ---------------------------------------------------------------------------
class AuditorLog(Base):
    """Audit findings emitted by automated auditors."""

    __tablename__ = "auditor_logs"

    id = _uuid_pk()
    agent_type = Column(String(128), nullable=False)
    agent_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id"),
        nullable=True,
    )
    severity = Column(String(32), nullable=False)
    finding = Column(Text, nullable=False)
    auto_action = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)

    def __repr__(self) -> str:
        return f"<AuditorLog id={self.id!s} agent_type={self.agent_type!r} severity={self.severity!r}>"


# ---------------------------------------------------------------------------
# Table 20: users
# ---------------------------------------------------------------------------
class User(Base):
    """Application users for authentication and authorization."""

    __tablename__ = "users"

    id = _uuid_pk()
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="operator")
    display_name = Column(String(128), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=_now_utc())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=_now_utc(), onupdate=_now_utc())


# ---------------------------------------------------------------------------
# Table 21: agent_configs
# ---------------------------------------------------------------------------
class AgentConfig(Base):
    """Agent 中文名与显示配置，供前端读取。"""

    __tablename__ = "agent_configs"

    agent_type = Column(String(64), primary_key=True)
    display_name_cn = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    visible_roles = Column(JSON, nullable=True)  # ["boss", "operator"] 等
    sort_order = Column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<AgentConfig agent_type={self.agent_type!r} display_name_cn={self.display_name_cn!r}>"


# ---------------------------------------------------------------------------
# Phase 1: sales, inventory and ads management tables
# ---------------------------------------------------------------------------
class Sku(Base):
    """SKU dimension table for phase-1 dashboard aggregation."""

    __tablename__ = "skus"

    id = _uuid_pk()
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True)
    sku = Column(String(128), nullable=False, unique=True, index=True)
    asin = Column(String(32), nullable=True, index=True)
    marketplace = Column(String(32), nullable=False, default="US", index=True)
    image_url = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=_now_utc(), onupdate=_now_utc(), nullable=False)


class SalesDaily(Base):
    """Daily sales fact table, grain: sku + date."""

    __tablename__ = "sales_daily"
    __table_args__ = (
        UniqueConstraint("date", "sku", "marketplace", "snapshot_type", name="uq_sales_daily_date_sku_marketplace_snapshot"),
    )

    id = _uuid_pk()
    date = Column(Date, nullable=False, index=True)
    sku = Column(String(128), nullable=False, index=True)
    asin = Column(String(32), nullable=True, index=True)
    marketplace = Column(String(32), nullable=False, default="US", index=True)
    sales_amount = Column(Float, nullable=False, default=0.0)
    order_count = Column(Integer, nullable=False, default=0)
    units_sold = Column(Integer, nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="USD")
    source = Column(String(64), nullable=False, default="sp_api")
    snapshot_type = Column(String(16), nullable=False, default="t0")
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)


class InventoryDaily(Base):
    """Daily inventory fact table, grain: sku + date."""

    __tablename__ = "inventory_daily"
    __table_args__ = (
        UniqueConstraint("date", "sku", name="uq_inventory_daily_date_sku"),
    )

    id = _uuid_pk()
    date = Column(Date, nullable=False, index=True)
    sku = Column(String(128), nullable=False, index=True)
    asin = Column(String(32), nullable=True, index=True)
    fba_available = Column(Integer, nullable=False, default=0)
    inbound_quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    estimated_days = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)


class AdsCampaign(Base):
    """Amazon Ads campaign cache."""

    __tablename__ = "ads_campaigns"

    id = _uuid_pk()
    campaign_id = Column(String(64), nullable=False, unique=True, index=True)
    portfolio_id = Column(String(64), nullable=True, index=True)
    campaign_name = Column(String(512), nullable=False)
    ad_type = Column(String(32), nullable=False, default="SP", index=True)
    state = Column(String(32), nullable=False, default="enabled", index=True)
    serving_status = Column(String(64), nullable=True, index=True)
    daily_budget = Column(Float, nullable=True)
    budget_currency = Column(String(8), nullable=False, default="USD")
    bidding_strategy = Column(String(128), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSON, nullable=True)


class AdsAdGroup(Base):
    """Amazon Ads ad group cache."""

    __tablename__ = "ads_ad_groups"

    id = _uuid_pk()
    ad_group_id = Column(String(64), nullable=False, unique=True, index=True)
    campaign_id = Column(String(64), nullable=False, index=True)
    group_name = Column(String(512), nullable=False)
    state = Column(String(32), nullable=False, default="enabled", index=True)
    default_bid = Column(Float, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSON, nullable=True)


class AdsTargeting(Base):
    """Amazon Ads keyword/product targeting cache."""

    __tablename__ = "ads_targeting"

    id = _uuid_pk()
    targeting_id = Column(String(64), nullable=False, unique=True, index=True)
    campaign_id = Column(String(64), nullable=False, index=True)
    ad_group_id = Column(String(64), nullable=True, index=True)
    keyword_text = Column(String(512), nullable=True, index=True)
    match_type = Column(String(64), nullable=True)
    state = Column(String(32), nullable=False, default="enabled", index=True)
    bid = Column(Float, nullable=True)
    suggested_bid = Column(Float, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSON, nullable=True)


class AdsSearchTerm(Base):
    """Amazon Ads search term report facts."""

    __tablename__ = "ads_search_terms"

    id = _uuid_pk()
    date = Column(Date, nullable=False, index=True)
    campaign_id = Column(String(64), nullable=False, index=True)
    ad_group_id = Column(String(64), nullable=True, index=True)
    search_term = Column(String(512), nullable=False, index=True)
    targeting_keyword = Column(String(512), nullable=True)
    match_type = Column(String(64), nullable=True)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    cost = Column(Float, nullable=False, default=0.0)
    ad_orders = Column(Integer, nullable=False, default=0)
    ad_sales = Column(Float, nullable=False, default=0.0)
    acos = Column(Float, nullable=False, default=0.0)
    cvr = Column(Float, nullable=False, default=0.0)
    suggested_bid = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)


class AdsNegativeTargeting(Base):
    """Amazon Ads negative targeting cache."""

    __tablename__ = "ads_negative_targeting"

    id = _uuid_pk()
    negative_id = Column(String(64), nullable=True, unique=True, index=True)
    campaign_id = Column(String(64), nullable=False, index=True)
    ad_group_id = Column(String(64), nullable=True, index=True)
    keyword_text = Column(String(512), nullable=False, index=True)
    match_type = Column(String(64), nullable=True)
    state = Column(String(32), nullable=False, default="enabled", index=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSON, nullable=True)


class AdsMetricsDaily(Base):
    """Daily ads performance facts, grain: campaign/ad_group/date."""

    __tablename__ = "ads_metrics_daily"
    __table_args__ = (
        UniqueConstraint("date", "campaign_id", "ad_group_id", "sku", name="uq_ads_metrics_daily_grain"),
    )

    id = _uuid_pk()
    date = Column(Date, nullable=False, index=True)
    campaign_id = Column(String(64), nullable=False, index=True)
    ad_group_id = Column(String(64), nullable=True, index=True)
    portfolio_id = Column(String(64), nullable=True, index=True)
    sku = Column(String(128), nullable=True, index=True)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    ctr = Column(Float, nullable=False, default=0.0)
    cost = Column(Float, nullable=False, default=0.0)
    cpc = Column(Float, nullable=False, default=0.0)
    ad_orders = Column(Integer, nullable=False, default=0)
    ad_units = Column(Integer, nullable=False, default=0)
    ad_sales = Column(Float, nullable=False, default=0.0)
    acos = Column(Float, nullable=False, default=0.0)
    tacos = Column(Float, nullable=False, default=0.0)
    cvr = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)


class AdsActionLog(Base):
    """Audit log for every Amazon Ads write attempt."""

    __tablename__ = "ads_action_logs"

    id = _uuid_pk()
    action_key = Column(String(128), nullable=False, index=True)
    target_type = Column(String(64), nullable=False, index=True)
    target_id = Column(String(128), nullable=False, index=True)
    operator_username = Column(String(128), nullable=False, index=True)
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    success = Column(Boolean, nullable=False, default=False, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)


class SyncJob(Base):
    """Execution log for data sync jobs."""

    __tablename__ = "sync_jobs"

    id = _uuid_pk()
    job_name = Column(String(128), nullable=False, index=True)
    job_type = Column(String(64), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=_now_utc(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="running", index=True)
    records_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    extra_payload = Column(JSON, nullable=True)

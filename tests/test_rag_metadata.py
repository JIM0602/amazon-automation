"""
T24 RAG 元数据增强单元测试。

覆盖范围：
  1. Pydantic 模型（DocumentMetadata / ChunkMetadata）字段验证
  2. DocumentProcessor.detect_doc_type() 类型推断
  3. DocumentProcessor.chunk_document() 元数据传递
  4. RAGEngine.ingest_chunks() 写入 doc_type
  5. RAGEngine.search() 元数据过滤参数（doc_type / date_range）
  6. ORM 模型（Document / DocumentChunk）新增列
"""

import sys
import uuid
from datetime import date
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 注入 openai / langchain stub（防止 ModuleNotFoundError）
# ---------------------------------------------------------------------------

def _inject_stubs():
    if "openai" not in sys.modules:
        stub = ModuleType("openai")
        stub.OpenAI = MagicMock
        sys.modules["openai"] = stub

    if "langchain_openai" not in sys.modules:
        lc_stub = ModuleType("langchain_openai")
        lc_stub.ChatOpenAI = MagicMock
        sys.modules["langchain_openai"] = lc_stub

    if "langchain" not in sys.modules:
        sys.modules["langchain"] = ModuleType("langchain")

    if "langchain.schema" not in sys.modules:
        schema = ModuleType("langchain.schema")
        schema.HumanMessage = MagicMock
        schema.SystemMessage = MagicMock
        sys.modules["langchain.schema"] = schema


_inject_stubs()


# ---------------------------------------------------------------------------
# 辅助：创建 RAGEngine 实例（绕过 settings）
# ---------------------------------------------------------------------------

def _make_engine():
    _inject_stubs()
    from src.knowledge_base.rag_engine import RAGEngine

    engine = RAGEngine.__new__(RAGEngine)
    engine._api_key = "sk-test"
    engine._model = "gpt-4o-mini"
    engine._openai_client = MagicMock()
    return engine


# ===========================================================================
# 1. Pydantic 模型测试
# ===========================================================================

class TestDocumentMetadata:
    """测试 DocumentMetadata Pydantic 模型。"""

    def test_required_fields(self):
        """source / title / category 是必填字段。"""
        from src.knowledge_base.models import DocumentMetadata

        meta = DocumentMetadata(
            source="s3://bucket/doc.pdf",
            title="Amazon广告指南",
            category="广告策略",
        )
        assert meta.source == "s3://bucket/doc.pdf"
        assert meta.title == "Amazon广告指南"
        assert meta.category == "广告策略"

    def test_default_values(self):
        """验证各字段的默认值。"""
        from src.knowledge_base.models import DocumentMetadata

        meta = DocumentMetadata(source="x", title="t", category="c")
        assert meta.doc_type == "other"
        assert meta.version is None
        assert meta.effective_date is None
        assert meta.expires_date is None
        assert meta.priority == 5

    def test_doc_type_valid_values(self):
        """DOC_TYPE 只接受合法值。"""
        from src.knowledge_base.models import DocumentMetadata, DOC_TYPE_VALUES

        for dt in DOC_TYPE_VALUES:
            meta = DocumentMetadata(source="s", title="t", category="c", doc_type=dt)
            assert meta.doc_type == dt

    def test_doc_type_invalid_raises(self):
        """非法 doc_type 应抛出验证错误。"""
        from src.knowledge_base.models import DocumentMetadata
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DocumentMetadata(source="s", title="t", category="c", doc_type="invalid_type")

    def test_priority_range(self):
        """priority 必须在 1-10 之间。"""
        from src.knowledge_base.models import DocumentMetadata
        from pydantic import ValidationError

        # 合法边界
        DocumentMetadata(source="s", title="t", category="c", priority=1)
        DocumentMetadata(source="s", title="t", category="c", priority=10)

        # 越界
        with pytest.raises(ValidationError):
            DocumentMetadata(source="s", title="t", category="c", priority=0)
        with pytest.raises(ValidationError):
            DocumentMetadata(source="s", title="t", category="c", priority=11)

    def test_effective_date_field(self):
        """验证 effective_date / expires_date 正常接受 date 类型。"""
        from src.knowledge_base.models import DocumentMetadata

        meta = DocumentMetadata(
            source="s",
            title="t",
            category="c",
            effective_date=date(2025, 1, 1),
            expires_date=date(2026, 12, 31),
        )
        assert meta.effective_date == date(2025, 1, 1)
        assert meta.expires_date == date(2026, 12, 31)


class TestChunkMetadata:
    """测试 ChunkMetadata，验证继承与新增字段。"""

    def test_inherits_document_metadata(self):
        """ChunkMetadata 应继承 DocumentMetadata 的所有字段。"""
        from src.knowledge_base.models import ChunkMetadata

        chunk = ChunkMetadata(
            source="s",
            title="t",
            category="c",
            doc_type="tutorial",
            chunk_index=3,
            chunk_strategy="paragraph",
        )
        # 继承字段
        assert chunk.source == "s"
        assert chunk.doc_type == "tutorial"
        # 新增字段
        assert chunk.chunk_index == 3
        assert chunk.chunk_strategy == "paragraph"

    def test_chunk_index_default(self):
        """chunk_index 默认 0。"""
        from src.knowledge_base.models import ChunkMetadata

        chunk = ChunkMetadata(source="s", title="t", category="c")
        assert chunk.chunk_index == 0

    def test_chunk_strategy_values(self):
        """chunk_strategy 支持 paragraph / heading / fixed。"""
        from src.knowledge_base.models import ChunkMetadata

        for strategy in ("paragraph", "heading", "fixed"):
            chunk = ChunkMetadata(
                source="s", title="t", category="c", chunk_strategy=strategy
            )
            assert chunk.chunk_strategy == strategy


# ===========================================================================
# 2. DocumentProcessor.detect_doc_type() 测试
# ===========================================================================

class TestDetectDocType:
    """测试 detect_doc_type() 文档类型推断。"""

    @pytest.fixture
    def processor(self):
        from src.knowledge_base.document_processor import DocumentProcessor
        return DocumentProcessor()

    def test_detect_tutorial_from_content(self, processor):
        """含'操作步骤'关键词的内容应识别为 tutorial。"""
        content = "本文档介绍操作步骤，帮助用户完成安装与配置方法。"
        assert processor.detect_doc_type(content) == "tutorial"

    def test_detect_rule_from_content(self, processor):
        """含'政策'关键词应识别为 rule。"""
        content = "以下为亚马逊卖家合规政策，违反本规定将面临账户封禁。"
        assert processor.detect_doc_type(content) == "rule"

    def test_detect_faq_from_content(self, processor):
        """含'FAQ'关键词应识别为 faq。"""
        content = "FAQ: 常见问题解答。Q1: 如何注册卖家账号？"
        assert processor.detect_doc_type(content) == "faq"

    def test_detect_report_from_content(self, processor):
        """含'分析报告'关键词应识别为 report。"""
        content = "2025年度亚马逊市场分析报告，数据分析显示跨境电商持续增长。"
        assert processor.detect_doc_type(content) == "report"

    def test_detect_guide_from_title(self, processor):
        """标题含'指南'应识别为 guide。"""
        assert processor.detect_doc_type("无特殊关键词内容", title="亚马逊运营最佳实践指南") == "guide"

    def test_detect_other_when_no_match(self, processor):
        """无匹配关键词时返回 'other'。"""
        content = "这是一段完全随机的文字，没有任何类型关键词。"
        assert processor.detect_doc_type(content, title="随机文档") == "other"

    def test_title_weighted_higher(self, processor):
        """标题关键词权重高于内容（相同命中数时标题优先）。"""
        # 标题包含'FAQ'，内容包含无类型关键词
        result = processor.detect_doc_type("普通内容文字", title="FAQ常见问题")
        assert result == "faq"


# ===========================================================================
# 3. DocumentProcessor.chunk_document() 元数据传递
# ===========================================================================

class TestChunkDocumentMetadata:
    """测试 chunk_document() 传递增强元数据。"""

    @pytest.fixture
    def processor(self):
        from src.knowledge_base.document_processor import DocumentProcessor
        return DocumentProcessor()

    def test_metadata_includes_doc_type(self, processor):
        """分块元数据应包含 doc_type 字段。"""
        doc = {
            "title": "广告投放教程",
            "content": "本教程介绍PPC广告操作步骤，帮助卖家优化广告投放。",
            "source": "ads_tutorial.md",
            "category": "广告策略",
        }
        chunks = processor.chunk_document(doc)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "doc_type" in chunk["metadata"]

    def test_metadata_doc_type_explicit(self, processor):
        """当 doc 字典中显式传入 doc_type，应直接使用而不推断。"""
        doc = {
            "title": "随便什么标题",
            "content": "随便什么内容",
            "source": "x.md",
            "category": "通用",
            "doc_type": "case_study",
        }
        chunks = processor.chunk_document(doc)
        for chunk in chunks:
            assert chunk["metadata"]["doc_type"] == "case_study"

    def test_metadata_priority_default(self, processor):
        """未传 priority 时，默认值为 5。"""
        doc = {
            "title": "T",
            "content": "内容",
            "source": "t.md",
            "category": "c",
        }
        chunks = processor.chunk_document(doc)
        for chunk in chunks:
            assert chunk["metadata"]["priority"] == 5

    def test_metadata_priority_custom(self, processor):
        """传入 priority 应在元数据中正确反映。"""
        doc = {
            "title": "T",
            "content": "内容",
            "source": "t.md",
            "category": "c",
            "priority": 8,
        }
        chunks = processor.chunk_document(doc)
        for chunk in chunks:
            assert chunk["metadata"]["priority"] == 8

    def test_metadata_version_effective_expires(self, processor):
        """version / effective_date / expires_date 应传递到元数据。"""
        doc = {
            "title": "T",
            "content": "内容",
            "source": "t.md",
            "category": "c",
            "version": "2.0",
            "effective_date": "2025-01-01",
            "expires_date": "2026-12-31",
        }
        chunks = processor.chunk_document(doc)
        for chunk in chunks:
            m = chunk["metadata"]
            assert m["version"] == "2.0"
            assert m["effective_date"] == "2025-01-01"
            assert m["expires_date"] == "2026-12-31"

    def test_chunk_strategy_default_paragraph(self, processor):
        """默认分块策略应为 'paragraph'。"""
        doc = {
            "title": "T",
            "content": "第一段。\n\n第二段。",
            "source": "t.md",
            "category": "c",
        }
        chunks = processor.chunk_document(doc)
        for chunk in chunks:
            assert chunk["metadata"]["chunk_strategy"] == "paragraph"


# ===========================================================================
# 4. RAGEngine.ingest_chunks() 写入 doc_type
# ===========================================================================

class TestIngestChunksDocType:
    """测试 ingest_chunks 传递 doc_type 到 DocumentChunk。"""

    @pytest.fixture
    def mock_embedding(self):
        return [0.1] * 1536

    def test_ingest_chunks_passes_doc_type(self, mock_embedding):
        """ingest_chunks 应将 metadata 中的 doc_type 传递给 DocumentChunk。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        chunks = [
            {
                "chunk_text": "关于广告规则和政策的内容",
                "chunk_index": 0,
                "metadata": {
                    "source": "ad_rules.md",
                    "category": "广告策略",
                    "title": "广告规则",
                    "doc_type": "rule",
                },
            }
        ]

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        created_chunks = []

        def capture_chunk(**kwargs):
            obj = MagicMock()
            obj._captured_kwargs = kwargs
            created_chunks.append(obj)
            return obj

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.DocumentChunk", side_effect=capture_chunk):
            mock_db.return_value = mock_cm
            result = engine.ingest_chunks(chunks)

        assert result == 1
        assert len(created_chunks) == 1
        assert created_chunks[0]._captured_kwargs.get("doc_type") == "rule"

    def test_ingest_chunks_defaults_doc_type_to_other(self, mock_embedding):
        """未传 doc_type 时应默认写入 'other'。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        chunks = [
            {
                "chunk_text": "某段内容",
                "chunk_index": 0,
                "metadata": {
                    "source": "x.md",
                    "category": "通用",
                    "title": "T",
                    # 没有 doc_type
                },
            }
        ]

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        created_chunks = []

        def capture_chunk(**kwargs):
            obj = MagicMock()
            obj._captured_kwargs = kwargs
            created_chunks.append(obj)
            return obj

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.DocumentChunk", side_effect=capture_chunk):
            mock_db.return_value = mock_cm
            result = engine.ingest_chunks(chunks)

        assert result == 1
        assert created_chunks[0]._captured_kwargs.get("doc_type") == "other"


# ===========================================================================
# 5. RAGEngine.search() 元数据过滤参数
# ===========================================================================

class TestSearchMetadataFilter:
    """测试 search() 的 doc_type 和 date_range 过滤参数。"""

    @pytest.fixture
    def mock_embedding(self):
        return [0.1] * 1536

    def _make_mock_row(self, chunk_text="text", chunk_index=0,
                       title="T", category="C", source="s.md",
                       distance=0.1, doc_type="other",
                       effective_date=None, expires_date=None, priority=5):
        """创建模拟数据库查询行（12列，与新 search() SELECT 列数一致）。"""
        return (
            str(uuid.uuid4()),  # 0: id
            chunk_text,         # 1: chunk_text
            chunk_index,        # 2: chunk_index
            str(uuid.uuid4()),  # 3: document_id
            title,              # 4: title
            category,           # 5: category
            source,             # 6: source
            distance,           # 7: distance
            doc_type,           # 8: doc_type
            effective_date,     # 9: effective_date
            expires_date,       # 10: expires_date
            priority,           # 11: priority
        )

    def test_search_doc_type_filter_adds_where_clause(self, mock_embedding):
        """传入 doc_type 时，SQL 应包含 dc.doc_type 过滤条件。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        captured_sqls = []

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        def capture_text(sql_str):
            captured_sqls.append(sql_str)
            return sql_str

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.text", side_effect=capture_text):
            mock_db.return_value = mock_cm
            engine.search("测试", doc_type="rule")

        assert len(captured_sqls) == 1
        assert "doc_type" in captured_sqls[0].lower()

    def test_search_date_range_adds_where_clause(self, mock_embedding):
        """传入 date_range 时，SQL 应包含 effective_date 相关过滤条件。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        captured_sqls = []

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        def capture_text(sql_str):
            captured_sqls.append(sql_str)
            return sql_str

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.text", side_effect=capture_text):
            mock_db.return_value = mock_cm
            engine.search("测试", date_range=(date(2025, 1, 1), date(2026, 12, 31)))

        assert len(captured_sqls) == 1
        assert "effective_date" in captured_sqls[0].lower()

    def test_search_no_filter_no_where_clause(self, mock_embedding):
        """无过滤参数时，SQL 不应有 WHERE 子句。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        captured_sqls = []

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        def capture_text(sql_str):
            captured_sqls.append(sql_str)
            return sql_str

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.text", side_effect=capture_text):
            mock_db.return_value = mock_cm
            engine.search("测试")

        assert len(captured_sqls) == 1
        assert "where" not in captured_sqls[0].lower()

    def test_search_returns_doc_type_in_metadata(self, mock_embedding):
        """search 结果中应包含 doc_type 元数据字段。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        mock_row = self._make_mock_row(
            chunk_text="广告规则详解",
            title="广告规则",
            category="广告策略",
            doc_type="rule",
            priority=8,
        )

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.text", return_value="sql"):
            mock_db.return_value = mock_cm
            results = engine.search("广告规则")

        assert len(results) == 1
        meta = results[0]["metadata"]
        assert meta["doc_type"] == "rule"
        assert meta["priority"] == 8

    def test_search_combined_category_and_doc_type_filter(self, mock_embedding):
        """同时传入 category_filter 和 doc_type，WHERE 子句应包含两者。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        captured_sqls = []

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        def capture_text(sql_str):
            captured_sqls.append(sql_str)
            return sql_str

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.text", side_effect=capture_text):
            mock_db.return_value = mock_cm
            engine.search("测试", category_filter="广告策略", doc_type="guide")

        assert len(captured_sqls) == 1
        sql_lower = captured_sqls[0].lower()
        assert "category" in sql_lower
        assert "doc_type" in sql_lower

    def test_search_date_range_partial_start_only(self, mock_embedding):
        """date_range 只有起始日期时，只加 start_date 条件。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        captured_sqls = []

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        def capture_text(sql_str):
            captured_sqls.append(sql_str)
            return sql_str

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db, \
             patch("src.knowledge_base.rag_engine.text", side_effect=capture_text):
            mock_db.return_value = mock_cm
            engine.search("测试", date_range=(date(2025, 1, 1), None))

        assert "start_date" in captured_sqls[0]
        assert "end_date" not in captured_sqls[0]


# ===========================================================================
# 6. ORM 模型新增列测试
# ===========================================================================

class TestORMModels:
    """验证 ORM 模型包含新增列。"""

    def test_document_has_doc_type_column(self):
        """Document 模型应有 doc_type 列。"""
        from src.db.models import Document

        assert hasattr(Document, "doc_type")

    def test_document_has_version_column(self):
        from src.db.models import Document

        assert hasattr(Document, "version")

    def test_document_has_effective_date_column(self):
        from src.db.models import Document

        assert hasattr(Document, "effective_date")

    def test_document_has_expires_date_column(self):
        from src.db.models import Document

        assert hasattr(Document, "expires_date")

    def test_document_has_priority_column(self):
        from src.db.models import Document

        assert hasattr(Document, "priority")

    def test_document_chunk_has_doc_type_column(self):
        """DocumentChunk 模型应有冗余 doc_type 列。"""
        from src.db.models import DocumentChunk

        assert hasattr(DocumentChunk, "doc_type")

    def test_existing_columns_unchanged(self):
        """现有列不应被删除（向后兼容）。"""
        from src.db.models import Document, DocumentChunk

        # Document 原始列
        for col in ("id", "title", "content", "source", "category", "embedding", "created_at"):
            assert hasattr(Document, col), f"Document.{col} 列丢失"

        # DocumentChunk 原始列
        for col in ("id", "document_id", "chunk_text", "chunk_embedding", "chunk_index", "created_at"):
            assert hasattr(DocumentChunk, col), f"DocumentChunk.{col} 列丢失"

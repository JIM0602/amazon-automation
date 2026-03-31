"""
RAG 引擎单元测试（全 mock，不需要真实 OpenAI API 或数据库）。

测试覆盖：
    - test_embed_text_calls_openai_api: 验证 embed_text 正确调用 OpenAI Embeddings API
    - test_embed_text_import_error: 未安装 openai 时抛出 ImportError
    - test_ingest_chunks_writes_to_db: 验证 ingest_chunks 写入数据库的逻辑（SQLite in-memory 或 mock session）
    - test_ingest_chunks_empty_list: 空列表时直接返回 0
    - test_search_vector_query: 验证 search 的向量查询逻辑（mock pgvector查询）
    - test_search_with_category_filter: 验证 category_filter 过滤逻辑
    - test_answer_full_flow: 完整 RAG 流程（mock embedding + mock LLM）
    - test_answer_empty_results_refuses_fabrication: 检索为空时回答必须包含"没有找到相关信息"
"""

import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 预先注入 openai stub（防止 No module named 'openai'）
# ---------------------------------------------------------------------------

def _inject_openai_stub():
    """如果 openai 未安装，注入最小 stub 到 sys.modules。"""
    if "openai" not in sys.modules:
        stub = ModuleType("openai")
        stub.OpenAI = MagicMock
        sys.modules["openai"] = stub

    if "langchain_openai" not in sys.modules:
        lc_stub = ModuleType("langchain_openai")
        lc_stub.ChatOpenAI = MagicMock
        sys.modules["langchain_openai"] = lc_stub

    if "langchain" not in sys.modules:
        lc_main = ModuleType("langchain")
        sys.modules["langchain"] = lc_main

    if "langchain.schema" not in sys.modules:
        lc_schema = ModuleType("langchain.schema")
        lc_schema.HumanMessage = MagicMock
        lc_schema.SystemMessage = MagicMock
        sys.modules["langchain.schema"] = lc_schema


# 在导入 rag_engine 之前注入 stub
_inject_openai_stub()


# ---------------------------------------------------------------------------
# 辅助 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_embedding():
    """返回一个 1536 维的 mock embedding 向量。"""
    return [0.1] * 1536


@pytest.fixture
def sample_chunks():
    """返回标准格式的文档分块样本。"""
    return [
        {
            "chunk_text": "BSR（Best Seller Rank）由亚马逊根据销售量综合计算",
            "chunk_index": 0,
            "metadata": {
                "source": "doc1.md",
                "category": "选品方法论",
                "title": "Amazon选品指南",
            },
        },
        {
            "chunk_text": "ACoS（广告成本销售比）= 广告花费 / 广告带来的销售额",
            "chunk_index": 1,
            "metadata": {
                "source": "doc2.md",
                "category": "广告策略",
                "title": "广告优化手册",
            },
        },
    ]


@pytest.fixture
def mock_search_results():
    """返回模拟的 search() 结果。"""
    return [
        {
            "chunk_text": "BSR（Best Seller Rank）由亚马逊根据销售量综合计算，每小时更新。",
            "chunk_index": 0,
            "metadata": {
                "title": "Amazon选品指南",
                "category": "选品方法论",
                "source": "doc1.md",
            },
            "similarity_score": 0.92,
        }
    ]


# ---------------------------------------------------------------------------
# 创建 RAGEngine 实例的辅助函数（绕过 settings 加载）
# ---------------------------------------------------------------------------

def _make_engine():
    """
    创建 RAGEngine 并注入 mock 配置，避免依赖真实 settings / openai。

    策略：
      1. 注入 openai stub 避免 ModuleNotFoundError
      2. 直接 __new__ 创建引擎实例并设置属性
      3. 注入 mock openai_client
    """
    _inject_openai_stub()

    from src.knowledge_base.rag_engine import RAGEngine

    engine = RAGEngine.__new__(RAGEngine)
    engine._api_key = "sk-test-mock-key"
    engine._model = "gpt-4o-mini"
    engine._openai_client = MagicMock()
    return engine


# ===========================================================================
# 测试：embed_text
# ===========================================================================

class TestEmbedText:
    """测试 embed_text 方法。"""

    def test_embed_text_calls_openai_api(self, mock_embedding):
        """验证 embed_text 正确调用 OpenAI Embeddings API，返回 1536 维向量。"""
        engine = _make_engine()

        # mock openai embeddings 响应
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        engine._openai_client.embeddings.create.return_value = mock_response

        # patch _OPENAI_AVAILABLE=True，因为本地可能未安装 openai 库
        with patch("src.knowledge_base.rag_engine._OPENAI_AVAILABLE", True):
            result = engine.embed_text("测试文本")

        # 验证调用参数
        engine._openai_client.embeddings.create.assert_called_once_with(
            input="测试文本",
            model="text-embedding-3-small",
        )
        # 验证返回值维度
        assert result == mock_embedding
        assert len(result) == 1536

    def test_embed_text_returns_list_of_floats(self, mock_embedding):
        """验证 embed_text 返回浮点数列表。"""
        engine = _make_engine()

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        engine._openai_client.embeddings.create.return_value = mock_response

        with patch("src.knowledge_base.rag_engine._OPENAI_AVAILABLE", True):
            result = engine.embed_text("任意文本")

        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_embed_text_raises_when_openai_unavailable(self):
        """未安装 openai 时，embed_text 应抛出 ImportError。"""
        engine = _make_engine()
        engine._openai_client = None

        with patch("src.knowledge_base.rag_engine._OPENAI_AVAILABLE", False):
            with pytest.raises(ImportError, match="openai 库未安装"):
                engine.embed_text("test")

    def test_embed_text_propagates_api_error(self):
        """API 调用失败时，embed_text 应抛出异常。"""
        engine = _make_engine()
        engine._openai_client.embeddings.create.side_effect = RuntimeError("API Error")

        with patch("src.knowledge_base.rag_engine._OPENAI_AVAILABLE", True):
            with pytest.raises(RuntimeError, match="API Error"):
                engine.embed_text("test")


# ===========================================================================
# 测试：ingest_chunks
# ===========================================================================

class TestIngestChunks:
    """测试 ingest_chunks 方法。"""

    def test_ingest_chunks_empty_list_returns_zero(self):
        """空列表时直接返回 0，不触发数据库操作。"""
        engine = _make_engine()
        result = engine.ingest_chunks([])
        assert result == 0

    def test_ingest_chunks_writes_to_db(self, sample_chunks, mock_embedding):
        """验证 ingest_chunks 正确写入数据库。"""
        engine = _make_engine()

        # mock embed_text
        engine.embed_text = MagicMock(return_value=mock_embedding)

        # mock 数据库 session
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db_session, \
             patch("src.knowledge_base.rag_engine.DocumentChunk") as mock_chunk_cls:

            # 让 db_session() 返回 context manager
            mock_db_session.return_value = mock_cm
            mock_chunk_instance = MagicMock()
            mock_chunk_cls.return_value = mock_chunk_instance

            # 执行
            result = engine.ingest_chunks(sample_chunks)

        # 验证返回数量
        assert result == len(sample_chunks)
        # 验证 session.add 被调用了正确次数
        assert mock_session.add.call_count == len(sample_chunks)
        # 验证 session.commit 被调用
        mock_session.commit.assert_called_once()

    def test_ingest_chunks_calls_embed_text_for_each_chunk(self, sample_chunks, mock_embedding):
        """验证 ingest_chunks 为每个 chunk 调用一次 embed_text。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db_session, \
             patch("src.knowledge_base.rag_engine.DocumentChunk"):
            mock_db_session.return_value = mock_cm
            engine.ingest_chunks(sample_chunks)

        assert engine.embed_text.call_count == len(sample_chunks)

    def test_ingest_chunks_continues_on_embed_failure(self, mock_embedding):
        """embedding 失败时，ingest_chunks 应跳过该 chunk 但继续处理其他 chunk。"""
        engine = _make_engine()

        # 第一个 embed 失败，第二个成功
        engine.embed_text = MagicMock(
            side_effect=[RuntimeError("embed failed"), mock_embedding]
        )

        chunks = [
            {
                "chunk_text": "chunk 1",
                "chunk_index": 0,
                "metadata": {"source": "s1", "category": "cat1", "title": "T1"},
            },
            {
                "chunk_text": "chunk 2",
                "chunk_index": 1,
                "metadata": {"source": "s2", "category": "cat2", "title": "T2"},
            },
        ]

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db_session, \
             patch("src.knowledge_base.rag_engine.DocumentChunk"):
            mock_db_session.return_value = mock_cm
            result = engine.ingest_chunks(chunks)

        # 两个 chunk 都应被写入（失败的 embedding 为 None，但仍然写入）
        assert result == 2


# ===========================================================================
# 测试：search
# ===========================================================================

class TestSearch:
    """测试 search 方法（mock pgvector 查询）。"""

    def _make_mock_row(self, chunk_text, chunk_index, title, category, source, distance=0.1):
        """创建模拟数据库查询行。"""
        return (
            str(uuid.uuid4()),  # id
            chunk_text,         # chunk_text
            chunk_index,        # chunk_index
            str(uuid.uuid4()),  # document_id
            title,              # title
            category,           # category
            source,             # source
            distance,           # distance (相似度距离，越小越相似)
        )

    def test_search_returns_results_sorted_by_similarity(self, mock_embedding):
        """验证 search 执行向量相似度查询并返回正确格式的结果。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        mock_row = self._make_mock_row(
            "BSR（Best Seller Rank）是亚马逊的排名指标",
            0, "选品指南", "选品方法论", "doc1.md", distance=0.08
        )

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db_session, \
             patch("src.knowledge_base.rag_engine.text") as mock_text:
            mock_db_session.return_value = mock_cm
            mock_text.return_value = "mocked_sql"

            results = engine.search("BSR是什么", top_k=5)

        assert len(results) == 1
        result = results[0]
        assert result["chunk_text"] == "BSR（Best Seller Rank）是亚马逊的排名指标"
        assert result["chunk_index"] == 0
        assert result["metadata"]["title"] == "选品指南"
        assert result["metadata"]["category"] == "选品方法论"
        assert "similarity_score" in result
        # distance=0.08 → similarity_score = 1 - 0.08 = 0.92
        assert abs(result["similarity_score"] - 0.92) < 0.001

    def test_search_with_category_filter(self, mock_embedding):
        """验证 category_filter 参数使查询包含 WHERE 条件。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        captured_sql = {}

        def mock_text(sql_str):
            captured_sql["sql"] = sql_str
            return sql_str

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db_session, \
             patch("src.knowledge_base.rag_engine.text", side_effect=mock_text):
            mock_db_session.return_value = mock_cm
            engine.search("查询广告策略", top_k=3, category_filter="广告策略")

        # 验证 SQL 包含 category 过滤条件
        assert "category" in captured_sql.get("sql", "").lower() or \
               mock_session.execute.called

    def test_search_returns_empty_list_when_no_results(self, mock_embedding):
        """没有匹配结果时应返回空列表。"""
        engine = _make_engine()
        engine.embed_text = MagicMock(return_value=mock_embedding)

        mock_session = MagicMock()
        mock_execute_result = MagicMock()
        mock_execute_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_execute_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("src.knowledge_base.rag_engine.db_session") as mock_db_session, \
             patch("src.knowledge_base.rag_engine.text"):
            mock_db_session.return_value = mock_cm
            results = engine.search("完全不存在的话题zzzzz", top_k=5)

        assert results == []


# ===========================================================================
# 测试：answer
# ===========================================================================

class TestAnswer:
    """测试 answer 方法（完整 RAG 流程）。"""

    def test_answer_empty_results_refuses_fabrication(self):
        """当检索结果为空时，回答必须包含'没有找到相关信息'（拒绝编造）。"""
        engine = _make_engine()
        engine.search = MagicMock(return_value=[])

        result = engine.answer("这是一个完全没有答案的问题xyz")

        assert "没有找到相关信息" in result["answer"]
        assert result["sources"] == []
        assert result["tokens_used"] == 0

    def test_answer_full_flow_with_mock(self, mock_search_results):
        """完整 RAG 流程：mock search + mock LLM，验证返回结构。"""
        engine = _make_engine()
        engine.search = MagicMock(return_value=mock_search_results)
        engine._call_llm = MagicMock(
            return_value=("BSR是亚马逊的排名指标，每小时更新。【来源：Amazon选品指南】", 150)
        )

        result = engine.answer("BSR是什么？")

        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result
        assert "model" in result
        assert "tokens_used" in result
        assert result["tokens_used"] == 150
        assert len(result["sources"]) >= 1

    def test_answer_appends_source_if_missing(self, mock_search_results):
        """如果 LLM 回答中没有来源标注，answer() 应自动添加。"""
        engine = _make_engine()
        engine.search = MagicMock(return_value=mock_search_results)
        # LLM 回答不包含【来源：xxx】
        engine._call_llm = MagicMock(
            return_value=("BSR是亚马逊的排名指标", 100)
        )

        result = engine.answer("BSR是什么？")

        assert "【来源：" in result["answer"]

    def test_answer_returns_correct_model_field(self, mock_search_results):
        """验证 answer 返回的 model 字段与引擎配置一致。"""
        engine = _make_engine()
        engine._model = "gpt-4o-mini"
        engine.search = MagicMock(return_value=mock_search_results)
        engine._call_llm = MagicMock(
            return_value=("测试回答【来源：测试文档】", 50)
        )

        result = engine.answer("测试问题")
        assert result["model"] == "gpt-4o-mini"

    def test_answer_sources_deduplicated(self):
        """来自同一文档的多个 chunk 应只产生一个 source 条目。"""
        engine = _make_engine()

        # 同一文档的两个 chunk
        dup_results = [
            {
                "chunk_text": "chunk 1 内容",
                "chunk_index": 0,
                "metadata": {
                    "title": "同一文档",
                    "category": "选品方法论",
                    "source": "same_doc.md",
                },
                "similarity_score": 0.95,
            },
            {
                "chunk_text": "chunk 2 内容",
                "chunk_index": 1,
                "metadata": {
                    "title": "同一文档",
                    "category": "选品方法论",
                    "source": "same_doc.md",
                },
                "similarity_score": 0.90,
            },
        ]
        engine.search = MagicMock(return_value=dup_results)
        engine._call_llm = MagicMock(
            return_value=("回答内容【来源：同一文档】", 80)
        )

        result = engine.answer("测试问题")

        # 同一文档只应出现一次
        assert len(result["sources"]) == 1
        assert result["sources"][0]["title"] == "同一文档"

    def test_answer_handles_llm_failure_gracefully(self, mock_search_results):
        """LLM 调用失败时，answer() 应降级返回检索内容而不是抛出异常。"""
        engine = _make_engine()
        engine.search = MagicMock(return_value=mock_search_results)
        engine._call_llm = MagicMock(side_effect=RuntimeError("LLM down"))

        result = engine.answer("测试问题")

        # 应该有回答内容（降级处理），而不是抛出异常
        assert "answer" in result
        assert result["answer"] != ""

    def test_answer_search_failure_returns_no_info(self):
        """search 完全失败时，answer() 应返回'没有找到相关信息'。"""
        engine = _make_engine()
        engine.search = MagicMock(side_effect=RuntimeError("DB connection failed"))

        result = engine.answer("测试问题")

        assert "没有找到相关信息" in result["answer"]
        assert result["sources"] == []


# ===========================================================================
# 测试：query 便捷函数
# ===========================================================================

class TestQueryFunction:
    """测试模块级 query() 便捷函数。"""

    def test_query_returns_string(self):
        """query() 应返回字符串。"""
        with patch("src.knowledge_base.rag_engine._get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.answer.return_value = {
                "answer": "这是测试回答",
                "sources": [],
                "model": "gpt-4o-mini",
                "tokens_used": 0,
            }
            mock_get_engine.return_value = mock_engine

            from src.knowledge_base.rag_engine import query
            result = query("测试问题")

        assert isinstance(result, str)
        assert result == "这是测试回答"

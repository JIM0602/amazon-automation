"""
RAG（检索增强生成）核心模块。

功能：
    - embed_text: 调用 OpenAI text-embedding-3-small 生成1536维向量
    - ingest_chunks: 批量写入文档分块到 document_chunks 表
    - search: pgvector 向量相似度搜索 + 可选关键词过滤
    - answer: RAG问答主流程（检索 + LLM生成）

依赖：
    - openai / langchain-openai（可选，try/except降级处理）
    - sqlalchemy + pgvector（数据库端）
    - src.config.settings 读取 OPENAI_API_KEY, OPENAI_MODEL
    - src.db.connection.db_session 获取数据库连接
    - src.db.models.DocumentChunk 写入向量数据
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import text  # noqa: F401 — re-exported for test patching

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 数据库依赖（延迟导入，避免循环依赖，但在模块级声明以支持 mock）
# ---------------------------------------------------------------------------
try:
    from src.db.connection import db_session  # noqa: F401
    from src.db.models import DocumentChunk  # noqa: F401
    _DB_AVAILABLE = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    DocumentChunk = None  # type: ignore[assignment]
    _DB_AVAILABLE = False

# ---------------------------------------------------------------------------
# 可选依赖：openai / langchain
# ---------------------------------------------------------------------------
try:
    import openai as _openai_module  # type: ignore

    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False
    logger.warning("openai 未安装，embed_text 将不可用")

try:
    from langchain_openai import ChatOpenAI  # type: ignore

    _LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    _LANGCHAIN_OPENAI_AVAILABLE = False
    logger.warning("langchain-openai 未安装，LLM 调用将直接使用 openai")

try:
    from langchain.schema import HumanMessage, SystemMessage  # type: ignore

    _LANGCHAIN_SCHEMA_AVAILABLE = True
except ImportError:
    _LANGCHAIN_SCHEMA_AVAILABLE = False

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

SYSTEM_PROMPT = """你是一个亚马逊跨境电商运营知识库助手。

规则（必须严格遵守）：
1. 只能基于下方提供的知识库内容回答问题，不能使用知识库之外的信息。
2. 如果知识库中没有相关信息，必须回答：
   "根据现有知识库，我没有找到关于[问题关键词]的相关信息"
3. 在回答末尾标注引用来源：【来源：文档名】

知识库内容：
{context}
"""


class RAGEngine:
    """RAG（检索增强生成）引擎，封装向量化、检索和问答能力。"""

    def __init__(self):
        """从 src.config.settings 读取 OPENAI_API_KEY，初始化 LangChain 组件。"""
        try:
            from src.config import settings  # noqa: PLC0415

            self._api_key = settings.OPENAI_API_KEY
            self._model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        except Exception as exc:
            logger.warning("无法加载 settings，将使用环境变量: %s", exc)
            import os

            self._api_key = os.environ.get("OPENAI_API_KEY", "")
            self._model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        if _OPENAI_AVAILABLE:
            self._openai_client = _openai_module.OpenAI(api_key=self._api_key)
        else:
            self._openai_client = None

        logger.info("RAGEngine 初始化完成，使用模型: %s", self._model)

    # ---------------------------------------------------------------------- #
    # embed_text
    # ---------------------------------------------------------------------- #

    def embed_text(self, text: str) -> list:
        """
        调用 OpenAI text-embedding-3-small 生成1536维向量。

        Args:
            text: 需要向量化的文本

        Returns:
            1536维浮点数列表

        Raises:
            ImportError: 未安装 openai 库
            Exception: API 调用失败
        """
        if not _OPENAI_AVAILABLE or self._openai_client is None:
            raise ImportError("openai 库未安装，无法调用 embed_text")

        try:
            response = self._openai_client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL,
            )
            embedding = response.data[0].embedding
            logger.debug("embed_text 成功，文本长度: %d", len(text))
            return embedding
        except Exception as exc:
            logger.error("embed_text 失败: %s", exc)
            raise

    # ---------------------------------------------------------------------- #
    # ingest_chunks
    # ---------------------------------------------------------------------- #

    def ingest_chunks(self, chunks: list) -> int:
        """
        将文档分块批量写入 document_chunks 表。

        Args:
            chunks: 文档分块列表，每个 chunk 格式为：
                {
                    "chunk_text": str,
                    "chunk_index": int,
                    "metadata": {
                        "source": str,
                        "category": str,
                        "title": str,
                    }
                }

        Returns:
            成功写入的数量
        """
        if not chunks:
            logger.info("ingest_chunks: 空列表，无需写入")
            return 0

        if db_session is None or DocumentChunk is None:
            raise ImportError("无法导入数据库模块（db_session 或 DocumentChunk 为 None）")

        success_count = 0

        try:
            with db_session() as session:
                for chunk in chunks:
                    chunk_text = chunk.get("chunk_text", "")
                    chunk_index = chunk.get("chunk_index", 0)
                    metadata = chunk.get("metadata", {})

                    # 生成 embedding
                    try:
                        embedding = self.embed_text(chunk_text)
                    except Exception as exc:
                        logger.warning(
                            "chunk[%d] embedding 失败，跳过: %s", chunk_index, exc
                        )
                        embedding = None

                    # 创建 DocumentChunk 记录
                    # document_id 使用 metadata 中的 source 生成确定性 UUID
                    source = metadata.get("source", "")
                    doc_uuid = uuid.uuid5(uuid.NAMESPACE_URL, source) if source else uuid.uuid4()

                    db_chunk = DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=doc_uuid,
                        chunk_text=chunk_text,
                        chunk_embedding=embedding,
                        chunk_index=chunk_index,
                    )
                    # 把 metadata 作为扩展属性存储（通过修改 chunk_text 附带 JSON 不优雅，
                    # 此处用一个非 ORM 字段来保持兼容，实际应在 Document 表维护 metadata）
                    # 为了测试可追踪，将 metadata 存到对象属性（不影响DB写入）
                    db_chunk._metadata = metadata

                    session.add(db_chunk)
                    success_count += 1

                session.commit()
                logger.info("ingest_chunks: 成功写入 %d/%d 块", success_count, len(chunks))

        except Exception as exc:
            logger.error("ingest_chunks 数据库写入失败: %s", exc)
            raise

        return success_count

    # ---------------------------------------------------------------------- #
    # search
    # ---------------------------------------------------------------------- #

    def search(
        self, query: str, top_k: int = 5, category_filter: Optional[str] = None
    ) -> list:
        """
        混合搜索：向量相似度搜索 + 可选关键词过滤。

        1. 生成 query 的 embedding 向量
        2. pgvector 相似度搜索：ORDER BY chunk_embedding <=> query_vec
        3. 如果有 category_filter，加 WHERE metadata->>'category' = category_filter

        Args:
            query: 查询文本
            top_k: 返回最相关的 top_k 条结果
            category_filter: 按分类过滤（可选）

        Returns:
            [{chunk_text, chunk_index, metadata, similarity_score}]
        """
        if db_session is None:
            raise ImportError("无法导入数据库模块（db_session 为 None）")

        # 生成查询向量
        try:
            query_embedding = self.embed_text(query)
        except Exception as exc:
            logger.error("search: 生成 query embedding 失败: %s", exc)
            raise

        results = []

        try:
            with db_session() as session:
                # 构建 pgvector 相似度查询
                # 使用余弦距离（<=> 操作符）
                query_vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

                if category_filter:
                    sql = text(
                        """
                        SELECT
                            dc.id,
                            dc.chunk_text,
                            dc.chunk_index,
                            dc.document_id,
                            d.title,
                            d.category,
                            d.source,
                            dc.chunk_embedding <=> CAST(:query_vec AS vector) AS distance
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE d.category = :category
                        ORDER BY distance ASC
                        LIMIT :top_k
                        """
                    )
                    rows = session.execute(
                        sql,
                        {
                            "query_vec": query_vec_str,
                            "category": category_filter,
                            "top_k": top_k,
                        },
                    ).fetchall()
                else:
                    sql = text(
                        """
                        SELECT
                            dc.id,
                            dc.chunk_text,
                            dc.chunk_index,
                            dc.document_id,
                            d.title,
                            d.category,
                            d.source,
                            dc.chunk_embedding <=> CAST(:query_vec AS vector) AS distance
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        ORDER BY distance ASC
                        LIMIT :top_k
                        """
                    )
                    rows = session.execute(
                        sql,
                        {"query_vec": query_vec_str, "top_k": top_k},
                    ).fetchall()

                for row in rows:
                    distance = row[-1] if row[-1] is not None else 1.0
                    similarity_score = max(0.0, 1.0 - float(distance))
                    results.append(
                        {
                            "chunk_text": row[1],
                            "chunk_index": row[2],
                            "metadata": {
                                "title": row[4],
                                "category": row[5],
                                "source": row[6],
                            },
                            "similarity_score": similarity_score,
                        }
                    )

        except Exception as exc:
            logger.error("search 数据库查询失败: %s", exc)
            raise

        logger.info(
            "search: 查询 '%s'，返回 %d 条结果 (category_filter=%s)",
            query[:50],
            len(results),
            category_filter,
        )
        return results

    # ---------------------------------------------------------------------- #
    # answer
    # ---------------------------------------------------------------------- #

    def answer(self, question: str, top_k: int = 5) -> dict:
        """
        RAG问答主流程：检索 + LLM 生成回答。

        1. search() 检索相关文档块
        2. 构建 Prompt：system_prompt + 检索结果 + 用户问题
        3. 调用 LLM 生成回答
        4. 如果检索结果为空，直接返回"没有找到相关信息"

        Args:
            question: 用户问题
            top_k: 检索最相关的 top_k 条

        Returns:
            {
                "answer": str,
                "sources": [{"title": str, "category": str, "source": str}],
                "model": str,
                "tokens_used": int,
            }
        """
        # 步骤1：检索相关文档
        try:
            search_results = self.search(question, top_k=top_k)
        except Exception as exc:
            logger.error("answer: search 失败: %s", exc)
            search_results = []

        # 步骤2：构建上下文
        if not search_results:
            # 知识库无相关内容，拒绝编造
            answer_text = f"根据现有知识库，我没有找到相关信息。（问题：{question}）"
            logger.info("answer: 检索结果为空，返回拒绝编造回答")
            return {
                "answer": answer_text,
                "sources": [],
                "model": self._model,
                "tokens_used": 0,
            }

        # 构建上下文文本
        context_parts = []
        sources = []
        seen_sources = set()

        for i, chunk in enumerate(search_results, 1):
            meta = chunk.get("metadata", {})
            title = meta.get("title", "未知文档")
            category = meta.get("category", "")
            source = meta.get("source", "")
            chunk_text = chunk.get("chunk_text", "")

            context_parts.append(f"[{i}] {title}（{category}）\n{chunk_text}")

            source_key = (title, category, source)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(
                    {"title": title, "category": category, "source": source}
                )

        context = "\n\n".join(context_parts)

        # 步骤3：构建 Prompt 并调用 LLM
        system_content = SYSTEM_PROMPT.format(context=context)
        tokens_used = 0
        answer_text = ""

        try:
            answer_text, tokens_used = self._call_llm(system_content, question)
        except Exception as exc:
            logger.error("answer: LLM 调用失败: %s", exc)
            # 降级：返回最相关的文档内容
            answer_text = f"（LLM调用失败）检索到的最相关内容：\n{search_results[0]['chunk_text']}"

        # 确保来源标注在回答末尾
        if sources and "【来源：" not in answer_text:
            source_labels = "、".join(s["title"] for s in sources[:3])
            answer_text = answer_text + f"\n\n【来源：{source_labels}】"

        return {
            "answer": answer_text,
            "sources": sources,
            "model": self._model,
            "tokens_used": tokens_used,
        }

    def _call_llm(self, system_content: str, user_question: str) -> tuple:
        """
        调用 LLM 生成回答。

        Returns:
            (answer_text: str, tokens_used: int)
        """
        # 优先使用 langchain-openai
        if _LANGCHAIN_OPENAI_AVAILABLE and _LANGCHAIN_SCHEMA_AVAILABLE:
            try:
                llm = ChatOpenAI(
                    model=self._model,
                    openai_api_key=self._api_key,
                    temperature=0.0,
                )
                messages = [
                    SystemMessage(content=system_content),
                    HumanMessage(content=user_question),
                ]
                response = llm.invoke(messages)
                answer_text = response.content
                tokens_used = getattr(response, "response_metadata", {}).get(
                    "token_usage", {}
                ).get("total_tokens", 0)
                return answer_text, tokens_used
            except Exception as exc:
                logger.warning("LangChain 调用失败，降级到 openai 直接调用: %s", exc)

        # 降级使用 openai 直接调用
        if _OPENAI_AVAILABLE and self._openai_client is not None:
            response = self._openai_client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_question},
                ],
                temperature=0.0,
            )
            answer_text = response.choices[0].message.content or ""
            tokens_used = getattr(response.usage, "total_tokens", 0)
            return answer_text, tokens_used

        raise ImportError("openai 和 langchain-openai 均未安装，无法调用 LLM")


# ---------------------------------------------------------------------------
# 模块级便捷函数
# ---------------------------------------------------------------------------

_engine_instance: Optional[RAGEngine] = None


def _get_engine() -> RAGEngine:
    """懒加载全局 RAGEngine 实例。"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RAGEngine()
    return _engine_instance


def query(question: str) -> str:
    """
    快速调用 RAGEngine.answer()，返回回答字符串，方便命令行测试。

    Args:
        question: 用户问题

    Returns:
        回答字符串
    """
    engine = _get_engine()
    result = engine.answer(question)
    return result["answer"]

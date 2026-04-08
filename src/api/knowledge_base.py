"""知识库 API 路由。

提供：
- POST /api/kb/import    — 触发后台文档导入（JSON 目录或文件上传）
- GET  /api/kb/status    — 查询知识库状态统计
- POST /api/kb/query     — RAG 知识库查询
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.db.connection import get_db
from src.db.models import Document, DocumentChunk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------

class ImportRequest(BaseModel):
    """POST /api/kb/import 的 JSON 请求体（目录导入模式）。"""
    directory: str
    batch_size: int = Field(default=10, ge=1, le=100)


class ImportResponse(BaseModel):
    """导入任务的立即响应。"""
    job_id: str
    status: str = "started"


class KBStatusResponse(BaseModel):
    """GET /api/kb/status 的响应。"""
    total_documents: int
    total_chunks: int
    last_updated: Optional[str] = None


class QueryRequest(BaseModel):
    """POST /api/kb/query 的请求体。"""
    question: str
    top_k: int = Field(default=5, ge=1, le=20)


class SourceInfo(BaseModel):
    """查询结果中的来源信息。"""
    title: str = ""
    source: str = ""
    chunk_text: str = ""


class QueryResponse(BaseModel):
    """POST /api/kb/query 的响应。"""
    answer: str
    sources: List[SourceInfo] = []


# ---------------------------------------------------------------------------
# 后台导入任务
# ---------------------------------------------------------------------------

def _run_import_task(directory: str, batch_size: int, job_id: str) -> None:
    """在后台线程中运行文档导入。"""
    try:
        from scripts.import_documents import import_documents
        result = import_documents(
            directory=directory,
            batch_size=batch_size,
            resume=False,
        )
        logger.info(
            "导入任务 %s 完成: 总计 %d, 成功 %d, 失败 %d",
            job_id,
            result["total"],
            result["imported"],
            result["failed"],
        )
    except Exception as exc:
        logger.error("导入任务 %s 失败: %s", job_id, exc)


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@router.post("/import", response_model=ImportResponse)
async def import_documents_api(
    body: ImportRequest,
    background_tasks: BackgroundTasks,
    _current_user: Dict[str, Any] = Depends(get_current_user),
) -> ImportResponse:
    """触发后台文档导入。

    接受 JSON body:
        {"directory": "/path/to/docs", "batch_size": 10}

    立即返回 job_id 和 status，导入在后台执行。
    """
    job_id = str(uuid.uuid4())

    background_tasks.add_task(
        _run_import_task,
        directory=body.directory,
        batch_size=body.batch_size,
        job_id=job_id,
    )

    logger.info(
        "导入任务已启动: job_id=%s, directory=%s, batch_size=%d",
        job_id,
        body.directory,
        body.batch_size,
    )
    return ImportResponse(job_id=job_id, status="started")


@router.get("/status", response_model=KBStatusResponse)
async def get_kb_status(
    db: Session = Depends(get_db),
    _current_user: Dict[str, Any] = Depends(get_current_user),
) -> KBStatusResponse:
    """查询知识库状态。

    返回:
        {"total_documents": N, "total_chunks": N, "last_updated": "ISO-8601 or null"}
    """
    try:
        total_documents = db.query(func.count(Document.id)).scalar() or 0
        total_chunks = db.query(func.count(DocumentChunk.id)).scalar() or 0

        # 获取最近更新时间（documents 和 chunks 中最新的 created_at）
        last_doc_time = db.query(func.max(Document.created_at)).scalar()
        last_chunk_time = db.query(func.max(DocumentChunk.created_at)).scalar()

        last_updated = None
        if last_doc_time and last_chunk_time:
            latest = max(last_doc_time, last_chunk_time)
            last_updated = latest.isoformat()
        elif last_doc_time:
            last_updated = last_doc_time.isoformat()
        elif last_chunk_time:
            last_updated = last_chunk_time.isoformat()

        return KBStatusResponse(
            total_documents=total_documents,
            total_chunks=total_chunks,
            last_updated=last_updated,
        )
    except Exception as exc:
        logger.error("查询知识库状态失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"查询知识库状态失败: {exc}")


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    body: QueryRequest,
    _current_user: Dict[str, Any] = Depends(get_current_user),
) -> QueryResponse:
    """RAG 知识库查询。

    接受:
        {"question": "...", "top_k": 5}

    返回:
        {"answer": "...", "sources": [{"title": "...", "source": "...", "chunk_text": "..."}]}
    """
    try:
        from src.knowledge_base.rag_engine import RAGEngine

        engine = RAGEngine()
        result = engine.answer(body.question, top_k=body.top_k)

        # 构建 sources 列表（包含 chunk_text）
        sources: List[SourceInfo] = []
        seen_sources = set()

        # answer() 返回的 sources 不含 chunk_text，需要从 search 结果补充
        try:
            search_results = engine.search(body.question, top_k=body.top_k)
            for sr in search_results:
                meta = sr.get("metadata", {})
                source_key = (meta.get("title", ""), meta.get("source", ""))
                if source_key not in seen_sources:
                    seen_sources.add(source_key)
                    sources.append(SourceInfo(
                        title=meta.get("title", ""),
                        source=meta.get("source", ""),
                        chunk_text=sr.get("chunk_text", "")[:500],  # 截断避免过长
                    ))
        except Exception as search_exc:
            logger.warning("获取 search 结果用于 sources 失败: %s", search_exc)
            # 降级：使用 answer() 自带的 sources
            for src_item in result.get("sources", []):
                sources.append(SourceInfo(
                    title=src_item.get("title", ""),
                    source=src_item.get("source", ""),
                    chunk_text="",
                ))

        return QueryResponse(
            answer=result.get("answer", ""),
            sources=sources,
        )

    except Exception as exc:
        logger.error("知识库查询失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"知识库查询失败: {exc}")

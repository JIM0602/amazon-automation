#!/usr/bin/env python3
"""知识库文档导入 CLI 脚本。

将 .docx 文件批量导入到 PostgreSQL pgvector 知识库中，
同时写入 documents 和 document_chunks 两张表。

用法:
    python scripts/import_documents.py --directory /tmp/test-docs/ --batch-size 10
    python scripts/import_documents.py --directory /tmp/test-docs/ --resume
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import uuid
from pathlib import Path

# 确保项目根目录在 sys.path 中（支持 docker exec 直接运行）
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.knowledge_base.document_processor import DocumentProcessor
from src.knowledge_base.rag_engine import RAGEngine
from src.db.connection import db_session
from src.db.models import Document, DocumentChunk

logger = logging.getLogger(__name__)


def compute_content_hash(file_path: str) -> str:
    """计算文件内容的 MD5 哈希值。"""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_existing_documents(session) -> dict[str, str]:
    """查询 documents 表中已存在的记录，返回 {source: content_hash_or_id} 映射。

    因为 Document 模型没有 content_hash 列，我们用 source 字段去重。
    返回 {source: document_id_hex}，用于检测重复。
    """
    existing = {}
    try:
        rows = session.query(Document.source, Document.id).all()
        for row in rows:
            existing[row.source] = str(row.id)
    except Exception as exc:
        logger.warning("查询已有文档失败（可能是首次导入）: %s", exc)
    return existing


def upsert_document(
    session,
    *,
    doc_id: uuid.UUID,
    title: str,
    content: str,
    source: str,
    category: str,
    doc_type: str,
) -> uuid.UUID:
    """创建或更新 Document 行。

    如果 source 已存在，更新内容；否则创建新记录。
    Document.id 使用 uuid5(NAMESPACE_URL, source) 以保持与 ingest_chunks 中
    document_id 生成逻辑一致（FK 关系自动成立）。

    Returns:
        Document 的 UUID
    """
    existing = session.query(Document).filter(Document.source == source).first()
    if existing is not None:
        # 更新已有记录
        existing.title = title
        existing.content = content
        existing.category = category
        existing.doc_type = doc_type
        logger.info("更新已有文档: %s (id=%s)", source, existing.id)
        return existing.id
    else:
        doc = Document(
            id=doc_id,
            title=title,
            content=content,
            source=source,
            category=category,
            doc_type=doc_type,
        )
        session.add(doc)
        session.flush()  # 确保 FK 可用
        logger.info("创建新文档: %s (id=%s)", source, doc_id)
        return doc_id


def delete_existing_chunks(session, document_id: uuid.UUID) -> int:
    """删除指定 document_id 的所有 chunks（用于更新场景）。"""
    count = session.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).delete()
    return count


def import_documents(
    directory: str,
    batch_size: int = 10,
    resume: bool = False,
    db_url: str | None = None,
) -> dict:
    """将指定目录下的 .docx 文件导入到知识库。

    完整流程:
    1. 扫描目录下所有 .docx 文件
    2. 计算每个文件的 MD5 哈希
    3. Upsert documents 记录
    4. 调用 DocumentProcessor 加载+分块
    5. 调用 RAGEngine.ingest_chunks() 写入 document_chunks
    6. 打印进度

    Args:
        directory: .docx 文件所在目录
        batch_size: 每批处理文档数
        resume: 是否断点续传（跳过已导入的文件）
        db_url: 数据库 URL（可选，默认从环境变量读取）

    Returns:
        {total, imported, skipped, failed, details}
    """
    # 如果指定了 db_url，设置环境变量以覆盖默认配置
    if db_url:
        os.environ["DATABASE_URL"] = db_url

    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")

    # 扫描 .docx 文件
    docx_files = sorted(dir_path.glob("*.docx"))
    if not docx_files:
        print(f"目录 {directory} 下没有找到 .docx 文件")
        return {"total": 0, "imported": 0, "skipped": 0, "failed": 0, "details": []}

    total = len(docx_files)
    print(f"找到 {total} 个 .docx 文件，batch_size={batch_size}")

    processor = DocumentProcessor()
    rag_engine = RAGEngine()

    report = {
        "total": total,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "details": [],
    }

    # 按 batch 处理
    for batch_start in range(0, total, batch_size):
        batch_files = docx_files[batch_start: batch_start + batch_size]

        with db_session() as session:
            # 查询已有文档（用于 resume 和幂等检测）
            existing_docs = get_existing_documents(session)

            for idx, file_path in enumerate(batch_files):
                file_num = batch_start + idx + 1
                file_str = str(file_path)
                source_key = str(file_path)  # 用完整路径作为 source

                try:
                    # 计算文件内容的 MD5 哈希
                    content_hash = compute_content_hash(file_str)

                    # 幂等 + resume 检查：如果 source 已存在
                    if source_key in existing_docs and resume:
                        print(f"  Skipped {file_num}/{total}: {file_path.name} (已导入)")
                        report["skipped"] += 1
                        report["details"].append({
                            "file": file_path.name,
                            "status": "skipped",
                            "reason": "already imported",
                        })
                        continue

                    # Step 1: 使用 DocumentProcessor 加载文档
                    doc_data = processor.load_document(file_str)

                    # Step 2: 分类 + 检测 doc_type
                    category = processor.classify_document(doc_data["content"])
                    doc_type = processor.detect_doc_type(
                        doc_data["content"], doc_data["title"]
                    )

                    # Step 3: 生成确定性 UUID（与 ingest_chunks 内部逻辑一致）
                    doc_uuid = uuid.uuid5(uuid.NAMESPACE_URL, source_key)

                    # Step 4: Upsert documents 行（必须先于 chunks 创建，FK 约束）
                    is_update = source_key in existing_docs

                    if is_update:
                        # 更新场景：先删除旧 chunks
                        delete_existing_chunks(session, doc_uuid)

                    document_id = upsert_document(
                        session,
                        doc_id=doc_uuid,
                        title=doc_data["title"],
                        content=doc_data["content"],
                        source=source_key,
                        category=category,
                        doc_type=doc_type,
                    )

                    # 必须先 commit documents 行，否则 ingest_chunks 的 FK 约束会失败
                    session.commit()

                    # Step 5: 分块
                    doc_for_chunk = {
                        **doc_data,
                        "category": category,
                        "doc_type": doc_type,
                        "source": source_key,
                    }
                    chunks = processor.chunk_document(doc_for_chunk)

                    # Step 6: 调用 rag_engine.ingest_chunks() 写入 document_chunks
                    # ingest_chunks 内部使用 uuid5(NAMESPACE_URL, source) 生成 document_id，
                    # 我们已经确保 Document.id 也用同样的逻辑生成。
                    # 确保每个 chunk 的 metadata.source 与 Document.source 一致。
                    for chunk in chunks:
                        chunk["metadata"]["source"] = source_key

                    written = rag_engine.ingest_chunks(chunks)

                    print(
                        f"  Processed {file_num}/{total}: {file_path.name} — "
                        f"{written} chunks"
                    )
                    report["imported"] += 1
                    report["details"].append({
                        "file": file_path.name,
                        "status": "imported",
                        "chunks": written,
                        "content_hash": content_hash,
                    })

                except Exception as exc:
                    logger.error("导入失败 %s: %s", file_path.name, exc)
                    print(f"  FAILED {file_num}/{total}: {file_path.name} — {exc}")
                    report["failed"] += 1
                    report["details"].append({
                        "file": file_path.name,
                        "status": "failed",
                        "error": str(exc),
                    })
                    # 出错后 rollback 并继续
                    try:
                        session.rollback()
                    except Exception:
                        pass

    # 汇总输出
    print(
        f"\n导入完成: 总计 {report['total']}, "
        f"成功 {report['imported']}, "
        f"跳过 {report['skipped']}, "
        f"失败 {report['failed']}"
    )
    return report


def main():
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="将 .docx 文件批量导入到 PostgreSQL pgvector 知识库"
    )
    parser.add_argument(
        "--directory",
        required=True,
        help=".docx 文件所在目录（必填）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="每批处理文档数（默认 10）",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="断点续传：跳过已导入的文件",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="数据库 URL（默认从环境变量 DATABASE_URL 读取）",
    )

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import_documents(
        directory=args.directory,
        batch_size=args.batch_size,
        resume=args.resume,
        db_url=args.db_url,
    )


if __name__ == "__main__":
    main()

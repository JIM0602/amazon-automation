#!/usr/bin/env python3
"""
seed_database.py — 一键初始化 Demo 数据库脚本

功能:
    - 从 data/mock/ 目录读取 Mock JSON 数据
    - 将知识文档导入 documents / document_chunks 表
    - 将产品数据导入 products 表
    - 将 system_config 写入初始配置
    - 将 audit_log 记录初始化事件

使用:
    python data/mock/seed_database.py               # 正常写入
    python data/mock/seed_database.py --dry-run     # 打印操作，不写 DB
    python data/mock/seed_database.py --clean       # 清空相关表后重建
    python data/mock/seed_database.py --clean --dry-run  # 显示清理+导入操作

要求:
    - 需要设置环境变量 DATABASE_URL 或 src/config.py 中有正确配置
    - 若 DB 不可用，脚本不会崩溃，会打印错误并退出
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
MOCK_DIR = SCRIPT_DIR
PROJECT_ROOT = SCRIPT_DIR.parent.parent.resolve()

KNOWLEDGE_BASE_DIR = MOCK_DIR / "knowledge_base"
SAMPLE_DOCS_DIR = KNOWLEDGE_BASE_DIR / "sample_docs"
SELLER_SPRITE_DIR = MOCK_DIR / "seller_sprite"
SP_API_DIR = MOCK_DIR / "amazon_sp_api"

# 把项目根目录加入 sys.path，保证 src.* 可导入
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# 统计计数器
# ---------------------------------------------------------------------------
stats: dict[str, int] = {
    "documents_imported": 0,
    "document_chunks_imported": 0,
    "products_imported": 0,
    "system_configs_written": 0,
    "audit_logs_written": 0,
    "errors": 0,
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def log(msg: str, indent: int = 0) -> None:
    prefix = "  " * indent
    try:
        print(f"{prefix}{msg}")
    except UnicodeEncodeError:
        # Windows GBK 终端下，将无法编码的字符替换后输出
        safe_msg = msg.encode("gbk", errors="replace").decode("gbk")
        print(f"{prefix}{safe_msg}")


def load_json(path: Path) -> dict | list | None:
    """安全读取 JSON 文件，失败返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log(f"[ERROR] 读取 JSON 失败: {path} — {exc}")
        stats["errors"] += 1
        return None


def load_markdown(path: Path) -> str | None:
    """安全读取 Markdown 文件，失败返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        log(f"[ERROR] 读取 Markdown 失败: {path} — {exc}")
        stats["errors"] += 1
        return None


def classify_doc(title: str, content: str) -> str:
    """根据标题/内容关键词简单分类文档。"""
    title_lower = title.lower()
    content_lower = content[:500].lower()
    combined = title_lower + " " + content_lower

    categories = {
        "A9算法": ["a9算法", "a9 algorithm", "a9", "搜索排名", "相关性因素"],
        "选品方法论": ["选品", "product selection", "d/c ratio", "需求竞争"],
        "Listing优化": ["listing优化", "五点描述", "bullet point", "a+内容", "主图"],
        "广告投放": ["ppc广告", "ppc", "acos", "sponsored products", "广告投放"],
        "竞品分析": ["竞品分析", "competitor", "竞争分析", "keepa"],
        "库存管理": ["库存管理", "ipi分数", "fba库存", "补货", "仓储"],
        "关键词研究": ["关键词研究", "关键词研究方法", "search volume", "长尾词"],
        "产品定价": ["产品定价", "定价策略", "pricing", "利润率", "成本结构"],
        "评论管理": ["评论管理", "review管理", "差评", "vine", "request a review"],
        "品牌建设": ["品牌建设", "品牌备案", "brand registry", "旗舰店", "商标"],
    }

    for category, keywords in categories.items():
        for kw in keywords:
            if kw in combined:
                return category

    return "通用运营"


def chunk_text(content: str, chunk_size: int = 800) -> list[str]:
    """将文本按段落分割成 chunks，每块不超过 chunk_size 字符。"""
    paragraphs = content.split("\n\n")
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [content[:chunk_size]]


# ---------------------------------------------------------------------------
# 核心导入函数
# ---------------------------------------------------------------------------

def import_documents(session, dry_run: bool = False) -> None:
    """扫描 sample_docs/ 目录，将 .md 文件导入 documents 和 document_chunks 表。"""
    from src.db.models import Document, DocumentChunk

    if not SAMPLE_DOCS_DIR.exists():
        log(f"[WARN] 文档目录不存在: {SAMPLE_DOCS_DIR}")
        return

    md_files = sorted(SAMPLE_DOCS_DIR.glob("*.md"))
    log(f"发现 {len(md_files)} 个 Markdown 文档")

    for md_file in md_files:
        content = load_markdown(md_file)
        if content is None:
            continue

        # 提取标题（第一行 # 开头）
        first_line = content.split("\n")[0].strip()
        title = first_line.lstrip("# ").strip() if first_line.startswith("#") else md_file.stem

        category = classify_doc(title, content)
        source = f"data/mock/knowledge_base/sample_docs/{md_file.name}"

        doc_id = uuid.uuid4()
        chunks = chunk_text(content)

        log(f"  [DOC] {title[:60]}", indent=1)
        log(f"       category={category}, chunks={len(chunks)}, chars={len(content)}", indent=2)

        if not dry_run:
            try:
                doc = Document(
                    id=doc_id,
                    title=title,
                    content=content,
                    source=source,
                    category=category,
                    embedding=None,  # embedding 需要 OpenAI API，此处置 None
                )
                session.add(doc)
                session.flush()  # 确保 doc.id 可用

                for idx, chunk_text_content in enumerate(chunks):
                    chunk = DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=doc_id,
                        chunk_text=chunk_text_content,
                        chunk_embedding=None,
                        chunk_index=idx,
                    )
                    session.add(chunk)

                stats["documents_imported"] += 1
                stats["document_chunks_imported"] += len(chunks)
            except Exception as exc:
                log(f"[ERROR] 写入文档失败: {title} — {exc}", indent=2)
                stats["errors"] += 1
                session.rollback()
        else:
            stats["documents_imported"] += 1
            stats["document_chunks_imported"] += len(chunks)


def import_products(session, dry_run: bool = False) -> None:
    """从 amazon_sp_api/product_catalog.json 导入产品数据到 products 表。"""
    from src.db.models import Product

    catalog_path = SP_API_DIR / "product_catalog.json"
    catalog = load_json(catalog_path)
    if catalog is None:
        return

    products_data = catalog.get("data", [])
    log(f"发现 {len(products_data)} 个产品")

    for prod in products_data:
        asin = prod.get("asin", "UNKNOWN")
        sku = prod.get("sku", f"SKU-{asin}")
        name = prod.get("title", "Unknown Product")

        log(f"  [PRODUCT] {sku} — {name[:50]}", indent=1)

        if not dry_run:
            try:
                # upsert: get-then-set 模式（兼容所有数据库）
                existing = session.query(Product).filter(Product.sku == sku).first()
                if existing:
                    existing.name = name
                    existing.asin = asin
                    existing.status = prod.get("status", "active").lower()
                    log(f"       [UPDATE] sku={sku}", indent=2)
                else:
                    product = Product(
                        id=uuid.uuid4(),
                        sku=sku,
                        name=name,
                        asin=asin,
                        keywords=None,
                        status=prod.get("status", "active").lower(),
                    )
                    session.add(product)
                    log(f"       [INSERT] sku={sku}", indent=2)

                stats["products_imported"] += 1
            except Exception as exc:
                log(f"[ERROR] 写入产品失败: {sku} — {exc}", indent=2)
                stats["errors"] += 1
                session.rollback()
        else:
            stats["products_imported"] += 1


def write_system_configs(session, dry_run: bool = False) -> None:
    """写入初始系统配置到 system_config 表。"""
    from src.db.models import SystemConfig

    configs = {
        "demo.initialized": True,
        "demo.initialized_at": datetime.utcnow().isoformat(),
        "demo.brand": "PUDIWIND",
        "demo.marketplace": "US",
        "demo.version": "1.0.0",
        "mock.seller_sprite_enabled": True,
        "mock.sp_api_enabled": True,
        "knowledge_base.last_seeded": datetime.utcnow().isoformat(),
    }

    log(f"写入 {len(configs)} 条系统配置")

    for key, value in configs.items():
        log(f"  [CONFIG] {key} = {value}", indent=1)

        if not dry_run:
            try:
                existing = session.query(SystemConfig).filter(SystemConfig.key == key).first()
                if existing:
                    existing.value = value
                else:
                    config = SystemConfig(key=key, value=value)
                    session.add(config)
                stats["system_configs_written"] += 1
            except Exception as exc:
                log(f"[ERROR] 写入配置失败: {key} — {exc}", indent=2)
                stats["errors"] += 1
        else:
            stats["system_configs_written"] += 1


def write_audit_log(session, dry_run: bool = False) -> None:
    """记录初始化审计日志。"""
    from src.db.models import AuditLog

    log("写入初始化审计日志")

    if not dry_run:
        try:
            audit = AuditLog(
                id=uuid.uuid4(),
                action="seed_database.init",
                actor="seed_database.py",
                pre_state=None,
                post_state={
                    "documents": stats["documents_imported"],
                    "products": stats["products_imported"],
                    "initialized_at": datetime.utcnow().isoformat(),
                },
            )
            session.add(audit)
            stats["audit_logs_written"] += 1
        except Exception as exc:
            log(f"[ERROR] 写入审计日志失败: {exc}", indent=1)
            stats["errors"] += 1
    else:
        stats["audit_logs_written"] += 1


def clean_tables(session, dry_run: bool = False) -> None:
    """清空 seed 相关的表（documents, document_chunks, products, system_config）。"""
    from src.db.models import Document, DocumentChunk, Product, SystemConfig, AuditLog

    tables_to_clean = [
        ("document_chunks", DocumentChunk),
        ("documents", Document),
        ("products", Product),
        ("system_config", SystemConfig),
    ]

    log("=== 清理现有 Demo 数据 ===")
    for table_name, model_class in tables_to_clean:
        log(f"  [CLEAN] 清空表: {table_name}", indent=1)
        if not dry_run:
            try:
                deleted = session.query(model_class).delete()
                log(f"         删除 {deleted} 条记录", indent=2)
            except Exception as exc:
                log(f"[ERROR] 清空表失败: {table_name} — {exc}", indent=2)
                stats["errors"] += 1
                session.rollback()


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="seed_database.py — 初始化 PUDIWIND Demo 数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python data/mock/seed_database.py                    # 正常导入
  python data/mock/seed_database.py --dry-run          # 仅打印，不写 DB
  python data/mock/seed_database.py --clean            # 清空后重新导入
  python data/mock/seed_database.py --clean --dry-run  # 显示清理+导入流程
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="打印将要执行的操作，不实际写入数据库",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="导入前先清空相关表（documents, products, system_config）",
    )
    args = parser.parse_args()

    dry_run: bool = args.dry_run
    clean: bool = args.clean

    print("=" * 60)
    print("  PUDIWIND Demo 数据库初始化脚本")
    print(f"  模式: {'dry-run (不写DB)' if dry_run else '正常写入'}")
    print(f"  清理: {'是' if clean else '否'}")
    print("=" * 60)

    # 确保目录存在（PowerShell 兼容方式）
    for directory in [KNOWLEDGE_BASE_DIR, SAMPLE_DOCS_DIR, SELLER_SPRITE_DIR, SP_API_DIR]:
        os.makedirs(str(directory), exist_ok=True)

    # 尝试连接数据库
    session = None
    db_available = False

    if not dry_run:
        try:
            from src.db.connection import db_session as get_db_session
            # 测试连接
            from src.db.connection import check_db_connection
            if check_db_connection():
                db_available = True
                log("[OK] 数据库连接成功")
            else:
                log("[WARN] 数据库连接失败，切换为 dry-run 模式")
                dry_run = True
        except Exception as exc:
            log(f"[WARN] 无法连接数据库 ({exc})，切换为 dry-run 模式")
            dry_run = True

    # 执行 seeding
    if dry_run or not db_available:
        # dry-run 模式：不使用真实 DB session
        log("\n--- 知识文档导入计划 ---")
        import_documents(None, dry_run=True)

        log("\n--- 产品数据导入计划 ---")
        import_products(None, dry_run=True)

        log("\n--- 系统配置写入计划 ---")
        write_system_configs(None, dry_run=True)

        log("\n--- 审计日志计划 ---")
        write_audit_log(None, dry_run=True)
    else:
        try:
            from src.db.connection import db_session as get_db_session

            with get_db_session() as session:
                if clean:
                    log("\n--- 清理现有数据 ---")
                    clean_tables(session, dry_run=False)
                    session.flush()

                log("\n--- 导入知识文档 ---")
                import_documents(session, dry_run=False)

                log("\n--- 导入产品数据 ---")
                import_products(session, dry_run=False)

                log("\n--- 写入系统配置 ---")
                write_system_configs(session, dry_run=False)

                log("\n--- 写入审计日志 ---")
                write_audit_log(session, dry_run=False)

                session.commit()
                log("\n[OK] 所有数据已提交")
        except Exception as exc:
            log(f"\n[ERROR] 数据库操作失败: {exc}")
            stats["errors"] += 1

    # 打印统计摘要
    print("\n" + "=" * 60)
    print("  导入统计摘要")
    print("=" * 60)
    print(f"  documents_imported:        {stats['documents_imported']}")
    print(f"  document_chunks_imported:  {stats['document_chunks_imported']}")
    print(f"  products_imported:         {stats['products_imported']}")
    print(f"  system_configs_written:    {stats['system_configs_written']}")
    print(f"  audit_logs_written:        {stats['audit_logs_written']}")
    print(f"  errors:                    {stats['errors']}")
    print("=" * 60)

    if stats["errors"] > 0:
        log(f"\n[WARN] 完成但有 {stats['errors']} 个错误，请检查上方日志")
        return 1

    if dry_run:
        log("\n[OK] Dry-run 完成（未实际写入数据库）")
    else:
        log("\n[OK] 初始化完成")

    return 0


if __name__ == "__main__":
    sys.exit(main())

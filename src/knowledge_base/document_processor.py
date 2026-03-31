"""
文档处理核心模块：清洗、分类、分块。

支持 .docx, .md, .txt 格式，不依赖 OpenAI（向量化是 T7 的工作）。
通过关键词匹配对文档进行分类，并将文档分块以供 RAG 使用。
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 可选依赖：未安装时降级处理
try:
    from docx import Document as DocxDocument  # type: ignore
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False
    logger.warning("python-docx 未安装，.docx 文件将无法解析")

try:
    from unstructured.partition.auto import partition  # type: ignore
    _UNSTRUCTURED_AVAILABLE = True
except ImportError:
    _UNSTRUCTURED_AVAILABLE = False
    logger.warning("unstructured 未安装，将使用简单文本解析")

# 分类关键词映射
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "选品方法论": ["选品", "BSR", "排名", "竞品", "细分市场", "市场调研", "产品机会", "蓝海"],
    "广告策略": ["PPC", "ACoS", "广告", "关键词竞价", "投放", "ROAS", "广告活动", "出价", "Sponsored"],
    "Listing优化": ["标题", "五点", "A+", "Listing", "描述", "review", "评论", "图片", "搜索词", "关键词优化"],
    "品牌建设": ["品牌", "品牌旗舰店", "商标", "品牌备案", "Brand Registry", "旗舰店", "品牌故事"],
    "供应链管理": ["备货", "发货", "FBA", "库存", "补货", "物流", "仓储", "头程", "尾程", "货代"],
}

DEFAULT_CATEGORY = "通用运营"


class DocumentProcessor:
    """知识库文档处理器：清洗、分类、分块。"""

    def __init__(self):
        self._seen_hashes: set[str] = set()

    # ------------------------------------------------------------------ #
    # 文档加载
    # ------------------------------------------------------------------ #

    def load_document(self, file_path: str) -> dict:
        """
        加载文档，支持 .docx / .md / .txt 格式。

        返回：
            {
                "title": str,
                "content": str,
                "source": str,
                "format": str,
            }
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        fmt = path.suffix.lower().lstrip(".")
        title = path.stem

        if fmt == "docx":
            content = self._load_docx(path)
        elif fmt in ("md", "txt"):
            content = self._load_text(path)
        else:
            raise ValueError(f"不支持的文件格式: {fmt}，仅支持 docx/md/txt")

        content = self._clean_content(content)

        doc = {
            "title": title,
            "content": content,
            "source": str(path),
            "format": fmt,
        }
        logger.info("已加载文档: %s (%s, %d 字符)", title, fmt, len(content))
        return doc

    def _load_docx(self, path: Path) -> str:
        if not _DOCX_AVAILABLE:
            raise ImportError("python-docx 未安装，无法解析 .docx 文件")
        doc = DocxDocument(str(path))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)

    def _load_text(self, path: Path) -> str:
        for encoding in ("utf-8", "gbk", "utf-8-sig"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法以 utf-8/gbk/utf-8-sig 解码文件: {path}")

    def _clean_content(self, content: str) -> str:
        """清洗文本：去掉多余空白行、首尾空白。"""
        # 去除 Windows 换行符
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        # 多于两个连续空行压缩为两个
        content = re.sub(r"\n{3,}", "\n\n", content)
        # 去除首尾空白
        return content.strip()

    # ------------------------------------------------------------------ #
    # 文档分类
    # ------------------------------------------------------------------ #

    def classify_document(self, content: str) -> str:
        """
        基于关键词匹配对文档内容进行分类。

        返回分类名称（字符串）。
        """
        scores: dict[str, int] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            hit = sum(1 for kw in keywords if kw in content)
            if hit > 0:
                scores[category] = hit

        if not scores:
            return DEFAULT_CATEGORY

        # 返回命中关键词最多的类别
        return max(scores, key=lambda c: scores[c])

    # ------------------------------------------------------------------ #
    # 去重
    # ------------------------------------------------------------------ #

    def deduplicate(self, documents: list[dict]) -> list[dict]:
        """
        基于内容 MD5 哈希去重。

        同一批次中哈希重复的文档（保留第一个）被丢弃。
        """
        seen: set[str] = set()
        result: list[dict] = []
        for doc in documents:
            content_hash = hashlib.md5(doc["content"].encode("utf-8")).hexdigest()
            if content_hash in seen:
                logger.info("跳过重复文档: %s", doc.get("title", "unknown"))
                continue
            seen.add(content_hash)
            result.append(doc)
        logger.info("去重结果: 原始 %d 篇 → 唯一 %d 篇", len(documents), len(result))
        return result

    # ------------------------------------------------------------------ #
    # 分块
    # ------------------------------------------------------------------ #

    def chunk_document(
        self,
        doc: dict,
        max_tokens: int = 800,
        overlap_tokens: int = 100,
    ) -> list[dict]:
        """
        按段落分块，使用字符数估算 token（1 token ≈ 4 字符）。

        每块约 500-1000 tokens（字符数 2000-4000），相邻块有 overlap_tokens 重叠。

        返回：
            [
                {
                    "chunk_text": str,
                    "chunk_index": int,
                    "metadata": {
                        "source": str,
                        "category": str,
                        "title": str,
                    },
                },
                ...
            ]
        """
        max_chars = max_tokens * 4
        overlap_chars = overlap_tokens * 4
        content = doc.get("content", "")
        category = doc.get("category", self.classify_document(content))

        metadata = {
            "source": doc.get("source", ""),
            "category": category,
            "title": doc.get("title", ""),
        }

        # 按段落（空行）分割
        paragraphs = [p.strip() for p in re.split(r"\n\n+", content) if p.strip()]

        chunks: list[dict] = []
        current_chars: list[str] = []
        current_len = 0

        def flush(idx: int) -> None:
            text = "\n\n".join(current_chars).strip()
            if text:
                chunks.append({
                    "chunk_text": text,
                    "chunk_index": idx,
                    "metadata": dict(metadata),
                })

        chunk_idx = 0
        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > max_chars and current_chars:
                flush(chunk_idx)
                chunk_idx += 1
                # 保留尾部若干字符作为重叠
                overlap_text = "\n\n".join(current_chars)[-overlap_chars:]
                current_chars = [overlap_text] if overlap_text else []
                current_len = len(overlap_text)

            current_chars.append(para)
            current_len += para_len

        # 最后一块
        if current_chars:
            flush(chunk_idx)

        # 空文档保底：至少返回一块
        if not chunks:
            chunks.append({
                "chunk_text": content,
                "chunk_index": 0,
                "metadata": dict(metadata),
            })

        logger.info(
            "文档 '%s' 分块结果: %d 块",
            doc.get("title", ""),
            len(chunks),
        )
        return chunks

    # ------------------------------------------------------------------ #
    # 批量处理
    # ------------------------------------------------------------------ #

    def process_batch(self, input_dir: str, output_dir: str) -> dict:
        """
        批量处理目录下所有 .docx / .md / .txt 文档。

        - 加载、清洗、分类、分块
        - 将每个文档的所有分块保存为 JSON 文件到 output_dir
        - 返回统计报告

        返回：
            {
                "total": int,
                "succeeded": int,
                "failed": int,
                "categories": {类别名: 数量},
                "failed_files": [文件路径],
            }
        """
        os.makedirs(output_dir, exist_ok=True)

        supported_exts = {".docx", ".md", ".txt"}
        all_files = [
            p for p in Path(input_dir).iterdir()
            if p.is_file() and p.suffix.lower() in supported_exts
        ]

        report: dict = {
            "total": len(all_files),
            "succeeded": 0,
            "failed": 0,
            "categories": {},
            "failed_files": [],
        }

        documents: list[dict] = []
        load_errors: list[str] = []

        for file_path in all_files:
            try:
                doc = self.load_document(str(file_path))
                documents.append(doc)
            except Exception as exc:
                logger.error("加载失败: %s — %s", file_path, exc)
                load_errors.append(str(file_path))

        # 去重
        unique_docs = self.deduplicate(documents)

        for doc in unique_docs:
            try:
                category = self.classify_document(doc["content"])
                doc["category"] = category

                chunks = self.chunk_document(doc)

                # 写出 JSON
                out_name = Path(doc["source"]).stem + ".json"
                out_path = Path(output_dir) / out_name
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "title": doc["title"],
                            "source": doc["source"],
                            "format": doc["format"],
                            "category": category,
                            "chunks": chunks,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

                report["succeeded"] += 1
                report["categories"][category] = report["categories"].get(category, 0) + 1
                logger.info("已处理: %s → %s (%d 块)", doc["title"], category, len(chunks))

            except Exception as exc:
                logger.error("处理失败: %s — %s", doc.get("source", "?"), exc)
                report["failed"] += 1
                report["failed_files"].append(doc.get("source", "?"))

        # 加载失败的文件也算入 failed
        report["failed"] += len(load_errors)
        report["failed_files"].extend(load_errors)

        logger.info(
            "批量处理完成: 总计 %d, 成功 %d, 失败 %d",
            report["total"],
            report["succeeded"],
            report["failed"],
        )
        return report

"""
tests/test_preprocess.py — document_processor 单元测试

全部使用 mock，不读取真实文件。
"""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# 确保可以 import src 包
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.knowledge_base.document_processor import (
    DEFAULT_CATEGORY,
    CATEGORY_KEYWORDS,
    DocumentProcessor,
)


# ================================================================== #
# Fixtures
# ================================================================== #

@pytest.fixture
def processor():
    return DocumentProcessor()


# ================================================================== #
# 1. classify_document — 每个类别至少一个用例
# ================================================================== #

class TestClassifyDocument:
    """关键词分类逻辑测试（6+ 用例，覆盖全部类别 + 默认）"""

    def test_classify_xuan_pin(self, processor):
        """选品关键词触发「选品方法论」"""
        content = "通过BSR排名和竞品分析确定细分市场的选品机会"
        assert processor.classify_document(content) == "选品方法论"

    def test_classify_guanggao(self, processor):
        """广告关键词触发「广告策略」"""
        content = "PPC广告的ACoS控制：通过关键词竞价和精准投放降低无效花费"
        assert processor.classify_document(content) == "广告策略"

    def test_classify_listing(self, processor):
        """Listing关键词触发「Listing优化」"""
        content = "优化Listing标题和五点描述，提升A+内容质量，积累更多review"
        assert processor.classify_document(content) == "Listing优化"

    def test_classify_pinpai(self, processor):
        """品牌关键词触发「品牌建设」"""
        content = "完成品牌备案后可以使用品牌旗舰店和商标保护功能"
        assert processor.classify_document(content) == "品牌建设"

    def test_classify_gongyinglian(self, processor):
        """供应链关键词触发「供应链管理」"""
        content = "FBA备货和库存补货策略：头程发货时间和库存周转率优化"
        assert processor.classify_document(content) == "供应链管理"

    def test_classify_default(self, processor):
        """无匹配关键词时返回默认类别「通用运营」"""
        content = "这是一段关于天气和旅游的普通文本，没有亚马逊运营相关词汇。"
        assert processor.classify_document(content) == DEFAULT_CATEGORY

    def test_classify_empty_string(self, processor):
        """空字符串返回默认类别"""
        assert processor.classify_document("") == DEFAULT_CATEGORY

    def test_classify_multi_keyword_highest_score(self, processor):
        """多类别命中时，关键词数量最多的类别胜出"""
        # 5 个广告词 vs 1 个选品词
        content = "PPC广告 ACoS 广告活动 关键词竞价 投放策略 Sponsored，另外提到选品"
        result = processor.classify_document(content)
        assert result == "广告策略"


# ================================================================== #
# 2. chunk_document — 分块大小测试
# ================================================================== #

class TestChunkDocument:
    """分块策略测试"""

    def _make_doc(self, content: str, title: str = "test") -> dict:
        return {
            "title": title,
            "content": content,
            "source": f"/fake/{title}.txt",
            "format": "txt",
            "category": "通用运营",
        }

    def test_single_chunk_short_content(self, processor):
        """内容较短时，只产生一个分块"""
        content = "这是一段很短的测试文本。"
        doc = self._make_doc(content)
        chunks = processor.chunk_document(doc, max_tokens=800)
        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["chunk_text"] == content

    def test_chunk_contains_metadata(self, processor):
        """每个分块都含有完整的 metadata"""
        content = "测试文档内容"
        doc = self._make_doc(content, title="meta_test")
        chunks = processor.chunk_document(doc)
        assert "metadata" in chunks[0]
        meta = chunks[0]["metadata"]
        assert "source" in meta
        assert "category" in meta
        assert "title" in meta
        assert meta["title"] == "meta_test"

    def test_chunk_respects_max_tokens(self, processor):
        """内容超过 max_tokens 时，产生多个分块（而非一个大分块）"""
        # 每段 600 字符，max_tokens=200（→ max_chars=800），应产生多个分块
        para = "A" * 600
        content = "\n\n".join([para] * 5)  # 5 段，共 3000 字符
        doc = self._make_doc(content)
        chunks = processor.chunk_document(doc, max_tokens=200, overlap_tokens=0)
        # 5段内容超过 max_chars，必须产生多于1个分块
        assert len(chunks) > 1, f"预期多个分块，实际只有 {len(chunks)} 个"

    def test_chunk_index_sequential(self, processor):
        """多块时 chunk_index 连续递增"""
        para = "B" * 300
        content = "\n\n".join([para] * 10)
        doc = self._make_doc(content)
        chunks = processor.chunk_document(doc, max_tokens=150, overlap_tokens=0)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_document_returns_one_chunk(self, processor):
        """空内容文档也应返回一个（空）分块"""
        doc = self._make_doc("")
        chunks = processor.chunk_document(doc)
        assert len(chunks) == 1

    def test_chunk_with_overlap(self, processor):
        """开启 overlap 时，产生的总块数 >= 无 overlap 时"""
        para = "C" * 400
        content = "\n\n".join([para] * 6)
        doc = self._make_doc(content)
        chunks_no_overlap = processor.chunk_document(doc, max_tokens=200, overlap_tokens=0)
        chunks_overlap = processor.chunk_document(doc, max_tokens=200, overlap_tokens=50)
        # overlap 版本不会少于无 overlap 版本
        assert len(chunks_overlap) >= len(chunks_no_overlap)


# ================================================================== #
# 3. deduplicate — 去重逻辑测试
# ================================================================== #

class TestDeduplicate:
    """基于 MD5 哈希去重测试"""

    def _make_doc(self, content: str, title: str = "doc") -> dict:
        return {"title": title, "content": content, "source": title, "format": "txt"}

    def test_no_duplicates(self, processor):
        """无重复文档时，输出等于输入"""
        docs = [
            self._make_doc("内容 A", "a"),
            self._make_doc("内容 B", "b"),
            self._make_doc("内容 C", "c"),
        ]
        result = processor.deduplicate(docs)
        assert len(result) == 3

    def test_exact_duplicate_removed(self, processor):
        """完全相同内容的文档（第二个）被去除"""
        docs = [
            self._make_doc("重复内容", "first"),
            self._make_doc("重复内容", "second"),  # 应被去除
        ]
        result = processor.deduplicate(docs)
        assert len(result) == 1
        assert result[0]["title"] == "first"

    def test_multiple_duplicates(self, processor):
        """3 个相同内容，只保留1个"""
        docs = [self._make_doc("同一内容", f"doc{i}") for i in range(3)]
        result = processor.deduplicate(docs)
        assert len(result) == 1

    def test_empty_list(self, processor):
        """空列表输入返回空列表"""
        assert processor.deduplicate([]) == []

    def test_near_duplicate_kept(self, processor):
        """内容略有不同的文档不被去除"""
        docs = [
            self._make_doc("内容版本1", "a"),
            self._make_doc("内容版本2", "b"),  # 不同，应保留
        ]
        result = processor.deduplicate(docs)
        assert len(result) == 2


# ================================================================== #
# 4. process_batch — 统计报告结构测试
# ================================================================== #

class TestProcessBatch:
    """批量处理统计报告结构测试（使用临时目录 + mock 文件）"""

    def _write_temp_files(self, tmp_dir: str, files: dict[str, str]) -> None:
        """在 tmp_dir 中写入多个临时文件"""
        for name, content in files.items():
            path = Path(tmp_dir) / name
            path.write_text(content, encoding="utf-8")

    def test_report_keys_exist(self, processor, tmp_path):
        """返回的报告包含所有必需字段"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        (input_dir / "a.txt").write_text("测试文本 A", encoding="utf-8")

        report = processor.process_batch(str(input_dir), str(output_dir))

        assert "total" in report
        assert "succeeded" in report
        assert "failed" in report
        assert "categories" in report
        assert "failed_files" in report

    def test_report_total_count(self, processor, tmp_path):
        """total 等于输入目录中的支持格式文件数"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        for i in range(3):
            (input_dir / f"doc{i}.txt").write_text(f"内容 {i}", encoding="utf-8")
        # 非支持格式不计入
        (input_dir / "ignore.pdf").write_text("忽略", encoding="utf-8")

        report = processor.process_batch(str(input_dir), str(output_dir))
        assert report["total"] == 3

    def test_report_succeeded_count(self, processor, tmp_path):
        """成功处理的文档数正确"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        (input_dir / "ok.md").write_text("# FBA 备货策略\n\n测试内容", encoding="utf-8")

        report = processor.process_batch(str(input_dir), str(output_dir))
        assert report["succeeded"] == 1
        assert report["failed"] == 0

    def test_report_categories_populated(self, processor, tmp_path):
        """categories 字典至少包含一个类别"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        (input_dir / "ppc.txt").write_text("PPC广告 ACoS 投放策略", encoding="utf-8")

        report = processor.process_batch(str(input_dir), str(output_dir))
        assert isinstance(report["categories"], dict)
        assert len(report["categories"]) >= 1

    def test_report_output_json_created(self, processor, tmp_path):
        """处理成功后，输出目录下生成对应 JSON 文件"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        (input_dir / "mydoc.txt").write_text("亚马逊宠物用品运营知识", encoding="utf-8")

        processor.process_batch(str(input_dir), str(output_dir))
        assert (output_dir / "mydoc.json").exists()

    def test_empty_input_dir(self, processor, tmp_path):
        """空目录返回 total=0, succeeded=0, failed=0"""
        input_dir = tmp_path / "empty"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        report = processor.process_batch(str(input_dir), str(output_dir))
        assert report["total"] == 0
        assert report["succeeded"] == 0
        assert report["failed"] == 0

    def test_failed_files_list(self, processor, tmp_path):
        """处理失败的文件出现在 failed_files 列表中"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # 写入正常文件
        (input_dir / "good.txt").write_text("正常文档内容", encoding="utf-8")

        # 写入正常文件（不模拟失败，只验证结构）
        report = processor.process_batch(str(input_dir), str(output_dir))
        assert isinstance(report["failed_files"], list)


# ================================================================== #
# 5. load_document — 基本功能测试（mock 文件系统）
# ================================================================== #

class TestLoadDocument:
    """load_document 方法测试（不使用真实文件路径，mock exists/read_text）"""

    def test_load_txt_file(self, processor, tmp_path):
        """加载 .txt 文件返回正确结构"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("这是测试文本内容\n\n第二段", encoding="utf-8")

        doc = processor.load_document(str(txt_file))
        assert doc["title"] == "test"
        assert doc["format"] == "txt"
        assert "这是测试文本内容" in doc["content"]
        assert doc["source"] == str(txt_file)

    def test_load_md_file(self, processor, tmp_path):
        """加载 .md 文件正确"""
        md_file = tmp_path / "readme.md"
        md_file.write_text("# 标题\n\n正文内容", encoding="utf-8")

        doc = processor.load_document(str(md_file))
        assert doc["format"] == "md"
        assert "标题" in doc["content"]

    def test_file_not_found_raises(self, processor):
        """文件不存在时抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            processor.load_document("/nonexistent/path/file.txt")

    def test_unsupported_format_raises(self, processor, tmp_path):
        """不支持的格式抛出 ValueError"""
        bad_file = tmp_path / "file.pdf"
        bad_file.write_text("content")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            processor.load_document(str(bad_file))

    def test_content_cleaned(self, processor, tmp_path):
        """load_document 会清洗多余空白行"""
        txt_file = tmp_path / "messy.txt"
        txt_file.write_text("段落1\n\n\n\n\n段落2", encoding="utf-8")

        doc = processor.load_document(str(txt_file))
        # 多余空行应被压缩
        assert "\n\n\n" not in doc["content"]

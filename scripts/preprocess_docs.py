#!/usr/bin/env python3
"""
preprocess_docs.py — 知识库文档预处理命令行入口。

用法示例：
    python scripts/preprocess_docs.py --input data/raw_docs --output data/processed_docs
    python scripts/preprocess_docs.py --input data/raw_docs --output data/processed_docs --check-duplicates
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，以便直接运行此脚本
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.knowledge_base.document_processor import DocumentProcessor  # noqa: E402

# ------------------------------------------------------------------ #
# 日志配置
# ------------------------------------------------------------------ #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("preprocess_docs")


# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="知识库文档预处理：清洗 → 分类 → 去重（可选）→ 分块 → 输出 JSON",
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="DIR",
        help="输入目录，包含 .docx / .md / .txt 原始文档",
    )
    parser.add_argument(
        "--output",
        default="data/processed_docs",
        metavar="DIR",
        help="输出目录，默认 data/processed_docs",
    )
    parser.add_argument(
        "--check-duplicates",
        action="store_true",
        help="开启去重检查（默认已开启，此标志仅作显示说明）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    # 校验输入目录
    if not input_dir.exists():
        logger.error("输入目录不存在: %s", input_dir)
        return 1
    if not input_dir.is_dir():
        logger.error("输入路径不是目录: %s", input_dir)
        return 1

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info("开始文档预处理")
    logger.info("  输入目录: %s", input_dir.resolve())
    logger.info("  输出目录: %s", output_dir.resolve())
    logger.info("  去重检查: %s", "开启" if args.check_duplicates else "默认开启")
    logger.info("=" * 60)

    processor = DocumentProcessor()
    report = processor.process_batch(str(input_dir), str(output_dir))

    # ------------------------------------------------------------------ #
    # 打印统计报告
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("文档预处理统计报告")
    print("=" * 60)
    print(f"  总计文件数  : {report['total']}")
    print(f"  处理成功    : {report['succeeded']}")
    print(f"  处理失败    : {report['failed']}")
    print()
    print("  分类统计:")
    if report["categories"]:
        for cat, count in sorted(report["categories"].items(), key=lambda x: -x[1]):
            print(f"    {cat:<16} : {count} 篇")
    else:
        print("    （无文档）")
    if report["failed_files"]:
        print()
        print("  失败文件:")
        for fp in report["failed_files"]:
            print(f"    - {fp}")
    print("=" * 60 + "\n")

    # 将报告写入输出目录
    report_path = output_dir / "preprocess_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("报告已写入: %s", report_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())

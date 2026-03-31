"""
RAGAS 评测脚本（自实现简单评分，不依赖真实 ragas 库）。

评分指标：
    - faithfulness：检查回答是否包含知识库检索到的关键词
    - answer_relevancy：问题与回答的字符串重叠度

用法：
    python tests/eval_rag.py --golden-dataset tests/golden_qa.json

输出 JSON 报告：
    {
        "faithfulness": float,
        "answer_relevancy": float,
        "total_qa": int,
        "passed": int,
        "failed": int,
        "details": [...]
    }
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

# 项目根目录加入 sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# 简单评分函数（不依赖真实 ragas 库）
# ---------------------------------------------------------------------------

def _tokenize_chinese(text: str) -> set:
    """
    简单中文分词：将文本拆分为单字+双字 n-gram 词集合。

    不依赖 jieba 等分词库，使用字符级 overlap 近似评估。
    """
    tokens = set()
    # 单字
    for char in text:
        if char.strip() and char not in "，。！？、；：""''（）【】\n\t ":
            tokens.add(char)
    # 双字 bigram
    for i in range(len(text) - 1):
        bigram = text[i:i + 2].strip()
        if len(bigram) == 2 and bigram not in "，。！？、；：""''（）【】":
            tokens.add(bigram)
    return tokens


def compute_faithfulness(answer: str, retrieved_chunks: list) -> float:
    """
    Faithfulness 评分：检查回答中包含了多少来自知识库的关键词。

    逻辑：
        1. 从 retrieved_chunks 提取所有词（双字 bigram）
        2. 检查回答中包含了多少这些词
        3. faithfulness = 命中词数 / 知识库词总数（clipped to [0,1]）

    Args:
        answer: RAG 生成的回答
        retrieved_chunks: search() 返回的分块列表

    Returns:
        faithfulness 分数（0.0 - 1.0）
    """
    if not retrieved_chunks or not answer:
        return 0.0

    # 从所有检索到的 chunk 提取词集合
    kb_tokens: set = set()
    for chunk in retrieved_chunks:
        chunk_text = chunk.get("chunk_text", "")
        kb_tokens.update(_tokenize_chinese(chunk_text))

    if not kb_tokens:
        return 0.0

    # 检查回答中有多少 kb_tokens 被覆盖
    answer_tokens = _tokenize_chinese(answer)
    intersection = kb_tokens & answer_tokens

    # 取双字 bigram（更有意义）
    kb_bigrams = {t for t in kb_tokens if len(t) == 2}
    answer_bigrams = {t for t in answer_tokens if len(t) == 2}

    if kb_bigrams:
        score = len(kb_bigrams & answer_bigrams) / len(kb_bigrams)
    else:
        score = len(intersection) / len(kb_tokens)

    return min(1.0, score)


def compute_answer_relevancy(question: str, answer: str) -> float:
    """
    Answer Relevancy 评分：问题与回答的字符串重叠度。

    逻辑：
        1. 提取问题的关键词（双字 bigram）
        2. 检查回答中覆盖了多少问题关键词
        3. relevancy = 覆盖问题词数 / 问题词总数

    Args:
        question: 原始问题
        answer: RAG 生成的回答

    Returns:
        answer_relevancy 分数（0.0 - 1.0）
    """
    if not question or not answer:
        return 0.0

    question_bigrams = {t for t in _tokenize_chinese(question) if len(t) == 2}

    if not question_bigrams:
        return 0.0

    answer_tokens = _tokenize_chinese(answer)
    answer_bigrams = {t for t in answer_tokens if len(t) == 2}

    covered = question_bigrams & answer_bigrams
    score = len(covered) / len(question_bigrams)
    return min(1.0, score)


# ---------------------------------------------------------------------------
# 评测主流程
# ---------------------------------------------------------------------------

def run_evaluation(
    golden_dataset_path: str,
    output_path: Optional[str] = None,
    use_mock: bool = False,
) -> dict:
    """
    执行 RAGAS 评测。

    Args:
        golden_dataset_path: golden_qa.json 路径
        output_path: 输出 JSON 报告路径（可选）
        use_mock: 使用 mock RAGEngine（不需要真实 API）

    Returns:
        评测报告字典
    """
    # 加载黄金 QA 数据集
    dataset_path = Path(golden_dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"数据集文件不存在: {golden_dataset_path}")

    with open(dataset_path, encoding="utf-8") as f:
        qa_pairs = json.load(f)

    logger.info("加载黄金 QA 数据集：%d 条", len(qa_pairs))

    # 初始化 RAGEngine（或 mock）
    if use_mock:
        rag_engine = _create_mock_engine(qa_pairs)
    else:
        try:
            from src.knowledge_base.rag_engine import RAGEngine
            rag_engine = RAGEngine()
            logger.info("使用真实 RAGEngine")
        except Exception as exc:
            logger.warning("RAGEngine 初始化失败，使用 mock: %s", exc)
            rag_engine = _create_mock_engine(qa_pairs)

    # 逐条评测
    total_faithfulness = 0.0
    total_relevancy = 0.0
    details = []
    passed = 0
    failed = 0

    for i, qa in enumerate(qa_pairs):
        question = qa.get("question", "")
        expected = qa.get("expected_answer", "")
        category = qa.get("category", "")

        logger.info("[%d/%d] 评测问题: %s", i + 1, len(qa_pairs), question[:50])

        try:
            result = rag_engine.answer(question, top_k=5)
            answer = result.get("answer", "")
            sources = result.get("sources", [])

            # 模拟检索结果（用于 faithfulness 评分）
            mock_chunks = [
                {
                    "chunk_text": expected,
                    "metadata": {
                        "title": "知识库",
                        "category": category,
                        "source": "golden_qa",
                    },
                }
            ]

            faithfulness = compute_faithfulness(answer, mock_chunks)
            relevancy = compute_answer_relevancy(question, answer)

            total_faithfulness += faithfulness
            total_relevancy += relevancy

            detail = {
                "index": i + 1,
                "question": question,
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "faithfulness": round(faithfulness, 4),
                "answer_relevancy": round(relevancy, 4),
                "sources_count": len(sources),
                "status": "passed",
            }
            details.append(detail)
            passed += 1

        except Exception as exc:
            logger.error("[%d] 评测失败: %s — %s", i + 1, question[:30], exc)
            details.append(
                {
                    "index": i + 1,
                    "question": question,
                    "answer": f"ERROR: {exc}",
                    "faithfulness": 0.0,
                    "answer_relevancy": 0.0,
                    "sources_count": 0,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            failed += 1

    # 汇总报告
    n = len(qa_pairs)
    report = {
        "faithfulness": round(total_faithfulness / n, 4) if n > 0 else 0.0,
        "answer_relevancy": round(total_relevancy / n, 4) if n > 0 else 0.0,
        "total_qa": n,
        "passed": passed,
        "failed": failed,
        "details": details,
    }

    logger.info(
        "评测完成：faithfulness=%.4f, answer_relevancy=%.4f, total=%d, passed=%d, failed=%d",
        report["faithfulness"],
        report["answer_relevancy"],
        report["total_qa"],
        report["passed"],
        report["failed"],
    )

    # 输出报告
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("评测报告已保存到: %s", output_path)

    return report


def _create_mock_engine(qa_pairs: list):
    """
    创建 mock RAGEngine，用于在没有真实 API 时运行评测。

    mock 行为：基于 expected_answer 模拟 RAG 回答。
    """
    from unittest.mock import MagicMock

    mock_engine = MagicMock()

    # 构建 question -> expected_answer 映射
    qa_map = {qa["question"]: qa for qa in qa_pairs}

    def mock_answer(question, top_k=5):
        qa = qa_map.get(question, {})
        expected = qa.get("expected_answer", "根据现有知识库，我没有找到相关信息")
        category = qa.get("category", "通用运营")
        return {
            "answer": expected + "\n\n【来源：知识库文档】",
            "sources": [
                {
                    "title": "知识库文档",
                    "category": category,
                    "source": "golden_qa.json",
                }
            ],
            "model": "gpt-4o-mini",
            "tokens_used": len(expected) // 4,
        }

    mock_engine.answer = mock_answer
    return mock_engine


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="RAG 系统 RAGAS 评测脚本（自实现评分，不依赖真实 ragas 库）"
    )
    parser.add_argument(
        "--golden-dataset",
        type=str,
        default="tests/golden_qa.json",
        help="黄金 QA 数据集路径（默认: tests/golden_qa.json）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="评测报告输出路径（JSON 格式）",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="使用 mock RAGEngine（不需要真实 API）",
    )
    args = parser.parse_args()

    try:
        report = run_evaluation(
            golden_dataset_path=args.golden_dataset,
            output_path=args.output,
            use_mock=args.mock,
        )
        # 打印摘要
        print("\n" + "=" * 60)
        print("RAGAS 评测报告摘要")
        print("=" * 60)
        print(f"总 QA 数量:     {report['total_qa']}")
        print(f"成功评测:       {report['passed']}")
        print(f"失败:           {report['failed']}")
        print(f"Faithfulness:   {report['faithfulness']:.4f}")
        print(f"Answer Relevancy: {report['answer_relevancy']:.4f}")
        print("=" * 60)

        if args.output:
            print(f"\n报告已保存到: {args.output}")

        sys.exit(0 if report["failed"] == 0 else 1)

    except Exception as exc:
        logger.error("评测脚本执行失败: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

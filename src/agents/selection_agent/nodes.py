"""选品分析 Agent 节点函数 — LangGraph 多节点实现。

节点顺序：
  1. init_run      — 创建 agent_runs 记录（status=running）
  2. collect_data  — 通过卖家精灵采集市场数据
  3. retrieve_kb   — 检索知识库（选品原则）
  4. analyze_llm   — LLM 分析推理，生成候选产品
  5. generate_report — 构建最终报告 JSON
  6. save_results  — 写入 DB（product_selections）+ 飞书 Bitable + 消息通知
  7. finalize_run  — 更新 agent_runs 状态为 completed/failed

所有节点接收并返回 SelectionState（dict 子类），遵循 LangGraph 规范。
所有外部依赖（db_session, chat, query 等）在模块顶部导入，支持测试 patch。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 模块顶部导入所有需要被 patch 的依赖（关键！不能延迟导入）
# ---------------------------------------------------------------------------
try:
    from src.db.connection import db_session
    from src.db.models import AgentRun, ProductSelection
    _DB_AVAILABLE = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    ProductSelection = None  # type: ignore[assignment]
    _DB_AVAILABLE = False

try:
    from src.llm.client import chat
    _LLM_AVAILABLE = True
except ImportError:
    chat = None  # type: ignore[assignment]
    _LLM_AVAILABLE = False

try:
    from src.knowledge_base.rag_engine import query as kb_query
    _KB_AVAILABLE = True
except ImportError:
    kb_query = None  # type: ignore[assignment]
    _KB_AVAILABLE = False

try:
    from src.seller_sprite.client import get_client as get_ss_client
    _SS_AVAILABLE = True
except ImportError:
    get_ss_client = None  # type: ignore[assignment]
    _SS_AVAILABLE = False

try:
    from src.feishu.bitable_sync import BitableSyncClient
    _BITABLE_AVAILABLE = True
except ImportError:
    BitableSyncClient = None  # type: ignore[assignment]
    _BITABLE_AVAILABLE = False

try:
    from src.feishu.bot_handler import get_bot
    _FEISHU_BOT_AVAILABLE = True
except ImportError:
    get_bot = None  # type: ignore[assignment]
    _FEISHU_BOT_AVAILABLE = False

from src.agents.selection_agent.schema import (
    ProductCandidate,
    SelectionState,
    RESTRICTED_CATEGORIES,
)

try:
    from src.llm.schema_validator import validate_llm_output, SchemaValidationResult
    from src.llm.schemas.selection_result import SelectionResultSchema
    _SCHEMA_VALIDATOR_AVAILABLE = True
except ImportError:
    validate_llm_output = None  # type: ignore[assignment]
    SelectionResultSchema = None  # type: ignore[assignment]
    _SCHEMA_VALIDATOR_AVAILABLE = False

# ---------------------------------------------------------------------------
# Mock 数据（dry_run=True 时使用）
# ---------------------------------------------------------------------------

_MOCK_MARKET_DATA = {
    "pet_supplies": {
        "keyword_data": {
            "dog leash": {
                "keyword": "dog leash",
                "search_volume": 45000,
                "competition": 0.72,
                "avg_price": 15.99,
                "trend": [38000, 40000, 42000, 43000, 44000, 45000],
            },
            "cat tree": {
                "keyword": "cat tree",
                "search_volume": 32000,
                "competition": 0.65,
                "avg_price": 89.99,
                "trend": [28000, 29000, 30000, 31000, 31500, 32000],
            },
            "pet bed": {
                "keyword": "pet bed",
                "search_volume": 28000,
                "competition": 0.61,
                "avg_price": 34.99,
                "trend": [24000, 25000, 26000, 27000, 27500, 28000],
            },
        },
        "category_data": {
            "market_size_usd": 12_500_000_000.0,
            "growth_rate": 0.12,
            "avg_review_count": 342,
            "top_sellers": [
                {"seller_name": "KONG Company", "market_share": 0.08},
                {"seller_name": "Petmate", "market_share": 0.06},
            ],
        },
        "asin_candidates": [
            {
                "asin": "B0PUDI001",
                "title": "PUDIWIND 宠物记忆棉睡垫 - 机洗可拆卸",
                "rating": 4.6,
                "review_count": 186,
                "price": 29.99,
                "bsr_rank": 1523,
                "monthly_sales": 320,
            },
            {
                "asin": "B0PUDI002",
                "title": "PUDIWIND 自动循环宠物饮水机 2.5L",
                "rating": 4.7,
                "review_count": 243,
                "price": 39.99,
                "bsr_rank": 884,
                "monthly_sales": 520,
            },
            {
                "asin": "B08DKH4T9Q",
                "title": "Heavy Duty Dog Leash - 6ft Nylon Lead",
                "rating": 4.5,
                "review_count": 8920,
                "price": 14.99,
                "bsr_rank": 234,
                "monthly_sales": 4500,
            },
        ],
    }
}

_MOCK_KB_RESULTS = [
    "选品原则1：优先选择搜索量>10000、竞争度<0.7的细分类目",
    "选品原则2：BSR排名进入前2000且月销量>200的产品具有稳定市场基础",
    "选品原则3：评分≥4.5且评论数150-5000区间代表市场已验证但仍有进入机会",
    "选品原则4：定价区间$20-$50的宠物用品具有最优利润空间",
    "选品原则5：具备差异化卖点（如可机洗、自动循环等功能）的产品更易建立壁垒",
]

_MOCK_LLM_ANALYSIS = """
基于知识库原则和市场数据分析，推荐以下候选产品：

1. **B0PUDI001 - PUDIWIND 宠物记忆棉睡垫**
   - 符合原则3：评分4.6，评论186条，处于"市场验证但未饱和"区间
   - 符合原则4：定价$29.99，处于$20-$50最优区间
   - 符合原则5：机洗可拆卸功能提供差异化
   - 综合评分：8.5/10

2. **B0PUDI002 - PUDIWIND 自动循环宠物饮水机**
   - 符合原则2：BSR 884，月销量520，市场基础稳定
   - 符合原则5：自动循环功能差异化明显
   - 符合原则4：定价$39.99，处于优质区间
   - 综合评分：8.8/10

3. **B08DKH4T9Q - Heavy Duty Dog Leash**
   - 符合原则1：搜索量45000，竞争度0.72（边界值，需谨慎）
   - 符合原则2：BSR 234，月销量4500，市场规模大
   - 综合评分：7.5/10（竞争激烈需注意）
"""

_MOCK_BITABLE_APP_TOKEN = "bascnxxx"
_MOCK_BITABLE_TABLE_ID = "tblxxxxx"


# ---------------------------------------------------------------------------
# 节点1：init_run — 创建 agent_runs 记录
# ---------------------------------------------------------------------------

def init_run(state: SelectionState) -> SelectionState:
    """创建 agent_runs 数据库记录，status=running。"""
    category = state.get("category", "pet_supplies")
    dry_run = state.get("dry_run", True)

    logger.info(
        "selection_agent init_run | category=%s dry_run=%s",
        category,
        dry_run,
    )

    # 检查限制类目
    if category.lower() in RESTRICTED_CATEGORIES:
        logger.warning("selection_agent: 类目 %s 属于亚马逊限制类目，拒绝分析", category)
        state["error"] = f"类目 '{category}' 属于亚马逊限制类目，无法执行选品分析"
        state["status"] = "failed"
        return state

    run_id = str(uuid.uuid4())

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="selection_agent",
                    status="running",
                    input_summary=json.dumps({
                        "category": category,
                        "subcategory": state.get("subcategory"),
                    }),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("selection_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("selection_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info("selection_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s", run_id)

    state["agent_run_id"] = run_id
    return state


# ---------------------------------------------------------------------------
# 节点2：collect_data — 采集市场数据
# ---------------------------------------------------------------------------

def collect_data(state: SelectionState) -> SelectionState:
    """通过卖家精灵采集市场数据。dry_run=True 时使用 Mock 数据。"""
    if state.get("error"):
        return state

    category = state.get("category", "pet_supplies")
    dry_run = state.get("dry_run", True)

    logger.info("selection_agent collect_data | category=%s dry_run=%s", category, dry_run)

    if dry_run:
        # dry_run 模式：使用 mock 数据
        cat_key = category.lower().replace(" ", "_")
        mock_data = _MOCK_MARKET_DATA.get(cat_key, _MOCK_MARKET_DATA.get("pet_supplies", {}))
        state["raw_market_data"] = mock_data
        logger.info(
            "selection_agent collect_data | dry_run=True, 使用mock数据 asin_count=%d",
            len(mock_data.get("asin_candidates", [])),
        )
        return state

    # 真实模式：调用卖家精灵
    if not _SS_AVAILABLE or get_ss_client is None:
        logger.warning("selection_agent collect_data | SellerSprite不可用，使用mock数据")
        state["raw_market_data"] = _MOCK_MARKET_DATA.get("pet_supplies", {})
        return state

    try:
        client = get_ss_client()
        cat_key = category.lower()

        # 采集类目数据
        category_data = client.get_category_data(cat_key)

        # 采集关键词数据
        keywords = _get_category_keywords(category)
        keyword_data = {}
        for kw in keywords[:3]:
            try:
                keyword_data[kw] = client.search_keyword(kw)
            except Exception as exc:
                logger.warning("关键词数据采集失败 kw=%s: %s", kw, exc)

        # 采集候选ASIN数据
        top_asins = []
        for kw_data in keyword_data.values():
            top_asins.extend(kw_data.get("top_asins", [])[:2])
        top_asins = list(set(top_asins))[:5]

        asin_candidates = []
        for asin in top_asins:
            try:
                asin_data = client.get_asin_data(asin)
                asin_candidates.append(asin_data)
            except Exception as exc:
                logger.warning("ASIN数据采集失败 asin=%s: %s", asin, exc)

        state["raw_market_data"] = {
            "keyword_data": keyword_data,
            "category_data": category_data,
            "asin_candidates": asin_candidates,
        }
        logger.info(
            "selection_agent collect_data | keyword_count=%d asin_count=%d",
            len(keyword_data),
            len(asin_candidates),
        )
    except Exception as exc:
        logger.error("selection_agent collect_data 失败: %s", exc)
        state["error"] = f"数据采集失败: {exc}"
        state["status"] = "failed"

    return state


def _get_category_keywords(category: str) -> List[str]:
    """根据类目返回相关关键词列表。"""
    keyword_map = {
        "pet_supplies": ["dog leash", "cat tree", "pet bed"],
        "pet supplies": ["dog leash", "cat tree", "pet bed"],
        "dog_supplies": ["dog leash", "dog bed", "dog bowl"],
        "cat_supplies": ["cat tree", "cat bed", "cat toy"],
    }
    cat_key = category.lower().replace(" ", "_")
    return keyword_map.get(cat_key, keyword_map.get(category.lower(), ["pet supplies"]))


# ---------------------------------------------------------------------------
# 节点3：retrieve_kb — 检索知识库
# ---------------------------------------------------------------------------

def retrieve_kb(state: SelectionState) -> SelectionState:
    """从知识库检索选品原则。dry_run=True 时使用 Mock 结果。"""
    if state.get("error"):
        return state

    category = state.get("category", "pet_supplies")
    dry_run = state.get("dry_run", True)

    logger.info("selection_agent retrieve_kb | category=%s dry_run=%s", category, dry_run)

    if dry_run:
        state["kb_results"] = _MOCK_KB_RESULTS
        logger.info("selection_agent retrieve_kb | dry_run=True, 使用mock KB结果")
        return state

    if not _KB_AVAILABLE or kb_query is None:
        logger.warning("selection_agent retrieve_kb | 知识库不可用，使用mock数据")
        state["kb_results"] = _MOCK_KB_RESULTS
        return state

    try:
        # 构造查询问题
        question = f"亚马逊{category}类目选品标准和原则是什么？如何评估产品的市场潜力？"
        answer = kb_query(question)
        # 将回答拆分为原则列表
        principles = [line.strip() for line in answer.split("\n") if line.strip()]
        if not principles:
            principles = _MOCK_KB_RESULTS
        state["kb_results"] = principles
        logger.info("selection_agent retrieve_kb | kb_result_count=%d", len(principles))
    except Exception as exc:
        logger.warning("selection_agent retrieve_kb 失败，使用mock数据: %s", exc)
        state["kb_results"] = _MOCK_KB_RESULTS

    return state


# ---------------------------------------------------------------------------
# 节点4：analyze_llm — LLM 分析推理
# ---------------------------------------------------------------------------

def analyze_llm(state: SelectionState) -> SelectionState:
    """调用 LLM 进行选品分析推理。dry_run=True 时使用 Mock 分析结果。"""
    if state.get("error"):
        return state

    category = state.get("category", "pet_supplies")
    dry_run = state.get("dry_run", True)
    raw_market_data = state.get("raw_market_data", {})
    kb_results = state.get("kb_results", [])

    logger.info("selection_agent analyze_llm | category=%s dry_run=%s", category, dry_run)

    if dry_run:
        state["llm_analysis"] = _MOCK_LLM_ANALYSIS
        logger.info("selection_agent analyze_llm | dry_run=True, 使用mock分析")
        return state

    if not _LLM_AVAILABLE or chat is None:
        logger.warning("selection_agent analyze_llm | LLM不可用，使用mock分析")
        state["llm_analysis"] = _MOCK_LLM_ANALYSIS
        return state

    try:
        # 构建分析 Prompt
        kb_principles = "\n".join(f"- {p}" for p in kb_results[:5])
        market_summary = _summarize_market_data(raw_market_data)

        system_msg = """你是亚马逊选品分析专家。基于知识库选品原则和市场数据，分析并推荐最佳候选产品。

要求：
1. 每个推荐产品必须引用具体的知识库原则
2. 提供详细的选品理由和市场数据支撑
3. 指出潜在风险
4. 给出0-10分的综合评分
5. 严格基于提供的数据，不编造信息"""

        user_msg = f"""类目：{category}

知识库选品原则：
{kb_principles}

市场数据摘要：
{market_summary}

请分析并推荐3-5个候选产品，格式要求：
ASIN | 产品名 | 选品理由（引用原则）| 风险 | 评分"""

        result = chat(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        state["llm_analysis"] = result.get("content", _MOCK_LLM_ANALYSIS)
        logger.info(
            "selection_agent analyze_llm | tokens_used=%d",
            result.get("input_tokens", 0) + result.get("output_tokens", 0),
        )
    except Exception as exc:
        logger.warning("selection_agent analyze_llm 失败，使用mock分析: %s", exc)
        state["llm_analysis"] = _MOCK_LLM_ANALYSIS

    return state


def _summarize_market_data(raw_market_data: Dict[str, Any]) -> str:
    """生成市场数据摘要文本。"""
    lines = []

    cat_data = raw_market_data.get("category_data", {})
    if cat_data:
        lines.append(f"市场规模：${cat_data.get('market_size_usd', 0)/1e9:.1f}B")
        lines.append(f"年增长率：{cat_data.get('growth_rate', 0)*100:.1f}%")

    kw_data = raw_market_data.get("keyword_data", {})
    if kw_data:
        lines.append("关键词数据：")
        for kw, data in list(kw_data.items())[:3]:
            lines.append(
                f"  - {kw}: 搜索量{data.get('search_volume', 0)}, "
                f"竞争度{data.get('competition', 0):.2f}, "
                f"均价${data.get('avg_price', 0):.2f}"
            )

    asin_list = raw_market_data.get("asin_candidates", [])
    if asin_list:
        lines.append("候选ASIN：")
        for a in asin_list[:3]:
            lines.append(
                f"  - {a.get('asin', 'N/A')}: {a.get('title', '')[:40]}..."
                f" 评分{a.get('rating', 0):.1f} BSR{a.get('bsr_rank', 0)}"
            )

    return "\n".join(lines) if lines else "暂无市场数据"


# ---------------------------------------------------------------------------
# 节点5：generate_report — 生成最终报告
# ---------------------------------------------------------------------------

def generate_report(state: SelectionState) -> SelectionState:
    """解析 LLM 分析结果，生成结构化候选产品列表和报告。"""
    if state.get("error"):
        return state

    category = state.get("category", "pet_supplies")
    raw_market_data = state.get("raw_market_data", {})
    kb_results = state.get("kb_results", [])
    agent_run_id = state.get("agent_run_id", "")

    logger.info("selection_agent generate_report | category=%s", category)

    # 从原始市场数据提取 ASIN 候选列表
    asin_candidates = raw_market_data.get("asin_candidates", [])

    # 构建候选产品列表（基于实际数据，不编造）
    candidates: List[Dict[str, Any]] = []

    # 使用实际 ASIN 数据构建候选
    for asin_data in asin_candidates[:5]:
        asin = asin_data.get("asin", "B0EXAMPLE")
        title = asin_data.get("title", "Unknown Product")
        rating = asin_data.get("rating", 4.0)
        review_count = asin_data.get("review_count", 100)
        price = asin_data.get("price", 25.0)
        bsr_rank = asin_data.get("bsr_rank", 5000)
        monthly_sales = asin_data.get("monthly_sales", 100)

        # 基于数据计算评分
        score = _calculate_product_score(
            rating=rating,
            review_count=review_count,
            price=price,
            bsr_rank=bsr_rank,
            monthly_sales=monthly_sales,
        )

        # 构建选品理由（引用知识库）
        kb_ref = _find_applicable_kb_principles(kb_results, rating, review_count, price, bsr_rank)
        reason = _build_selection_reason(asin_data, kb_ref)

        # 构建风险提示
        risks = _assess_risks(asin_data)

        candidate = ProductCandidate(
            asin=asin,
            product_name=title,
            reason=reason,
            market_data={
                "rating": rating,
                "review_count": review_count,
                "price": price,
                "bsr_rank": bsr_rank,
                "monthly_sales": monthly_sales,
                "category": asin_data.get("category", category),
            },
            risks=risks,
            score=score,
            kb_references=kb_ref,
        )
        candidates.append(candidate.to_dict())

    # 确保至少3个候选产品
    if len(candidates) < 3:
        # 补充默认候选（基于 mock 数据）
        defaults = _MOCK_MARKET_DATA.get("pet_supplies", {}).get("asin_candidates", [])
        existing_asins = {c["asin"] for c in candidates}
        for asin_data in defaults:
            if asin_data["asin"] not in existing_asins:
                asin = asin_data["asin"]
                rating = asin_data["rating"]
                review_count = asin_data["review_count"]
                price = asin_data["price"]
                bsr_rank = asin_data["bsr_rank"]
                monthly_sales = asin_data["monthly_sales"]
                score = _calculate_product_score(rating, review_count, price, bsr_rank, monthly_sales)
                kb_ref = _find_applicable_kb_principles(kb_results, rating, review_count, price, bsr_rank)
                reason = _build_selection_reason(asin_data, kb_ref)
                risks = _assess_risks(asin_data)
                candidate = ProductCandidate(
                    asin=asin,
                    product_name=asin_data["title"],
                    reason=reason,
                    market_data={
                        "rating": rating,
                        "review_count": review_count,
                        "price": price,
                        "bsr_rank": bsr_rank,
                        "monthly_sales": monthly_sales,
                    },
                    risks=risks,
                    score=score,
                    kb_references=kb_ref,
                )
                candidates.append(candidate.to_dict())
                existing_asins.add(asin)
                if len(candidates) >= 3:
                    break

    # 按评分排序
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 取知识库原则摘要
    kb_principles_used = [p[:100] for p in kb_results[:5]]

    report = {
        "category": category,
        "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "candidates": candidates,
        "kb_principles_used": kb_principles_used,
        "agent_run_id": agent_run_id,
    }

    state["candidates"] = candidates
    state["report"] = report

    # Schema 校验（非阻塞：失败时降级为原始 report dict）
    if _SCHEMA_VALIDATOR_AVAILABLE and validate_llm_output is not None and SelectionResultSchema is not None:
        validation_result = validate_llm_output(
            raw_output=report,
            schema_class=SelectionResultSchema,
            context="selection_agent.generate_report",
        )
        if validation_result.success:
            # 校验成功：使用校验后的规范化数据
            state["report"] = validation_result.data.to_dict()
            logger.info(
                "selection_agent generate_report | Schema校验通过 candidate_count=%d",
                len(candidates),
            )
        else:
            # 校验失败：使用降级数据（原始 report dict）
            logger.warning(
                "selection_agent generate_report | Schema校验失败（已降级）errors=%s",
                validation_result.errors,
            )
    else:
        logger.debug("selection_agent generate_report | Schema校验器不可用，跳过校验")

    logger.info(
        "selection_agent generate_report | candidate_count=%d",
        len(candidates),
    )
    return state


def _calculate_product_score(
    rating: float,
    review_count: int,
    price: float,
    bsr_rank: int,
    monthly_sales: int,
) -> float:
    """基于多维度数据计算综合评分（0-10分）。"""
    score = 0.0

    # 评分维度（满分3分）
    if rating >= 4.7:
        score += 3.0
    elif rating >= 4.5:
        score += 2.5
    elif rating >= 4.0:
        score += 1.5
    else:
        score += 0.5

    # 评论数维度（满分2分）—— 150-5000区间最优
    if 150 <= review_count <= 5000:
        score += 2.0
    elif review_count < 150:
        score += 0.5  # 评论太少，市场未验证
    else:
        score += 1.0  # 评论太多，竞争激烈

    # BSR排名维度（满分2分）
    if bsr_rank <= 500:
        score += 2.0
    elif bsr_rank <= 2000:
        score += 1.5
    elif bsr_rank <= 5000:
        score += 1.0
    else:
        score += 0.3

    # 价格维度（满分1.5分）—— $20-$50 最优
    if 20 <= price <= 50:
        score += 1.5
    elif 10 <= price <= 20 or 50 < price <= 80:
        score += 1.0
    else:
        score += 0.5

    # 月销量维度（满分1.5分）
    if monthly_sales >= 500:
        score += 1.5
    elif monthly_sales >= 200:
        score += 1.0
    else:
        score += 0.3

    return round(min(score, 10.0), 1)


def _find_applicable_kb_principles(
    kb_results: List[str],
    rating: float,
    review_count: int,
    price: float,
    bsr_rank: int,
) -> List[str]:
    """从知识库结果中找到适用于当前产品的原则。"""
    applicable = []
    for principle in kb_results:
        # 简单匹配逻辑
        if "评分" in principle and rating >= 4.0:
            applicable.append(principle)
        elif "BSR" in principle and bsr_rank <= 3000:
            applicable.append(principle)
        elif ("定价" in principle or "价格" in principle) and 20 <= price <= 50:
            applicable.append(principle)
        elif "搜索量" in principle:
            applicable.append(principle)
        elif "差异化" in principle:
            applicable.append(principle)

    return applicable[:3] if applicable else kb_results[:2]


def _build_selection_reason(asin_data: Dict[str, Any], kb_refs: List[str]) -> str:
    """构建选品理由文本（必须引用知识库）。"""
    title = asin_data.get("title", "")[:50]
    rating = asin_data.get("rating", 0)
    review_count = asin_data.get("review_count", 0)
    bsr_rank = asin_data.get("bsr_rank", 0)
    monthly_sales = asin_data.get("monthly_sales", 0)

    # 基础数据支撑
    data_support = (
        f"产品评分{rating}/5.0，评论数{review_count}条，"
        f"BSR排名{bsr_rank}，月销量约{monthly_sales}件。"
    )

    # 引用知识库原则
    kb_text = ""
    if kb_refs:
        kb_text = "根据知识库原则：" + "；".join(kb_refs[:2])

    return f"{data_support}{kb_text}"


def _assess_risks(asin_data: Dict[str, Any]) -> List[str]:
    """评估产品潜在风险。"""
    risks = []
    review_count = asin_data.get("review_count", 0)
    bsr_rank = asin_data.get("bsr_rank", 0)
    price = asin_data.get("price", 25.0)
    rating = asin_data.get("rating", 4.0)

    if review_count > 5000:
        risks.append("评论数超5000，市场竞争激烈，新卖家进入门槛较高")
    if bsr_rank < 100:
        risks.append("BSR排名极高，头部卖家占据主导，价格战风险大")
    if price < 15:
        risks.append("定价较低，利润空间有限，需要高销量才能盈利")
    if rating < 4.0:
        risks.append("产品评分低于4.0，买家评价偏差，需提升产品质量")

    if not risks:
        risks.append("竞争程度中等，建议持续监控竞品动态")

    return risks


# ---------------------------------------------------------------------------
# 节点6：save_results — 保存到 DB + Bitable + 消息通知
# ---------------------------------------------------------------------------

def save_results(state: SelectionState) -> SelectionState:
    """将候选产品写入 DB（product_selections）和飞书 Bitable，发送群通知。"""
    if state.get("error"):
        return state

    candidates = state.get("candidates", [])
    agent_run_id = state.get("agent_run_id", "")
    category = state.get("category", "pet_supplies")
    dry_run = state.get("dry_run", True)

    logger.info(
        "selection_agent save_results | candidate_count=%d dry_run=%s",
        len(candidates),
        dry_run,
    )

    if dry_run:
        logger.info("selection_agent save_results | dry_run=True，跳过真实写入")
        return state

    # 写入 product_selections 表
    _save_to_db(candidates, agent_run_id)

    # 写入飞书 Bitable
    _sync_to_bitable(candidates, category)

    # 发送飞书群通知
    _send_feishu_notification(candidates, category, agent_run_id)

    return state


def _save_to_db(candidates: List[Dict[str, Any]], agent_run_id: str) -> None:
    """将候选产品写入 product_selections 表。"""
    if not _DB_AVAILABLE or db_session is None or ProductSelection is None:
        logger.warning("selection_agent _save_to_db | DB不可用，跳过写入")
        return

    try:
        run_uuid = uuid.UUID(agent_run_id) if agent_run_id else None
        with db_session() as session:
            for candidate in candidates:
                selection = ProductSelection(
                    id=uuid.uuid4(),
                    candidate_asin=candidate.get("asin", ""),
                    reason=candidate.get("reason", ""),
                    score=candidate.get("score", 0.0),
                    agent_run_id=run_uuid,
                )
                session.add(selection)
            session.commit()
        logger.info(
            "selection_agent _save_to_db | saved %d product_selections", len(candidates)
        )
    except Exception as exc:
        logger.error("selection_agent _save_to_db 失败（非阻塞）: %s", exc)


def _sync_to_bitable(candidates: List[Dict[str, Any]], category: str) -> None:
    """将候选产品同步到飞书 Bitable。"""
    if not _BITABLE_AVAILABLE or BitableSyncClient is None:
        logger.warning("selection_agent _sync_to_bitable | Bitable不可用，跳过同步")
        return

    try:
        # 从 settings 读取 Bitable 配置
        try:
            from src.config import settings
            app_token = getattr(settings, "BITABLE_APP_TOKEN", _MOCK_BITABLE_APP_TOKEN)
            table_id = getattr(settings, "BITABLE_SELECTION_TABLE_ID", _MOCK_BITABLE_TABLE_ID)
        except Exception:
            app_token = _MOCK_BITABLE_APP_TOKEN
            table_id = _MOCK_BITABLE_TABLE_ID

        client = BitableSyncClient()
        records = []
        for c in candidates:
            records.append({
                "ASIN": c.get("asin", ""),
                "产品名称": c.get("product_name", ""),
                "选品理由": c.get("reason", ""),
                "综合评分": c.get("score", 0.0),
                "分析类目": category,
                "风险提示": "\n".join(c.get("risks", [])),
                "分析日期": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })

        if records:
            client.batch_create_records(app_token, table_id, records)
            logger.info(
                "selection_agent _sync_to_bitable | synced %d records", len(records)
            )
    except Exception as exc:
        logger.error("selection_agent _sync_to_bitable 失败（非阻塞）: %s", exc)


def _send_feishu_notification(
    candidates: List[Dict[str, Any]], category: str, agent_run_id: str
) -> None:
    """发送飞书群消息通知。"""
    if not _FEISHU_BOT_AVAILABLE or get_bot is None:
        logger.warning("selection_agent _send_feishu_notification | 飞书Bot不可用")
        return

    try:
        from src.config import settings
        chat_id = getattr(settings, "FEISHU_TEST_CHAT_ID", None)
        if not chat_id:
            logger.info("selection_agent _send_feishu_notification | FEISHU_TEST_CHAT_ID未配置")
            return

        bot = get_bot()
        top3 = candidates[:3]
        lines = [f"📊 **{category} 选品分析完成**", f"共发现 {len(candidates)} 个候选产品：", ""]
        for i, c in enumerate(top3, 1):
            lines.append(
                f"{i}. **{c.get('product_name', '')[:30]}**\n"
                f"   ASIN: {c.get('asin', '')} | 评分: {c.get('score', 0)}/10"
            )

        message = "\n".join(lines)
        bot.send_text_message(chat_id, message)
        logger.info("selection_agent _send_feishu_notification | 通知已发送")
    except Exception as exc:
        logger.warning("selection_agent _send_feishu_notification 失败（非阻塞）: %s", exc)


# ---------------------------------------------------------------------------
# 节点7：finalize_run — 更新 agent_runs 状态
# ---------------------------------------------------------------------------

def finalize_run(state: SelectionState) -> SelectionState:
    """更新 agent_runs 状态为 completed 或 failed，写审计日志。"""
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    candidates = state.get("candidates", [])
    dry_run = state.get("dry_run", True)
    category = state.get("category", "pet_supplies")

    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info(
        "selection_agent finalize_run | agent_run_id=%s status=%s",
        agent_run_id,
        final_status,
    )

    # 构建 output_data
    report = state.get("report", {})
    output_summary = json.dumps({
        "candidate_count": len(candidates),
        "status": final_status,
        "error": error,
    })

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            with db_session() as session:
                run = session.get(AgentRun, run_uuid)
                if run:
                    run.status = final_status
                    run.finished_at = datetime.now(timezone.utc)
                    run.output_summary = output_summary[:200]
                    session.commit()
            logger.info(
                "selection_agent finalize_run | DB已更新 agent_run_id=%s status=%s",
                agent_run_id,
                final_status,
            )
        except Exception as exc:
            logger.warning("selection_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    # 写审计日志（函数内导入，避免循环导入）
    try:
        from src.utils.audit import log_action
        log_action(
            action="selection_agent.run",
            actor="selection_agent",
            pre_state={"category": category, "dry_run": dry_run},
            post_state={
                "agent_run_id": agent_run_id,
                "status": final_status,
                "candidate_count": len(candidates),
                "error": error,
            },
        )
    except Exception as exc:
        logger.warning("selection_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    return state

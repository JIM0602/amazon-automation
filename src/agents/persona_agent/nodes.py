"""用户画像Agent节点函数 — LangGraph多节点工作流实现。

节点顺序：
  1. init_run        — 创建 agent_runs 记录（status=running），验证输入
  2. collect_data    — 获取评论/Q&A数据（dry_run=True时使用Mock）
  3. retrieve_kb     — 调用知识库查询相关运营知识
  4. analyze_reviews — 调用 analyzer.py 分析评论数据
  5. generate_persona — 构建 UserPersona，保存到 state
  6. finalize_run    — 更新DB状态，写审计日志

所有节点接收并返回 PersonaState（dict子类），遵循LangGraph规范。
所有外部依赖在模块顶部导入，支持测试 patch。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 模块顶部导入所有需要被 patch 的依赖
# ---------------------------------------------------------------------------
_db_available = False
try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    _db_available = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]

_DB_AVAILABLE = _db_available

_ss_available = False
try:
    from src.seller_sprite.client import get_client as get_ss_client
    _ss_available = True
except ImportError:
    get_ss_client = None  # type: ignore[assignment]

_SS_AVAILABLE = _ss_available

_llm_available = False
try:
    from src.llm.client import chat
    _llm_available = True
except ImportError:
    chat = None  # type: ignore[assignment]

_LLM_AVAILABLE = _llm_available

_kb_available = False
try:
    from src.knowledge_base.rag_engine import query as kb_query
    _kb_available = True
except ImportError:
    kb_query = None  # type: ignore[assignment]

_KB_AVAILABLE = _kb_available

from src.agents.persona_agent.schemas import PersonaState
from src.agents.persona_agent.analyzer import (
    analyze_reviews_for_persona,
    build_user_persona,
)

# ---------------------------------------------------------------------------
# Mock 数据（dry_run=True 时使用）
# ---------------------------------------------------------------------------

_MOCK_REVIEWS = [
    {
        "text": "My cat loves this fountain! Very quiet and easy to clean. The filter keeps water fresh.",
        "rating": 5,
        "helpful_votes": 45,
        "verified": True,
    },
    {
        "text": "Great product for multiple cats. One issue - the pump sometimes makes noise at night.",
        "rating": 4,
        "helpful_votes": 30,
        "verified": True,
    },
    {
        "text": "Easy to assemble, but hard to find replacement filters. Would buy again.",
        "rating": 4,
        "helpful_votes": 22,
        "verified": False,
    },
    {
        "text": "The water stays clean much longer than a bowl. My senior dog drinks more water now.",
        "rating": 5,
        "helpful_votes": 38,
        "verified": True,
    },
    {
        "text": "Cute design but plastic feels cheap. Looking for stainless steel version.",
        "rating": 3,
        "helpful_votes": 15,
        "verified": True,
    },
]

_MOCK_KB_CONTEXT = [
    "宠物饮水机用户主要关注：安静性（夜间使用）、清洁便利、滤芯替换成本",
    "购买决策关键词：BPA-free、静音、过滤系统、大容量",
    "目标人群特征：25-45岁、养宠1-3年、重视宠物健康",
]

_MOCK_DEMOGRAPHICS = {
    "age_range": "25-45",
    "gender": "female-dominant",
    "income_level": "middle",
    "lifestyle": "pet-focused",
}


# ---------------------------------------------------------------------------
# 节点1：init_run — 验证输入，创建 agent_runs 记录
# ---------------------------------------------------------------------------

def init_run(state: PersonaState) -> PersonaState:
    """验证 category 或 asin 至少一个非空，创建 agent_runs 数据库记录（status=running）。"""
    category = state.get("category", "")
    asin = state.get("asin", "")
    dry_run = state.get("dry_run", True)

    logger.info(
        "persona_agent init_run | category=%s asin=%s dry_run=%s",
        category,
        asin,
        dry_run,
    )

    # 验证至少一个非空
    if not category and not asin:
        state["error"] = "必须提供 category 或 asin"
        state["status"] = "failed"
        return state

    run_id = str(uuid.uuid4())

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="persona_agent",
                    status="running",
                    input_summary=json.dumps({
                        "category": category,
                        "asin": asin,
                    }, ensure_ascii=False),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("persona_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("persona_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info("persona_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s", run_id)

    state["agent_run_id"] = run_id
    return state


# ---------------------------------------------------------------------------
# 节点2：collect_data — 获取评论数据
# ---------------------------------------------------------------------------

def collect_data(state: PersonaState) -> PersonaState:
    """获取评论/Q&A数据。dry_run=True 时返回 Mock 评论数据。"""
    if state.get("error"):
        return state

    category = state.get("category", "")
    asin = state.get("asin", "")
    dry_run = state.get("dry_run", True)

    logger.info(
        "persona_agent collect_data | category=%s asin=%s dry_run=%s",
        category,
        asin,
        dry_run,
    )

    if dry_run:
        state["raw_reviews"] = list(_MOCK_REVIEWS)
        logger.info(
            "persona_agent collect_data | dry_run=True, 使用Mock评论数据 count=%d",
            len(_MOCK_REVIEWS),
        )
        return state

    # 非 dry_run 模式：使用 Seller Sprite 市场数据 + LLM 合成伪评论
    if _SS_AVAILABLE and get_ss_client is not None:
        try:
            client = get_ss_client()
            market_data: Dict[str, Any] = {"keywords": [], "category": {}, "asin": {}}

            if category:
                try:
                    category_data = client.get_category_data(category)
                    market_data["category"] = category_data if isinstance(category_data, dict) else {}
                except Exception as exc:
                    logger.warning(
                        "persona_agent collect_data | 类目数据获取失败，继续使用关键词数据: %s",
                        exc,
                    )
                try:
                    keyword_result = client.search_keyword(category)
                    if isinstance(keyword_result, dict):
                        market_data["keywords"] = [keyword_result]
                except Exception as exc:
                    logger.warning(
                        "persona_agent collect_data | 关键词数据获取失败: %s",
                        exc,
                    )

            if asin:
                try:
                    asin_data = client.get_asin_data(asin)
                    market_data["asin"] = asin_data if isinstance(asin_data, dict) else {}
                except Exception as exc:
                    logger.warning(
                        "persona_agent collect_data | ASIN数据获取失败，继续合成评论: %s",
                        exc,
                    )

            if _LLM_AVAILABLE and chat is not None:
                try:
                    prompt = (
                        "你是电商用户画像分析助手。请根据以下市场信息，生成5条代表性伪评论，"
                        "每条评论都应反映用户痛点、购买动机和可能的人群特征。"
                        "请严格输出 JSON 数组，每个元素包含 text, rating, helpful_votes, verified。\n\n"
                        f"类目: {category}\n"
                        f"ASIN: {asin}\n"
                        f"类目数据: {json.dumps(market_data.get('category', {}), ensure_ascii=False)}\n"
                        f"关键词数据: {json.dumps(market_data.get('keywords', []), ensure_ascii=False)}\n"
                        f"ASIN数据: {json.dumps(market_data.get('asin', {}), ensure_ascii=False)}\n"
                        "重点推断：用户痛点、购买动机、人口统计特征。"
                    )
                    response = chat(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "你负责把市场信号转成结构化伪评论。"},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.3,
                        max_tokens=800,
                    )
                    content = response.get("content", "") if isinstance(response, dict) else ""
                    parsed: Any = json.loads(content)
                    if isinstance(parsed, list):
                        state["raw_reviews"] = [
                            {
                                "text": str(item.get("text", "")),
                                "rating": int(item.get("rating", 4)),
                                "helpful_votes": int(item.get("helpful_votes", 0)),
                                "verified": bool(item.get("verified", True)),
                            }
                            for item in parsed
                            if isinstance(item, dict)
                        ]
                    else:
                        raise ValueError("LLM response is not a JSON array")
                    logger.info(
                        "persona_agent collect_data | 使用Seller Sprite+LLM合成伪评论 count=%d",
                        len(state["raw_reviews"]),
                    )
                    if state.get("raw_reviews"):
                        return state
                except Exception as exc:
                    logger.warning(
                        "persona_agent collect_data | LLM合成伪评论失败，使用Mock数据兜底: %s",
                        exc,
                    )

            logger.warning("persona_agent collect_data | 使用Mock评论数据兜底")
            state["raw_reviews"] = list(_MOCK_REVIEWS)
            return state
        except Exception as exc:
            logger.warning(
                "persona_agent collect_data | 真实API不可用，使用Mock数据兜底: %s",
                exc,
            )

    logger.warning("persona_agent collect_data | 使用Mock评论数据兜底")
    state["raw_reviews"] = list(_MOCK_REVIEWS)
    return state


# ---------------------------------------------------------------------------
# 节点3：retrieve_kb — 查询知识库
# ---------------------------------------------------------------------------

def retrieve_kb(state: PersonaState) -> PersonaState:
    """调用知识库查询相关运营知识。dry_run=True 时使用 Mock 数据。"""
    if state.get("error"):
        return state

    category = state.get("category", "")
    dry_run = state.get("dry_run", True)

    logger.info(
        "persona_agent retrieve_kb | category=%s dry_run=%s",
        category,
        dry_run,
    )

    if dry_run:
        state["kb_context"] = list(_MOCK_KB_CONTEXT)
        logger.info("persona_agent retrieve_kb | dry_run=True, 使用Mock知识库数据")
        return state

    if _KB_AVAILABLE and kb_query is not None:
        try:
            query_text = f"{category} 用户画像 购买决策 用户痛点" if category else "用户画像分析"
            result = kb_query(query_text)
            state["kb_context"] = [result] if result else list(_MOCK_KB_CONTEXT)
            logger.info("persona_agent retrieve_kb | KB查询成功 results=%d", len(state["kb_context"]))
        except Exception as exc:
            logger.warning("persona_agent retrieve_kb KB查询失败（非阻塞）: %s", exc)
            state["kb_context"] = list(_MOCK_KB_CONTEXT)
    else:
        state["kb_context"] = list(_MOCK_KB_CONTEXT)

    return state


# ---------------------------------------------------------------------------
# 节点4：analyze_reviews — 分析评论数据
# ---------------------------------------------------------------------------

def analyze_reviews(state: PersonaState) -> PersonaState:
    """对评论数据调用 analyzer.py 进行分析，结果保存到 state["analysis_result"]。"""
    if state.get("error"):
        return state

    raw_reviews = state.get("raw_reviews", [])
    category = state.get("category", "")

    logger.info(
        "persona_agent analyze_reviews | category=%s review_count=%d",
        category,
        len(raw_reviews),
    )

    if not raw_reviews:
        logger.warning("persona_agent analyze_reviews | 没有评论数据，使用空分析结果")
        state["analysis_result"] = {
            "demographics": _MOCK_DEMOGRAPHICS.copy(),
            "pain_points": [],
            "motivations": [],
            "trigger_words": [],
            "persona_tags": [],
        }
        return state

    try:
        analysis = analyze_reviews_for_persona(raw_reviews, category)
        state["analysis_result"] = analysis
        logger.info(
            "persona_agent analyze_reviews | 完成分析 pain_points=%d motivations=%d",
            len(analysis.get("pain_points", [])),
            len(analysis.get("motivations", [])),
        )
    except Exception as exc:
        logger.error("persona_agent analyze_reviews 失败: %s", exc)
        state["error"] = f"评论分析失败: {exc}"
        state["status"] = "failed"

    return state


# ---------------------------------------------------------------------------
# 节点5：generate_persona — 构建 UserPersona
# ---------------------------------------------------------------------------

def generate_persona(state: PersonaState) -> PersonaState:
    """构建 UserPersona，保存到 state["user_persona"]。"""
    if state.get("error"):
        return state

    category = state.get("category", "")
    asin = state.get("asin", "")
    analysis_result = state.get("analysis_result", {})
    kb_context = state.get("kb_context", [])

    logger.info(
        "persona_agent generate_persona | category=%s asin=%s",
        category,
        asin,
    )

    # 构建数据来源列表
    data_sources = ["product_reviews"]
    if kb_context:
        data_sources.append("knowledge_base")
    if asin:
        data_sources.append(f"asin:{asin}")

    try:
        persona_dict = build_user_persona(
            category=category,
            asin=asin,
            analysis=analysis_result,
            data_sources=data_sources,
        )
        state["user_persona"] = persona_dict
        logger.info(
            "persona_agent generate_persona | 完成 pain_points=%d trigger_words=%d",
            len(persona_dict.get("pain_points", [])),
            len(persona_dict.get("trigger_words", [])),
        )
    except Exception as exc:
        logger.error("persona_agent generate_persona 失败: %s", exc)
        state["error"] = f"用户画像生成失败: {exc}"
        state["status"] = "failed"

    return state


# ---------------------------------------------------------------------------
# 节点6：finalize_run — 更新DB状态，写审计日志
# ---------------------------------------------------------------------------

def finalize_run(state: PersonaState) -> PersonaState:
    """更新 agent_runs 状态为 completed 或 failed，写审计日志。"""
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    dry_run = state.get("dry_run", True)
    category = state.get("category", "")

    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info(
        "persona_agent finalize_run | agent_run_id=%s status=%s",
        agent_run_id,
        final_status,
    )

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            user_persona = state.get("user_persona", {})
            output_summary = json.dumps({
                "category": category,
                "asin": state.get("asin", ""),
                "persona_tags": user_persona.get("persona_tags", []),
                "status": final_status,
                "error": error,
            }, ensure_ascii=False)

            with db_session() as session:
                run = session.get(AgentRun, run_uuid)
                if run:
                    setattr(run, "status", final_status)
                    setattr(run, "finished_at", datetime.now(timezone.utc))
                    setattr(run, "output_summary", output_summary[:200])
                    session.commit()

            logger.info(
                "persona_agent finalize_run | DB已更新 agent_run_id=%s status=%s",
                agent_run_id,
                final_status,
            )
        except Exception as exc:
            logger.warning("persona_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    # 写审计日志
    try:
        from src.utils.audit import log_action  # noqa: PLC0415
        log_action(
            action="persona_agent.run",
            actor="persona_agent",
            pre_state={
                "category": category,
                "asin": state.get("asin", ""),
                "dry_run": dry_run,
            },
            post_state={
                "agent_run_id": agent_run_id,
                "status": final_status,
                "error": error,
            },
        )
    except Exception as exc:
        logger.warning("persona_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    return state

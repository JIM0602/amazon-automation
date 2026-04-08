"""白皮书 Agent 节点函数 — LangGraph 多节点工作流实现。"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    from src.seller_sprite.client import get_client as get_ss_client
    ss_available = True
except ImportError:
    get_ss_client = None  # type: ignore[assignment]
    ss_available = False

try:
    from src.llm.client import chat
    llm_available = True
except ImportError:
    chat = None  # type: ignore[assignment]
    llm_available = False

try:
    from src.knowledge_base.rag_engine import query as kb_query
    kb_available = True
except ImportError:
    kb_query = None  # type: ignore[assignment]
    kb_available = False

try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    db_available = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    db_available = False

from .schemas import WhitepaperState

_MOCK_MARKET_DATA = {
    "search_volume_trend": "稳定上升",
    "price_band": {"min": 22.99, "max": 49.99},
    "top_keywords": ["insulated pet bottle", "travel dog water bottle", "leak proof dog water bottle"],
    "market_notes": [
        "便携饮水产品的购买决策高度依赖容量、防漏和清洁便利性。",
        "用户对户外、旅行、车载等场景需求强烈。",
    ],
}

_MOCK_COMPETITOR_SUMMARY = {
    "top_brands": ["PawFlow", "HydroPup", "TrailTails"],
    "strengths": ["评分高", "容量适中", "场景清晰"],
    "weaknesses": ["同质化较高", "页面信息不完整"],
    "opportunities": ["强调材质安全", "增加组合装", "优化包装与内容页"],
}

_MOCK_KB_RESEARCH = [
    "白皮书需要先定义市场机会，再定义产品定位。",
    "内部文档应包含竞品对比、风险评估和上市建议。",
    "建议在 go-to-market 中明确主推关键词和主视觉信息。",
]


def init_run(state: WhitepaperState) -> WhitepaperState:
    """验证输入，创建 agent_runs 数据库记录。"""
    product_name = state.get("product_name", "")
    asin = state.get("asin", "")
    dry_run = state.get("dry_run", True)

    logger.info("whitepaper_agent init_run | product_name=%s asin=%s dry_run=%s", product_name, asin, dry_run)

    if (not product_name or not str(product_name).strip()) and (not asin or not str(asin).strip()):
        state["error"] = "必须提供 product_name 或 asin，无法生成白皮书"
        state["status"] = "failed"
        return state

    run_id = str(uuid.uuid4())

    if not dry_run and db_available and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="whitepaper_agent",
                    status="running",
                    input_summary=json.dumps(
                        {
                            "product_name": product_name,
                            "asin": asin,
                            "category": state.get("category", ""),
                            "target_audience": state.get("target_audience", ""),
                        },
                        ensure_ascii=False,
                    ),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("whitepaper_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("whitepaper_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info("whitepaper_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s", run_id)

    state["agent_run_id"] = run_id
    return state


def research_market(state: WhitepaperState) -> WhitepaperState:
    """研究市场数据；dry_run 使用 Mock，真实模式使用 Seller Sprite。"""
    if state.get("error"):
        return state

    product_name = state.get("product_name", "")
    asin = state.get("asin", "")
    category = state.get("category", "")
    dry_run = state.get("dry_run", True)

    logger.info("whitepaper_agent research_market | product_name=%s asin=%s dry_run=%s", product_name, asin, dry_run)

    if dry_run:
        state["market_data"] = dict(_MOCK_MARKET_DATA)
        state["competitor_summary"] = dict(_MOCK_COMPETITOR_SUMMARY)
        return state

    if ss_available and get_ss_client is not None:
        try:
            client = get_ss_client()
            market_data: Dict[str, Any] = {"category": category, "product_name": product_name, "asin": asin}

            try:
                if asin:
                    market_data["asin_data"] = client.get_asin_data(asin)
                elif category:
                    market_data["category_data"] = client.get_category_data(category)
                else:
                    market_data["keyword_data"] = client.search_keyword(product_name or category or "product")
            except Exception as exc:
                logger.warning("whitepaper_agent research_market | Seller Sprite 查询失败: %s", exc)

            try:
                keyword_result = client.search_keyword(product_name or category or "product")
                market_data["keyword_result"] = keyword_result
            except Exception as exc:
                logger.warning("whitepaper_agent research_market | keyword 搜索失败: %s", exc)

            state["market_data"] = market_data
            state["competitor_summary"] = {
                "source": "seller_sprite",
                "notes": ["已采集市场与竞品基础信息，建议结合具体 ASIN 深化分析。"],
            }
            return state
        except Exception as exc:
            logger.warning("whitepaper_agent research_market | Seller Sprite 不可用，使用 Mock 兜底: %s", exc)

    state["market_data"] = dict(_MOCK_MARKET_DATA)
    state["competitor_summary"] = dict(_MOCK_COMPETITOR_SUMMARY)
    return state


def retrieve_kb(state: WhitepaperState) -> WhitepaperState:
    """检索知识库；dry_run 使用 Mock，真实模式查询 KB。"""
    if state.get("error"):
        return state

    product_name = state.get("product_name", "")
    category = state.get("category", "")
    dry_run = state.get("dry_run", True)

    logger.info("whitepaper_agent retrieve_kb | product_name=%s dry_run=%s", product_name, dry_run)

    if dry_run:
        state["kb_research"] = list(_MOCK_KB_RESEARCH)
        return state

    if kb_available and kb_query is not None:
        try:
            question = (
                f"为产品白皮书检索相关知识：产品 {product_name}，类目 {category}，"
                "请提供市场定位、竞品对比、产品 brief 与 go-to-market 建议。"
            )
            kb_answer = kb_query(question)
            insights: List[str] = []
            if isinstance(kb_answer, str) and kb_answer.strip():
                insights = [line.strip("-• ") for line in kb_answer.splitlines() if line.strip()]
            if not insights:
                insights = [str(kb_answer)] if kb_answer else []
            state["kb_research"] = insights
            return state
        except Exception as exc:
            logger.warning("whitepaper_agent retrieve_kb | KB 查询失败，使用 Mock 兜底: %s", exc)

    state["kb_research"] = list(_MOCK_KB_RESEARCH)
    return state


def generate_whitepaper(state: WhitepaperState) -> WhitepaperState:
    """生成白皮书章节；dry_run 使用 Mock，真实模式使用 LLM。"""
    if state.get("error"):
        return state

    product_name = state.get("product_name", "")
    asin = state.get("asin", "")
    category = state.get("category", "")
    target_audience = state.get("target_audience", "")
    market_data = state.get("market_data", {})
    competitor_summary = state.get("competitor_summary", {})
    kb_research = state.get("kb_research", [])
    dry_run = state.get("dry_run", True)

    logger.info("whitepaper_agent generate_whitepaper | product_name=%s dry_run=%s", product_name, dry_run)

    if dry_run:
        sections = {
            "executive_summary": f"{product_name or asin} 面向 {target_audience or '核心买家'} 的产品白皮书摘要。",
            "market_analysis": {
                "market_data": market_data,
                "insights": ["市场需求稳定增长", "用户重视便携与防漏"],
            },
            "product_positioning": "便携、耐用、场景明确的中高性价比解决方案。",
            "competitive_landscape": competitor_summary,
            "go_to_market": ["站内关键词布局", "A+ 页面", "主图/视频内容优化"],
            "risk_assessment": ["同质化竞争", "价格带压缩", "评论积累周期较长"],
        }
    else:
        if llm_available and chat is not None:
            try:
                response = chat(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是产品白皮书专家，请输出内部可直接使用的结构化白皮书。"},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "product_name": product_name,
                                    "asin": asin,
                                    "category": category,
                                    "target_audience": target_audience,
                                    "market_data": market_data,
                                    "competitor_summary": competitor_summary,
                                    "kb_research": kb_research,
                                    "required_sections": [
                                        "executive_summary",
                                        "market_analysis",
                                        "product_positioning",
                                        "competitive_landscape",
                                        "go_to_market",
                                        "risk_assessment",
                                    ],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
                content = response.get("content", "") if isinstance(response, dict) else str(response)
                sections = {
                    "executive_summary": content,
                    "market_analysis": market_data,
                    "product_positioning": "",
                    "competitive_landscape": competitor_summary,
                    "go_to_market": [],
                    "risk_assessment": [],
                    "raw_llm_output": content,
                }
            except Exception as exc:
                logger.warning("whitepaper_agent generate_whitepaper | LLM 失败，使用 Mock 兜底: %s", exc)
                sections = {
                    "executive_summary": f"{product_name or asin} 的产品白皮书摘要。",
                    "market_analysis": market_data,
                    "product_positioning": f"{product_name or '产品'} 应围绕 {category} 细分需求建立差异化。",
                    "competitive_landscape": competitor_summary,
                    "go_to_market": ["关键词广告", "详情页优化", "组合装策略"],
                    "risk_assessment": ["库存风险", "流量波动", "竞品价格战"],
                }
        else:
            sections = {
                "executive_summary": f"{product_name or asin} 的产品白皮书摘要。",
                "market_analysis": market_data,
                "product_positioning": f"{product_name or '产品'} 应围绕 {category} 细分需求建立差异化。",
                "competitive_landscape": competitor_summary,
                "go_to_market": ["关键词广告", "详情页优化", "组合装策略"],
                "risk_assessment": ["库存风险", "流量波动", "竞品价格战"],
            }

    state["whitepaper_sections"] = sections
    state["report"] = {
        "product_name": product_name,
        "asin": asin,
        "category": category,
        "target_audience": target_audience,
        "kb_research": kb_research,
        "market_data": market_data,
        "competitor_summary": competitor_summary,
        "whitepaper_sections": sections,
    }
    return state


def finalize_run(state: WhitepaperState) -> WhitepaperState:
    """更新 DB 状态并写审计日志。"""
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    dry_run = state.get("dry_run", True)

    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info("whitepaper_agent finalize_run | agent_run_id=%s status=%s", agent_run_id, final_status)

    if not dry_run and db_available and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            output_summary = json.dumps(
                {
                    "product_name": state.get("product_name", ""),
                    "asin": state.get("asin", ""),
                    "status": final_status,
                    "error": error,
                },
                ensure_ascii=False,
            )
            with db_session() as session:
                run = session.get(AgentRun, run_uuid)
                if run:
                    run.__dict__["status"] = final_status
                    run.__dict__["finished_at"] = datetime.now(timezone.utc)
                    run.__dict__["output_summary"] = output_summary[:200]
                    session.commit()
        except Exception as exc:
            logger.warning("whitepaper_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    try:
        from src.utils.audit import log_action  # noqa: PLC0415

        log_action(
            action="whitepaper_agent.run",
            actor="whitepaper_agent",
            pre_state={
                "product_name": state.get("product_name", ""),
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
        logger.warning("whitepaper_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    return state

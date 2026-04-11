"""品牌规划 Agent 节点函数 — LangGraph 多节点工作流实现。"""
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

from .schemas import BrandPlanningState

_MOCK_MARKET_DATA = {
    "category": "pet_supplies",
    "market_size_estimate": "中高竞争、稳定增长",
    "avg_price_range": {"min": 18.99, "max": 39.99},
    "top_keywords": ["pet water bottle", "portable dog water bottle", "leak proof pet bottle"],
    "top_competitors": [
        {"asin": "B0PETWATER1", "brand": "PawFlow", "price": 24.99, "rating": 4.6},
        {"asin": "B0PETWATER2", "brand": "HydroPup", "price": 28.99, "rating": 4.4},
        {"asin": "B0PETWATER3", "brand": "TrailTails", "price": 19.99, "rating": 4.2},
    ],
    "customer_insights": [
        "便携、漏水控制、单手操作是核心购买因素",
        "评论中高频提到材质安全与清洁便利性",
    ],
}

_MOCK_KB_INSIGHTS = [
    "品牌定位应聚焦单一核心场景，避免过早扩张品类。",
    "Amazon 品牌故事要把功能价值与生活方式价值结合。",
    "新品线建议采用 1 个引流款 + 2 个利润款的梯度结构。",
]


def init_run(state: BrandPlanningState) -> BrandPlanningState:
    """验证输入，创建 agent_runs 数据库记录。"""
    brand_name = state.get("brand_name", "")
    dry_run = state.get("dry_run", True)

    logger.info("brand_planning_agent init_run | brand_name=%s dry_run=%s", brand_name, dry_run)

    if not brand_name or not str(brand_name).strip():
        state["error"] = "必须提供 brand_name，无法进行品牌规划"
        state["status"] = "failed"
        return state

    run_id = str(uuid.uuid4())

    if not dry_run and db_available and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="brand_planning_agent",
                    status="running",
                    input_summary=json.dumps(
                        {
                            "brand_name": brand_name,
                            "category": state.get("category", ""),
                            "target_market": state.get("target_market", "US"),
                            "budget_range": state.get("budget_range", ""),
                        },
                        ensure_ascii=False,
                    ),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("brand_planning_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("brand_planning_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info("brand_planning_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s", run_id)

    state["agent_run_id"] = run_id
    return state


def collect_market_data(state: BrandPlanningState) -> BrandPlanningState:
    """采集市场数据；dry_run 使用 Mock，真实模式使用 Seller Sprite。"""
    if state.get("error"):
        return state

    brand_name = state.get("brand_name", "")
    category = state.get("category", "pet_supplies")
    target_market = state.get("target_market", "US")
    dry_run = state.get("dry_run", True)

    logger.info(
        "brand_planning_agent collect_market_data | brand_name=%s category=%s dry_run=%s",
        brand_name,
        category,
        dry_run,
    )

    if dry_run:
        state["market_analysis"] = {
            "category": category or "pet_supplies",
            "target_market": target_market,
            "market_size_estimate": _MOCK_MARKET_DATA["market_size_estimate"],
            "avg_price_range": _MOCK_MARKET_DATA["avg_price_range"],
            "top_keywords": _MOCK_MARKET_DATA["top_keywords"],
            "top_competitors": _MOCK_MARKET_DATA["top_competitors"],
            "customer_insights": _MOCK_MARKET_DATA["customer_insights"],
        }
        return state

    if ss_available and get_ss_client is not None:
        try:
            client = get_ss_client()
            query_term = category or brand_name or "pet supplies"
            market_data: Dict[str, Any] = {
                "category": category,
                "target_market": target_market,
            }

            try:
                keyword_result = client.search_keyword(query_term)
                market_data["keyword_result"] = keyword_result
                if isinstance(keyword_result, dict):
                    market_data["top_keywords"] = keyword_result.get("keywords") or keyword_result.get("top_keywords") or []
                    market_data["top_competitors"] = keyword_result.get("top_asins") or []
            except Exception as exc:
                logger.warning("brand_planning_agent collect_market_data | search_keyword 失败: %s", exc)

            try:
                market_data["category_data"] = client.get_category_data(query_term)
            except Exception as exc:
                logger.warning("brand_planning_agent collect_market_data | get_category_data 失败: %s", exc)

            state["market_analysis"] = market_data
            return state
        except Exception as exc:
            logger.warning("brand_planning_agent collect_market_data | Seller Sprite 不可用，使用 Mock 兜底: %s", exc)

    state["market_analysis"] = dict(_MOCK_MARKET_DATA)
    state["market_analysis"]["category"] = category
    state["market_analysis"]["target_market"] = target_market
    return state


def retrieve_kb(state: BrandPlanningState) -> BrandPlanningState:
    """检索知识库；dry_run 使用 Mock，真实模式查询 KB。"""
    if state.get("error"):
        return state

    brand_name = state.get("brand_name", "")
    category = state.get("category", "")
    dry_run = state.get("dry_run", True)

    logger.info("brand_planning_agent retrieve_kb | brand_name=%s dry_run=%s", brand_name, dry_run)

    if dry_run:
        state["kb_insights"] = list(_MOCK_KB_INSIGHTS)
        return state

    if kb_available and kb_query is not None:
        try:
            question = (
                f"为 Amazon 品牌规划提供建议：品牌 {brand_name}，类目 {category}，"
                "重点关注品牌定位、产品线规划、品牌故事和营销策略。"
            )
            kb_answer = kb_query(question)
            insights: List[str] = []
            if isinstance(kb_answer, str) and kb_answer.strip():
                insights = [line.strip("-• ") for line in kb_answer.splitlines() if line.strip()]
            if not insights:
                insights = [str(kb_answer)] if kb_answer else []
            state["kb_insights"] = insights
            return state
        except Exception as exc:
            logger.warning("brand_planning_agent retrieve_kb | KB 查询失败，使用 Mock 兜底: %s", exc)

    state["kb_insights"] = list(_MOCK_KB_INSIGHTS)
    return state


def generate_strategy(state: BrandPlanningState) -> BrandPlanningState:
    """基于市场数据、知识库与 LLM 生成品牌策略。"""
    if state.get("error"):
        return state

    brand_name = state.get("brand_name", "")
    category = state.get("category", "")
    target_market = state.get("target_market", "US")
    budget_range = state.get("budget_range", "")
    market_analysis = state.get("market_analysis", {})
    kb_insights = state.get("kb_insights", [])
    dry_run = state.get("dry_run", True)

    logger.info("brand_planning_agent generate_strategy | brand_name=%s dry_run=%s", brand_name, dry_run)

    if dry_run:
        brand_strategy = {
            "positioning": f"面向 {target_market} 宠物用户的便携清洁型品牌，突出安全材质与单手操作。",
            "product_line_plan": [
                "引流款：便携宠物水瓶",
                "利润款：加大容量户外款",
                "延展款：折叠碗/便携食盆组合",
            ],
            "brand_story": f"{brand_name} 诞生于户外遛宠场景，目标是让宠物补水更简单更安心。",
            "marketing_strategy": [
                "围绕户外遛狗、旅行、车载补水场景投放关键词广告",
                "利用 A+ 页面展示材质安全与防漏结构",
                "搭配捆绑销售提升客单价",
            ],
            "budget_allocation": budget_range or "首批预算建议控制在 $8k-$15k",
        }
    else:
        if llm_available and chat is not None:
            try:
                prompt = [
                    {"role": "system", "content": "你是亚马逊品牌策略顾问，输出简洁、可执行的品牌规划。"},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "brand_name": brand_name,
                                "category": category,
                                "target_market": target_market,
                                "budget_range": budget_range,
                                "market_analysis": market_analysis,
                                "kb_insights": kb_insights,
                                "required_output": [
                                    "positioning",
                                    "product_line_plan",
                                    "brand_story",
                                    "marketing_strategy",
                                    "budget_allocation",
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    },
                ]
                response = chat(model="gpt-4o-mini", messages=prompt, temperature=0.3, max_tokens=2000)
                content = response.get("content", "") if isinstance(response, dict) else str(response)
                brand_strategy = {
                    "positioning": content,
                    "product_line_plan": [],
                    "brand_story": "",
                    "marketing_strategy": [],
                    "budget_allocation": budget_range,
                    "raw_llm_output": content,
                }
            except Exception as exc:
                logger.warning("brand_planning_agent generate_strategy | LLM 失败，使用 Mock 兜底: %s", exc)
                brand_strategy = {
                    "positioning": f"{brand_name} 应聚焦 {category} 细分场景，突出差异化与可复购配件。",
                    "product_line_plan": ["单品切入", "组合装扩展", "配件补充"],
                    "brand_story": f"{brand_name} 致力于解决 {target_market} 用户在日常使用中的真实痛点。",
                    "marketing_strategy": ["关键词广告", "站内内容优化", "社媒种草"],
                    "budget_allocation": budget_range,
                }
        else:
            brand_strategy = {
                "positioning": f"{brand_name} 应聚焦 {category} 细分场景，突出差异化与可复购配件。",
                "product_line_plan": ["单品切入", "组合装扩展", "配件补充"],
                "brand_story": f"{brand_name} 致力于解决 {target_market} 用户在日常使用中的真实痛点。",
                "marketing_strategy": ["关键词广告", "站内内容优化", "社媒种草"],
                "budget_allocation": budget_range,
            }

    state["brand_strategy"] = brand_strategy
    state["report"] = {
        "brand_name": brand_name,
        "category": category,
        "target_market": target_market,
        "market_analysis": market_analysis,
        "kb_insights": kb_insights,
        "brand_strategy": brand_strategy,
    }
    return state


def finalize_run(state: BrandPlanningState) -> BrandPlanningState:
    """更新 DB 状态并写审计日志。"""
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    dry_run = state.get("dry_run", True)

    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info("brand_planning_agent finalize_run | agent_run_id=%s status=%s", agent_run_id, final_status)

    if not dry_run and db_available and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            output_summary = json.dumps(
                {
                    "brand_name": state.get("brand_name", ""),
                    "category": state.get("category", ""),
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
            logger.warning("brand_planning_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    try:
        from src.utils.audit import log_action  # noqa: PLC0415

        log_action(
            action="brand_planning_agent.run",
            actor="brand_planning_agent",
            pre_state={
                "brand_name": state.get("brand_name", ""),
                "category": state.get("category", ""),
                "dry_run": dry_run,
            },
            post_state={
                "agent_run_id": agent_run_id,
                "status": final_status,
                "error": error,
            },
        )
    except Exception as exc:
        logger.warning("brand_planning_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    return state

"""Listing文案Agent节点函数 — LangGraph多节点工作流实现。

节点顺序：
  1. init_run       — 创建 agent_runs 记录（status=running）
  2. retrieve_kb    — 检索知识库（文案技巧、运营文档）
  3. generate_copy  — 调用LLM生成原始文案
  4. check_compliance — 合规词检查
  5. finalize_run   — 更新 agent_runs 状态，准备输出

所有节点接收并返回 ListingState（dict子类），遵循LangGraph规范。
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
try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    _DB_AVAILABLE = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    _DB_AVAILABLE = False

try:
    from src.knowledge_base.rag_engine import query as kb_query
    _KB_AVAILABLE = True
except ImportError:
    kb_query = None  # type: ignore[assignment]
    _KB_AVAILABLE = False

from src.agents.listing_agent.schemas import ListingState, ListingCopySchema
from src.agents.listing_agent.generator import generate_full_listing
from src.agents.listing_agent.compliance import run_compliance_check

# ---------------------------------------------------------------------------
# Mock 数据（dry_run=True 时使用）
# ---------------------------------------------------------------------------

_MOCK_KB_TIPS = [
    "文案技巧1：标题前段放品牌名，中段放核心关键词，后段放使用场景，覆盖长尾词",
    "文案技巧2：Bullet Point以ALL CAPS关键词开头，后跟破折号和详细说明",
    "文案技巧3：Search Terms只放标题未覆盖的词，优先放长尾词和同义词",
    "文案技巧4：用买家语言描述痛点，强调'解决方案'而非'产品特性'",
    "文案技巧5：数字化描述产品规格（如'2.5L大容量'），增加信服力",
]


# ---------------------------------------------------------------------------
# 节点1：init_run — 创建 agent_runs 记录
# ---------------------------------------------------------------------------

def init_run(state: ListingState) -> ListingState:
    """创建 agent_runs 数据库记录，status=running。"""
    asin = state.get("asin", "")
    product_name = state.get("product_name", "")
    dry_run = state.get("dry_run", True)

    logger.info(
        "listing_agent init_run | asin=%s product_name=%s dry_run=%s",
        asin,
        product_name[:30] if product_name else "",
        dry_run,
    )

    # 验证最低输入要求
    if not asin and not product_name:
        state["error"] = "必须提供 asin 或 product_name，无法生成文案"
        state["status"] = "failed"
        return state

    run_id = str(uuid.uuid4())

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="listing_agent",
                    status="running",
                    input_summary=json.dumps({
                        "asin": asin,
                        "product_name": product_name,
                        "category": state.get("category", ""),
                    }, ensure_ascii=False),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("listing_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("listing_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info("listing_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s", run_id)

    state["agent_run_id"] = run_id
    return state


# ---------------------------------------------------------------------------
# 节点2：retrieve_kb — 检索知识库文案技巧
# ---------------------------------------------------------------------------

def retrieve_kb(state: ListingState) -> ListingState:
    """从知识库检索Listing文案技巧和运营文档。dry_run=True 时使用 Mock 结果。"""
    if state.get("error"):
        return state

    category = state.get("category", "")
    product_name = state.get("product_name", "")
    dry_run = state.get("dry_run", True)

    logger.info("listing_agent retrieve_kb | category=%s dry_run=%s", category, dry_run)

    if dry_run:
        state["kb_tips"] = _MOCK_KB_TIPS
        logger.info("listing_agent retrieve_kb | dry_run=True, 使用Mock KB结果")
        return state

    if not _KB_AVAILABLE or kb_query is None:
        logger.warning("listing_agent retrieve_kb | 知识库不可用，使用Mock数据")
        state["kb_tips"] = _MOCK_KB_TIPS
        return state

    try:
        # 构造查询问题
        query_text = f"亚马逊{category}类目Listing文案撰写技巧，如何写高转化的标题和Bullet Points？"
        answer = kb_query(query_text)
        # 将回答拆分为技巧列表
        tips = [line.strip() for line in answer.split("\n") if line.strip() and len(line.strip()) > 10]
        if not tips:
            tips = _MOCK_KB_TIPS
        state["kb_tips"] = tips[:10]  # 最多取10条
        logger.info("listing_agent retrieve_kb | kb_tips_count=%d", len(tips))
    except Exception as exc:
        logger.warning("listing_agent retrieve_kb 失败，使用Mock数据: %s", exc)
        state["kb_tips"] = _MOCK_KB_TIPS

    return state


# ---------------------------------------------------------------------------
# 节点3：generate_copy — 调用LLM生成文案
# ---------------------------------------------------------------------------

def generate_copy(state: ListingState) -> ListingState:
    """调用LLM生成Listing文案（标题+五点+关键词+A+）。dry_run=True 时使用 Mock。"""
    if state.get("error"):
        return state

    asin = state.get("asin", "")
    product_name = state.get("product_name", "")
    category = state.get("category", "")
    features = state.get("features", [])
    persona_data = state.get("persona_data", {})
    competitor_data = state.get("competitor_data", {})
    kb_tips = state.get("kb_tips", [])
    dry_run = state.get("dry_run", True)

    logger.info(
        "listing_agent generate_copy | asin=%s dry_run=%s",
        asin,
        dry_run,
    )

    try:
        generated = generate_full_listing(
            asin=asin,
            product_name=product_name,
            category=category,
            features=features,
            persona_data=persona_data,
            competitor_data=competitor_data,
            kb_tips=kb_tips,
            dry_run=dry_run,
        )
        state["generated_copy"] = generated
        logger.info(
            "listing_agent generate_copy | title_len=%d bp_count=%d",
            len(generated.get("title", "")),
            len(generated.get("bullet_points", [])),
        )
    except Exception as exc:
        logger.error("listing_agent generate_copy 失败: %s", exc)
        state["error"] = f"文案生成失败: {exc}"
        state["status"] = "failed"

    return state


# ---------------------------------------------------------------------------
# 节点4：check_compliance — 合规词检查
# ---------------------------------------------------------------------------

def check_compliance(state: ListingState) -> ListingState:
    """对生成的文案执行合规词检查。"""
    if state.get("error"):
        return state

    generated = state.get("generated_copy", {})
    title = generated.get("title", "")
    bullet_points = generated.get("bullet_points", [])
    search_terms = generated.get("search_terms", "")
    aplus_copy = generated.get("aplus_copy", "") or ""

    logger.info("listing_agent check_compliance | checking generated copy")

    try:
        compliance_result = run_compliance_check(
            title=title,
            bullet_points=bullet_points,
            search_terms=search_terms,
            aplus_copy=aplus_copy,
        )

        state["compliance_result"] = compliance_result

        # 构建最终Listing文案（即使合规不通过也输出，附上问题列表）
        listing_copy = {
            "asin": state.get("asin", ""),
            "title": title,
            "bullet_points": bullet_points,
            "search_terms": search_terms,
            "aplus_copy": generated.get("aplus_copy"),
            "compliance_passed": compliance_result["passed"],
            "compliance_issues": compliance_result["issues"],
            "kb_tips_used": state.get("kb_tips", [])[:3],
        }

        state["listing_copy"] = listing_copy

        if compliance_result["passed"]:
            logger.info("listing_agent check_compliance | 合规检查通过")
        else:
            logger.warning(
                "listing_agent check_compliance | 合规检查发现问题: %s",
                compliance_result["issues"],
            )

    except Exception as exc:
        logger.error("listing_agent check_compliance 失败: %s", exc)
        # 不设置 error，允许继续（合规检查失败不应阻断输出）
        state["compliance_result"] = {"passed": False, "issues": [f"合规检查异常: {exc}"]}
        state["listing_copy"] = {
            "asin": state.get("asin", ""),
            "title": generated.get("title", ""),
            "bullet_points": generated.get("bullet_points", []),
            "search_terms": generated.get("search_terms", ""),
            "aplus_copy": generated.get("aplus_copy"),
            "compliance_passed": False,
            "compliance_issues": [f"合规检查异常: {exc}"],
            "kb_tips_used": [],
        }

    return state


# ---------------------------------------------------------------------------
# 节点5：finalize_run — 更新 agent_runs 状态，准备输出
# ---------------------------------------------------------------------------

def finalize_run(state: ListingState) -> ListingState:
    """更新 agent_runs 状态为 completed 或 failed，写审计日志。"""
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    dry_run = state.get("dry_run", True)
    asin = state.get("asin", "")

    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info(
        "listing_agent finalize_run | agent_run_id=%s status=%s",
        agent_run_id,
        final_status,
    )

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            listing_copy = state.get("listing_copy", {})
            output_summary = json.dumps({
                "asin": asin,
                "compliance_passed": listing_copy.get("compliance_passed", False),
                "status": final_status,
                "error": error,
            }, ensure_ascii=False)

            with db_session() as session:
                run = session.get(AgentRun, run_uuid)
                if run:
                    run.status = final_status
                    run.finished_at = datetime.now(timezone.utc)
                    run.output_summary = output_summary[:200]
                    session.commit()

            logger.info(
                "listing_agent finalize_run | DB已更新 agent_run_id=%s status=%s",
                agent_run_id,
                final_status,
            )
        except Exception as exc:
            logger.warning("listing_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    # 写审计日志
    try:
        from src.utils.audit import log_action  # noqa: PLC0415
        log_action(
            action="listing_agent.run",
            actor="listing_agent",
            pre_state={
                "asin": asin,
                "dry_run": dry_run,
            },
            post_state={
                "agent_run_id": agent_run_id,
                "status": final_status,
                "compliance_passed": state.get("listing_copy", {}).get("compliance_passed", False),
                "error": error,
            },
        )
    except Exception as exc:
        logger.warning("listing_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    return state

"""竞品调研Agent节点函数 — LangGraph多节点工作流实现。

节点顺序：
  1. init_run           — 创建 agent_runs 记录（status=running），验证输入
  2. fetch_asin_data    — 获取竞品ASIN数据（dry_run=True时使用Mock）
  3. analyze_competitors — 调用 analyzer.py 逐一分析竞品
  4. generate_profile   — 构建 CompetitorAnalysis，保存到 state
  5. finalize_run       — 更新DB状态，写审计日志

所有节点接收并返回 CompetitorState（dict子类），遵循LangGraph规范。
所有外部依赖在模块顶部导入，支持测试 patch。

注意：竞品数据不爬取亚马逊页面，仅使用Mock数据或官方API。
数据保留策略：竞品敏感数据不超过30天，清理逻辑由数据库定期任务处理。
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

from src.agents.competitor_agent.schemas import CompetitorState, CompetitorProfile, CompetitorAnalysis
from src.agents.competitor_agent.analyzer import (
    analyze_competitor_data,
    extract_strengths_weaknesses,
    calculate_competitive_position,
    build_competitor_analysis,
)

# ---------------------------------------------------------------------------
# Mock 数据（dry_run=True 时使用）
# ---------------------------------------------------------------------------

_MOCK_COMPETITOR_DATA = {
    "B0COMPETITOR1": {
        "asin": "B0COMPETITOR1",
        "title": "Competitor Pet Water Fountain 2L",
        "brand": "CompetitorBrand",
        "price": 29.99,
        "bsr_rank": 150,
        "rating": 4.3,
        "review_count": 1250,
        "bullet_points": ["Feature 1 - Easy Clean", "Feature 2 - Quiet Pump", "Feature 3 - 2L Capacity"],
    },
    "B0COMPETITOR2": {
        "asin": "B0COMPETITOR2",
        "title": "Budget Pet Fountain 1.5L",
        "brand": "BudgetBrand",
        "price": 19.99,
        "bsr_rank": 500,
        "rating": 3.8,
        "review_count": 340,
        "bullet_points": ["Feature 1 - Affordable", "Feature 2 - 1.5L"],
    },
}


# ---------------------------------------------------------------------------
# 节点1：init_run — 验证输入，创建 agent_runs 记录
# ---------------------------------------------------------------------------

def init_run(state: CompetitorState) -> CompetitorState:
    """验证 target_asin 非空，创建 agent_runs 数据库记录（status=running）。"""
    target_asin = state.get("target_asin", "")
    dry_run = state.get("dry_run", True)

    logger.info(
        "competitor_agent init_run | target_asin=%s dry_run=%s",
        target_asin,
        dry_run,
    )

    # 验证 target_asin 非空
    if not target_asin or not target_asin.strip():
        state["error"] = "必须提供 target_asin，无法进行竞品分析"
        state["status"] = "failed"
        return state

    run_id = str(uuid.uuid4())

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="competitor_agent",
                    status="running",
                    input_summary=json.dumps({
                        "target_asin": target_asin,
                        "competitor_asins": state.get("competitor_asins", []),
                    }, ensure_ascii=False),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("competitor_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("competitor_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info("competitor_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s", run_id)

    state["agent_run_id"] = run_id
    return state


# ---------------------------------------------------------------------------
# 节点2：fetch_asin_data — 获取竞品数据
# ---------------------------------------------------------------------------

def fetch_asin_data(state: CompetitorState) -> CompetitorState:
    """获取竞品ASIN数据。dry_run=True 时返回 Mock 竞品数据。

    注意：此节点不爬取亚马逊页面，仅使用 Mock 数据或官方 API。
    """
    if state.get("error"):
        return state

    target_asin = state.get("target_asin", "")
    competitor_asins = state.get("competitor_asins", [])
    dry_run = state.get("dry_run", True)

    logger.info(
        "competitor_agent fetch_asin_data | target_asin=%s competitor_count=%d dry_run=%s",
        target_asin,
        len(competitor_asins),
        dry_run,
    )

    if dry_run:
        # dry_run 模式：使用 Mock 数据
        mock_data = {}
        if competitor_asins:
            # 如果指定了竞品ASIN，从Mock数据中找对应的，找不到则生成占位数据
            for asin in competitor_asins:
                if asin in _MOCK_COMPETITOR_DATA:
                    mock_data[asin] = _MOCK_COMPETITOR_DATA[asin]
                else:
                    # 生成占位Mock数据
                    mock_data[asin] = {
                        "asin": asin,
                        "title": f"Mock Product for {asin}",
                        "brand": "MockBrand",
                        "price": 24.99,
                        "bsr_rank": 300,
                        "rating": 4.0,
                        "review_count": 200,
                        "bullet_points": ["Mock Feature 1", "Mock Feature 2"],
                    }
        else:
            # 未指定竞品ASIN时，使用全部Mock数据
            mock_data = dict(_MOCK_COMPETITOR_DATA)

        state["competitor_data"] = mock_data
        logger.info(
            "competitor_agent fetch_asin_data | dry_run=True, 使用Mock数据 count=%d",
            len(mock_data),
        )
        return state

    # 非 dry_run 模式：此处预留真实 API 调用逻辑
    # 当前仅使用 Mock 数据兜底（避免爬取亚马逊页面）
    logger.warning(
        "competitor_agent fetch_asin_data | 非dry_run模式，真实API未实现，使用Mock数据兜底"
    )
    state["competitor_data"] = dict(_MOCK_COMPETITOR_DATA)
    return state


# ---------------------------------------------------------------------------
# 节点3：analyze_competitors — 分析每个竞品
# ---------------------------------------------------------------------------

def analyze_competitors(state: CompetitorState) -> CompetitorState:
    """对每个竞品调用 analyzer.py 进行分析，结果保存到 state["analysis_result"]。"""
    if state.get("error"):
        return state

    competitor_data = state.get("competitor_data", {})
    target_asin = state.get("target_asin", "")

    logger.info(
        "competitor_agent analyze_competitors | target_asin=%s count=%d",
        target_asin,
        len(competitor_data),
    )

    if not competitor_data:
        state["error"] = "没有竞品数据可供分析"
        state["status"] = "failed"
        return state

    analysis_result = {}
    market_avg = _calculate_market_avg(competitor_data)

    for asin, data in competitor_data.items():
        try:
            result = analyze_competitor_data(data)
            # 用市场均值重新计算竞争位置
            result["competitive_position"] = calculate_competitive_position(
                rating=float(data.get("rating", 0.0)),
                review_count=int(data.get("review_count", 0)),
                price=float(data.get("price", 0.0)),
                market_avg=market_avg,
            )
            analysis_result[asin] = result
        except Exception as exc:
            logger.warning("competitor_agent analyze_competitors | ASIN %s 分析失败: %s", asin, exc)
            analysis_result[asin] = {
                "asin": asin,
                "strengths": [],
                "weaknesses": [],
                "opportunities": [],
                "competitive_position": "unknown",
            }

    state["analysis_result"] = analysis_result
    logger.info(
        "competitor_agent analyze_competitors | 完成分析 count=%d",
        len(analysis_result),
    )
    return state


# ---------------------------------------------------------------------------
# 节点4：generate_profile — 构建 CompetitorAnalysis
# ---------------------------------------------------------------------------

def generate_profile(state: CompetitorState) -> CompetitorState:
    """构建 CompetitorAnalysis，保存到 state["competitor_profile"]。"""
    if state.get("error"):
        return state

    target_asin = state.get("target_asin", "")
    competitor_data = state.get("competitor_data", {})
    analysis_result = state.get("analysis_result", {})

    logger.info(
        "competitor_agent generate_profile | target_asin=%s",
        target_asin,
    )

    # 合并原始数据和分析结果，构建竞品画像列表
    competitor_profiles = []
    for asin, raw_data in competitor_data.items():
        analysis = analysis_result.get(asin, {})
        try:
            profile = CompetitorProfile(
                asin=asin,
                brand=raw_data.get("brand", ""),
                title=raw_data.get("title", ""),
                price=float(raw_data.get("price", 0.0)),
                bsr_rank=int(raw_data.get("bsr_rank", 0)),
                rating=float(raw_data.get("rating", 0.0)),
                review_count=int(raw_data.get("review_count", 0)),
                bullet_points=raw_data.get("bullet_points", []),
                strengths=analysis.get("strengths", []),
                weaknesses=analysis.get("weaknesses", []),
                opportunities=analysis.get("opportunities", []),
                competitive_position=analysis.get("competitive_position", "unknown"),
            )
            competitor_profiles.append(profile)
        except Exception as exc:
            logger.warning(
                "competitor_agent generate_profile | ASIN %s 画像构建失败: %s", asin, exc
            )

    # 构建完整分析报告
    try:
        analysis_report = build_competitor_analysis(
            target_asin=target_asin,
            competitor_profiles=competitor_profiles,
            dry_run=state.get("dry_run", True),
        )
        state["competitor_profile"] = analysis_report
        logger.info(
            "competitor_agent generate_profile | 完成 profiles=%d",
            len(competitor_profiles),
        )
    except Exception as exc:
        logger.error("competitor_agent generate_profile 失败: %s", exc)
        state["error"] = f"竞品画像生成失败: {exc}"
        state["status"] = "failed"

    return state


# ---------------------------------------------------------------------------
# 节点5：finalize_run — 更新DB状态，写审计日志
# ---------------------------------------------------------------------------

def finalize_run(state: CompetitorState) -> CompetitorState:
    """更新 agent_runs 状态为 completed 或 failed，写审计日志。"""
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    dry_run = state.get("dry_run", True)
    target_asin = state.get("target_asin", "")

    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info(
        "competitor_agent finalize_run | agent_run_id=%s status=%s",
        agent_run_id,
        final_status,
    )

    if not dry_run and _DB_AVAILABLE and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            competitor_profile = state.get("competitor_profile", {})
            output_summary = json.dumps({
                "target_asin": target_asin,
                "competitor_count": len(competitor_profile.get("competitor_profiles", [])),
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
                "competitor_agent finalize_run | DB已更新 agent_run_id=%s status=%s",
                agent_run_id,
                final_status,
            )
        except Exception as exc:
            logger.warning("competitor_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    # 写审计日志
    try:
        from src.utils.audit import log_action  # noqa: PLC0415
        log_action(
            action="competitor_agent.run",
            actor="competitor_agent",
            pre_state={
                "target_asin": target_asin,
                "dry_run": dry_run,
            },
            post_state={
                "agent_run_id": agent_run_id,
                "status": final_status,
                "error": error,
            },
        )
    except Exception as exc:
        logger.warning("competitor_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    return state


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _calculate_market_avg(competitor_data: dict) -> dict:
    """计算市场均值。"""
    if not competitor_data:
        return {"avg_price": 0.0, "avg_rating": 0.0, "avg_reviews": 0.0}

    prices = [float(d.get("price", 0.0)) for d in competitor_data.values() if d.get("price", 0.0) > 0]
    ratings = [float(d.get("rating", 0.0)) for d in competitor_data.values() if d.get("rating", 0.0) > 0]
    reviews = [int(d.get("review_count", 0)) for d in competitor_data.values()]

    return {
        "avg_price": round(sum(prices) / len(prices), 2) if prices else 0.0,
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
        "avg_reviews": round(sum(reviews) / len(reviews), 2) if reviews else 0.0,
    }

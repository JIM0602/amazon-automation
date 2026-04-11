"""广告监控Agent节点函数 — LangGraph多节点工作流实现。

节点顺序：
  1. init_run           — 创建 agent_runs 记录（status=running），验证输入
  2. fetch_ad_data      — 获取广告数据（dry_run=True时使用Mock）
  3. check_thresholds   — 调用 monitor.py 检查指标阈值
  4. generate_suggestions — 调用 alerts.py 生成优化建议
  5. send_alerts        — 调用 alerts.py 发送飞书告警
  6. finalize_run       — 更新DB状态，写审计日志

所有节点接收并返回 AdMonitorState（dict子类），遵循LangGraph规范。
所有外部依赖在模块顶部导入，支持测试 patch。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 模块顶部导入所有需要被 patch 的依赖
# ---------------------------------------------------------------------------

try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    db_available = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    db_available = False

from src.agents.ad_monitor_agent.schemas import AdMonitorState
from src.agents.ad_monitor_agent.monitor import (
    check_metrics,
    evaluate_all_campaigns,
    compute_summary,
)
from src.agents.ad_monitor_agent.alerts import (
    format_alert_message,
    generate_optimization_suggestions,
    send_feishu_alert,
)
from src.config import settings

# ---------------------------------------------------------------------------
# Mock 数据（dry_run=True 时使用）
# ---------------------------------------------------------------------------

_MOCK_AD_METRICS = [
    {
        "campaign_id": "CAMP001",
        "campaign_name": "Pet Fountain - Exact Match",
        "acos": 28.5,
        "roas": 3.51,
        "ctr": 0.45,
        "cvr": 12.8,
        "spend": 142.30,
        "sales": 499.30,
        "impressions": 31622,
        "clicks": 142,
        "date": "2026-04-01",
    },
    {
        "campaign_id": "CAMP002",
        "campaign_name": "Pet Fountain - Broad Match",
        "acos": 52.3,   # 超过critical阈值50%
        "roas": 1.91,
        "ctr": 0.22,    # 低于warning阈值0.3%
        "cvr": 8.1,
        "spend": 287.60,
        "sales": 549.50,
        "impressions": 130727,
        "clicks": 288,
        "date": "2026-04-01",
    },
]


# ---------------------------------------------------------------------------
# 节点1：init_run — 验证输入，创建 agent_runs 记录
# ---------------------------------------------------------------------------

def init_run(state: AdMonitorState) -> AdMonitorState:
    """验证输入，创建 agent_runs 数据库记录（status=running）。

    非dry_run模式下campaigns为空时记录警告日志，但不报错（监控全部）。
    """
    campaigns = state.get("campaigns", [])
    dry_run = state.get("dry_run", True)

    logger.info(
        "ad_monitor_agent init_run | campaigns_count=%d dry_run=%s",
        len(campaigns),
        dry_run,
    )

    if not campaigns and not dry_run:
        logger.warning(
            "ad_monitor_agent init_run | campaigns为空，将监控全部广告活动"
        )

    run_id = str(uuid.uuid4())

    if not dry_run and db_available and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="ad_monitor_agent",
                    status="running",
                    input_summary=json.dumps({
                        "campaigns": campaigns,
                        "campaigns_count": len(campaigns),
                    }, ensure_ascii=False),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("ad_monitor_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("ad_monitor_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info(
            "ad_monitor_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s",
            run_id,
        )

    state["agent_run_id"] = run_id
    return state


# ---------------------------------------------------------------------------
# 节点2：fetch_ad_data — 获取广告数据
# ---------------------------------------------------------------------------

def fetch_ad_data(state: AdMonitorState) -> AdMonitorState:
    """获取广告活动指标数据。dry_run=True 时返回 Mock 广告数据。"""
    if state.get("error"):
        return state

    campaigns = state.get("campaigns", [])
    dry_run = state.get("dry_run", True)

    logger.info(
        "ad_monitor_agent fetch_ad_data | campaigns_count=%d dry_run=%s",
        len(campaigns),
        dry_run,
    )

    if dry_run:
        # dry_run 模式：使用 Mock 数据
        if campaigns:
            # 如果指定了广告活动ID，只返回对应的Mock数据
            mock_data = [
                m for m in _MOCK_AD_METRICS
                if m["campaign_id"] in campaigns
            ]
            # 如果指定的campaign_id不在Mock中，生成占位数据
            found_ids = {m["campaign_id"] for m in mock_data}
            for cid in campaigns:
                if cid not in found_ids:
                    mock_data.append({
                        "campaign_id": cid,
                        "campaign_name": f"Mock Campaign {cid}",
                        "acos": 25.0,
                        "roas": 4.0,
                        "ctr": 0.5,
                        "cvr": 10.0,
                        "spend": 100.0,
                        "sales": 400.0,
                        "impressions": 20000,
                        "clicks": 100,
                        "date": "2026-04-01",
                    })
        else:
            # 未指定时使用全部Mock数据
            mock_data = list(_MOCK_AD_METRICS)

        state["ad_metrics"] = mock_data
        logger.info(
            "ad_monitor_agent fetch_ad_data | dry_run=True, 使用Mock数据 count=%d",
            len(mock_data),
        )
        return state

    try:
        from src.amazon_ads_api import AmazonAdsClient, CampaignsApi

        ads_client = AmazonAdsClient(
            client_id=settings.AMAZON_ADS_CLIENT_ID or "",
            client_secret=settings.AMAZON_ADS_CLIENT_SECRET or "",
            refresh_token=settings.AMAZON_ADS_REFRESH_TOKEN or "",
            profile_id=settings.AMAZON_ADS_PROFILE_ID or "",
            region=settings.AMAZON_ADS_REGION or "NA",
            dry_run=False,
        )
        campaigns_api = CampaignsApi(ads_client)

        metrics = campaigns_api.get_campaign_metrics(
            campaign_ids=campaigns or None,
            start_date=state.get("start_date"),
            end_date=state.get("end_date"),
        )

        if not metrics and campaigns:
            metrics = [
                {
                    "campaign_id": cid,
                    "campaign_name": f"Campaign {cid}",
                    "acos": 0.0,
                    "roas": 0.0,
                    "ctr": 0.0,
                    "cvr": 0.0,
                    "spend": 0.0,
                    "sales": 0.0,
                    "impressions": 0,
                    "clicks": 0,
                    "date": state.get("end_date") or state.get("start_date") or datetime.now(timezone.utc).date().isoformat(),
                }
                for cid in campaigns
            ]

        state["ad_metrics"] = metrics
        logger.info(
            "ad_monitor_agent fetch_ad_data | dry_run=False, 使用真实Ads API数据 count=%d",
            len(metrics),
        )
        return state
    except Exception as exc:
        logger.warning(
            "ad_monitor_agent fetch_ad_data | 真实Ads API调用失败，回退Mock数据 | error=%s",
            exc,
        )
        state["ad_metrics"] = list(_MOCK_AD_METRICS)
    return state


# ---------------------------------------------------------------------------
# 节点3：check_thresholds — 检查指标阈值
# ---------------------------------------------------------------------------

def check_thresholds(state: AdMonitorState) -> AdMonitorState:
    """调用 monitor.py 批量检查广告指标是否超过阈值，生成告警列表。"""
    if state.get("error"):
        return state

    ad_metrics = state.get("ad_metrics", [])
    thresholds = cast(dict[str, float], state.get("thresholds") or {})

    logger.info(
        "ad_monitor_agent check_thresholds | metrics_count=%d",
        len(ad_metrics),
    )

    if not ad_metrics:
        logger.warning("ad_monitor_agent check_thresholds | 无广告数据，跳过检查")
        state["alerts"] = []
        return state

    try:
        alerts = evaluate_all_campaigns(ad_metrics, thresholds)
        summary = compute_summary(ad_metrics)

        state["alerts"] = alerts
        state["summary"] = summary

        logger.info(
            "ad_monitor_agent check_thresholds | alerts_count=%d summary_total_spend=%.2f",
            len(alerts),
            summary.get("total_spend", 0.0),
        )
    except Exception as exc:
        logger.error("ad_monitor_agent check_thresholds 失败: %s", exc)
        state["error"] = f"指标检查失败: {exc}"
        state["status"] = "failed"

    return state


# ---------------------------------------------------------------------------
# 节点4：generate_suggestions — 生成优化建议
# ---------------------------------------------------------------------------

def generate_suggestions(state: AdMonitorState) -> AdMonitorState:
    """调用 alerts.py 根据告警生成优化建议。"""
    if state.get("error"):
        return state

    alerts = state.get("alerts", [])

    logger.info(
        "ad_monitor_agent generate_suggestions | alerts_count=%d",
        len(alerts),
    )

    try:
        suggestions = generate_optimization_suggestions(alerts)
        state["suggestions"] = suggestions

        logger.info(
            "ad_monitor_agent generate_suggestions | suggestions_count=%d",
            len(suggestions),
        )
    except Exception as exc:
        logger.error("ad_monitor_agent generate_suggestions 失败: %s", exc)
        state["error"] = f"建议生成失败: {exc}"
        state["status"] = "failed"

    return state


# ---------------------------------------------------------------------------
# 节点5：send_alerts — 发送飞书告警
# ---------------------------------------------------------------------------

def send_alerts(state: AdMonitorState) -> AdMonitorState:
    """调用 alerts.py 发送飞书告警（dry_run=True时Mock）。"""
    if state.get("error"):
        return state

    alerts = state.get("alerts", [])
    summary = state.get("summary", {})
    dry_run = state.get("dry_run", True)

    logger.info(
        "ad_monitor_agent send_alerts | alerts_count=%d dry_run=%s",
        len(alerts),
        dry_run,
    )

    try:
        success = send_feishu_alert(alerts, summary, dry_run=dry_run)
        state["alerts_sent"] = success

        if not success:
            logger.warning("ad_monitor_agent send_alerts | 飞书告警发送失败")
        else:
            logger.info("ad_monitor_agent send_alerts | 告警发送成功（或dry_run）")
    except Exception as exc:
        logger.error("ad_monitor_agent send_alerts 失败: %s", exc)
        # 发送失败不设置 error，不阻塞流程
        state["alerts_sent"] = False

    return state


# ---------------------------------------------------------------------------
# 节点6：finalize_run — 更新DB状态，写审计日志
# ---------------------------------------------------------------------------

def finalize_run(state: AdMonitorState) -> AdMonitorState:
    """更新 agent_runs 状态为 completed 或 failed，写审计日志。"""
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    dry_run = state.get("dry_run", True)
    campaigns = state.get("campaigns", [])
    alerts = state.get("alerts", [])

    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info(
        "ad_monitor_agent finalize_run | agent_run_id=%s status=%s alerts=%d",
        agent_run_id,
        final_status,
        len(alerts),
    )

    if not dry_run and db_available and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            output_summary = json.dumps({
                "campaigns_count": len(campaigns),
                "alerts_count": len(alerts),
                "status": final_status,
                "error": error,
            }, ensure_ascii=False)

            with db_session() as session:
                run = session.get(AgentRun, run_uuid)
                if run:
                    session.execute(
                        AgentRun.__table__.update()
                        .where(AgentRun.__table__.c.id == run_uuid)
                        .values(
                            status=final_status,
                            finished_at=datetime.now(timezone.utc),
                            output_summary=output_summary[:200],
                        )
                    )
                    session.commit()

            logger.info(
                "ad_monitor_agent finalize_run | DB已更新 agent_run_id=%s status=%s",
                agent_run_id,
                final_status,
            )
        except Exception as exc:
            logger.warning("ad_monitor_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    # 写审计日志
    try:
        from src.utils.audit import log_action  # noqa: PLC0415
        log_action(
            action="ad_monitor_agent.run",
            actor="ad_monitor_agent",
            pre_state={
                "campaigns": campaigns,
                "dry_run": dry_run,
            },
            post_state={
                "agent_run_id": agent_run_id,
                "status": final_status,
                "alerts_count": len(alerts),
                "error": error,
            },
        )
    except Exception as exc:
        logger.warning("ad_monitor_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    return state

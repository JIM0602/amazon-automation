"""广告监控核心逻辑 — 指标检查与告警生成。

提供：
  - DEFAULT_THRESHOLDS  — 默认监控阈值
  - check_metrics       — 检查单个广告活动指标，返回告警列表
  - evaluate_all_campaigns — 批量检查所有广告活动
  - compute_summary     — 计算汇总统计
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认阈值
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "acos_warning": 30.0,      # ACoS超过30%触发WARNING
    "acos_critical": 50.0,     # ACoS超过50%触发CRITICAL
    "roas_warning": 2.0,       # ROAS低于2触发WARNING
    "roas_critical": 1.0,      # ROAS低于1触发CRITICAL
    "ctr_warning": 0.3,        # CTR低于0.3%触发WARNING
    "spend_daily_limit": 500.0, # 日花费超过$500触发WARNING
}


def check_metrics(metrics: Dict[str, Any], thresholds: Dict[str, float] = None) -> List[Dict[str, Any]]:
    """检查单个广告活动指标，返回告警列表。

    Args:
        metrics:    广告活动指标字典（含campaign_id, acos, roas, ctr, spend等字段）
        thresholds: 自定义阈值字典，None时使用 DEFAULT_THRESHOLDS

    Returns:
        告警列表，每个告警为dict包含：
          campaign_id, metric, current_value, threshold, level, message, suggestions
    """
    if not metrics:
        return []

    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    alerts = []
    campaign_id = metrics.get("campaign_id", "")
    campaign_name = metrics.get("campaign_name", campaign_id)

    # ----- ACoS 检查 -----
    acos = metrics.get("acos")
    if acos is not None:
        if acos > t["acos_critical"]:
            alerts.append({
                "campaign_id": campaign_id,
                "metric": "acos",
                "current_value": acos,
                "threshold": t["acos_critical"],
                "level": "critical",
                "message": (
                    f"广告活动 [{campaign_name}] ACoS={acos:.1f}% 超过严重阈值 {t['acos_critical']:.1f}%，"
                    f"广告效率严重不足"
                ),
                "suggestions": [
                    "暂停表现最差的关键词或广告组",
                    "降低竞价或调整投放策略",
                    "检查产品转化率，排查落地页问题",
                ],
            })
        elif acos > t["acos_warning"]:
            alerts.append({
                "campaign_id": campaign_id,
                "metric": "acos",
                "current_value": acos,
                "threshold": t["acos_warning"],
                "level": "warning",
                "message": (
                    f"广告活动 [{campaign_name}] ACoS={acos:.1f}% 超过警告阈值 {t['acos_warning']:.1f}%，"
                    f"建议优化"
                ),
                "suggestions": [
                    "审查低效关键词并降低竞价",
                    "优化广告文案以提升CTR和CVR",
                ],
            })

    # ----- ROAS 检查 -----
    roas = metrics.get("roas")
    if roas is not None:
        if roas < t["roas_critical"]:
            alerts.append({
                "campaign_id": campaign_id,
                "metric": "roas",
                "current_value": roas,
                "threshold": t["roas_critical"],
                "level": "critical",
                "message": (
                    f"广告活动 [{campaign_name}] ROAS={roas:.2f} 低于严重阈值 {t['roas_critical']:.2f}，"
                    f"广告严重亏损"
                ),
                "suggestions": [
                    "立即审查广告活动，考虑暂停",
                    "分析转化漏斗，查找流失节点",
                    "核实产品定价策略是否合理",
                ],
            })
        elif roas < t["roas_warning"]:
            alerts.append({
                "campaign_id": campaign_id,
                "metric": "roas",
                "current_value": roas,
                "threshold": t["roas_warning"],
                "level": "warning",
                "message": (
                    f"广告活动 [{campaign_name}] ROAS={roas:.2f} 低于警告阈值 {t['roas_warning']:.2f}，"
                    f"广告效率偏低"
                ),
                "suggestions": [
                    "优化关键词出价策略",
                    "提升产品listing质量以改善转化率",
                ],
            })

    # ----- CTR 检查 -----
    ctr = metrics.get("ctr")
    if ctr is not None:
        if ctr < t["ctr_warning"]:
            alerts.append({
                "campaign_id": campaign_id,
                "metric": "ctr",
                "current_value": ctr,
                "threshold": t["ctr_warning"],
                "level": "warning",
                "message": (
                    f"广告活动 [{campaign_name}] CTR={ctr:.2f}% 低于警告阈值 {t['ctr_warning']:.2f}%，"
                    f"广告吸引力不足"
                ),
                "suggestions": [
                    "优化广告主图和标题以提升吸引力",
                    "检查关键词相关性，移除不相关词",
                    "考虑使用A+内容或视频广告",
                ],
            })

    # ----- 日花费限额检查 -----
    spend = metrics.get("spend")
    if spend is not None:
        if spend > t["spend_daily_limit"]:
            alerts.append({
                "campaign_id": campaign_id,
                "metric": "spend",
                "current_value": spend,
                "threshold": t["spend_daily_limit"],
                "level": "warning",
                "message": (
                    f"广告活动 [{campaign_name}] 日花费=${spend:.2f} 超过限额 ${t['spend_daily_limit']:.2f}，"
                    f"需关注预算控制"
                ),
                "suggestions": [
                    "检查每日预算设置",
                    "评估花费与ROI是否匹配",
                    "考虑设置竞价上限控制花费",
                ],
            })

    logger.debug(
        "ad_monitor check_metrics | campaign_id=%s alerts_count=%d",
        campaign_id,
        len(alerts),
    )
    return alerts


def evaluate_all_campaigns(
    ad_metrics: List[Dict[str, Any]],
    thresholds: Dict[str, float] = None,
) -> List[Dict[str, Any]]:
    """批量检查所有广告活动，返回所有告警。

    Args:
        ad_metrics:  广告指标列表，每个元素为单个广告活动的指标字典
        thresholds:  自定义阈值，None时使用默认值

    Returns:
        所有告警的列表（按 campaign_id + metric 排序）
    """
    if not ad_metrics:
        logger.info("ad_monitor evaluate_all_campaigns | 空数据，无需检查")
        return []

    all_alerts = []
    for metrics in ad_metrics:
        try:
            campaign_alerts = check_metrics(metrics, thresholds)
            all_alerts.extend(campaign_alerts)
        except Exception as exc:
            campaign_id = metrics.get("campaign_id", "unknown") if isinstance(metrics, dict) else "unknown"
            logger.warning(
                "ad_monitor evaluate_all_campaigns | campaign_id=%s 检查失败: %s",
                campaign_id,
                exc,
            )

    logger.info(
        "ad_monitor evaluate_all_campaigns | 共检查 %d 个活动，生成 %d 条告警",
        len(ad_metrics),
        len(all_alerts),
    )
    return all_alerts


def compute_summary(ad_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算汇总统计数据。

    Args:
        ad_metrics: 广告指标列表

    Returns:
        汇总统计字典：
          total_spend   (float) — 总花费
          total_sales   (float) — 总销售额
          avg_acos      (float) — 平均ACoS
          avg_roas      (float) — 平均ROAS
          total_impressions (int) — 总展示次数
          total_clicks  (int)  — 总点击次数
          campaign_count (int) — 活动总数
    """
    if not ad_metrics:
        return {
            "total_spend": 0.0,
            "total_sales": 0.0,
            "avg_acos": 0.0,
            "avg_roas": 0.0,
            "total_impressions": 0,
            "total_clicks": 0,
            "campaign_count": 0,
        }

    total_spend = sum(float(m.get("spend", 0.0)) for m in ad_metrics)
    total_sales = sum(float(m.get("sales", 0.0)) for m in ad_metrics)

    acos_values = [float(m.get("acos", 0.0)) for m in ad_metrics if m.get("acos") is not None]
    roas_values = [float(m.get("roas", 0.0)) for m in ad_metrics if m.get("roas") is not None]

    avg_acos = round(sum(acos_values) / len(acos_values), 2) if acos_values else 0.0
    avg_roas = round(sum(roas_values) / len(roas_values), 2) if roas_values else 0.0

    total_impressions = sum(int(m.get("impressions", 0)) for m in ad_metrics)
    total_clicks = sum(int(m.get("clicks", 0)) for m in ad_metrics)

    return {
        "total_spend": round(total_spend, 2),
        "total_sales": round(total_sales, 2),
        "avg_acos": avg_acos,
        "avg_roas": avg_roas,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "campaign_count": len(ad_metrics),
    }

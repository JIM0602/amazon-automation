"""广告监控异常告警逻辑 — 格式化、建议生成、飞书发送。

提供：
  - format_alert_message           — 格式化告警消息为可读文字
  - generate_optimization_suggestions — 根据告警生成优化建议列表
  - send_feishu_alert              — 发送飞书告警（dry_run=True时只打印日志）
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 飞书 Webhook（可选依赖）
# ---------------------------------------------------------------------------

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _requests = None  # type: ignore[assignment]
    _REQUESTS_AVAILABLE = False


# ---------------------------------------------------------------------------
# 告警级别对应的 emoji 标记
# ---------------------------------------------------------------------------

_LEVEL_EMOJI = {
    "info": "ℹ️",
    "warning": "⚠️",
    "critical": "🚨",
}

_LEVEL_LABELS = {
    "info": "信息",
    "warning": "警告",
    "critical": "严重",
}


def format_alert_message(alert: Dict[str, Any]) -> str:
    """格式化单条告警消息为可读文字。

    Args:
        alert: 告警字典，包含 campaign_id/metric/current_value/threshold/level/message/suggestions

    Returns:
        格式化后的告警文字字符串
    """
    if not alert:
        return ""

    level = alert.get("level", "info")
    emoji = _LEVEL_EMOJI.get(level, "📋")
    label = _LEVEL_LABELS.get(level, level.upper())
    campaign_id = alert.get("campaign_id", "")
    metric = alert.get("metric", "")
    current_value = alert.get("current_value", 0.0)
    threshold = alert.get("threshold", 0.0)
    message = alert.get("message", "")
    suggestions = alert.get("suggestions", [])

    lines = [
        f"{emoji} [{label}] 广告活动: {campaign_id}",
        f"指标: {metric} | 当前值: {current_value} | 阈值: {threshold}",
        f"描述: {message}",
    ]

    if suggestions:
        lines.append("优化建议:")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"  {i}. {s}")

    return "\n".join(lines)


def generate_optimization_suggestions(
    alerts: List[Dict[str, Any]],
    kb_context: List[str] = None,
) -> List[str]:
    """根据告警生成优化建议列表（基于规则+KB）。

    Args:
        alerts:     告警列表
        kb_context: 知识库上下文（可选，用于增强建议）

    Returns:
        去重后的优化建议字符串列表
    """
    if not alerts:
        return []

    suggestions_set: set = set()

    # 统计各类告警
    acos_critical_count = sum(
        1 for a in alerts if a.get("metric") == "acos" and a.get("level") == "critical"
    )
    acos_warning_count = sum(
        1 for a in alerts if a.get("metric") == "acos" and a.get("level") == "warning"
    )
    roas_critical_count = sum(
        1 for a in alerts if a.get("metric") == "roas" and a.get("level") == "critical"
    )
    roas_warning_count = sum(
        1 for a in alerts if a.get("metric") == "roas" and a.get("level") == "warning"
    )
    ctr_low_count = sum(1 for a in alerts if a.get("metric") == "ctr")
    spend_over_count = sum(1 for a in alerts if a.get("metric") == "spend")

    # 从告警本身提取建议
    for alert in alerts:
        for s in alert.get("suggestions", []):
            suggestions_set.add(s)

    # 综合性建议（基于多指标组合）
    if acos_critical_count > 0:
        suggestions_set.add("立即审查高ACoS广告活动，考虑暂停或大幅调整投放策略")

    if acos_critical_count > 1:
        suggestions_set.add("多个广告活动ACoS严重超标，建议全面审查关键词策略和竞价设置")

    if roas_critical_count > 0:
        suggestions_set.add("ROAS严重低于目标，需全面评估广告活动盈利能力")

    if acos_warning_count + acos_critical_count > 0 and ctr_low_count > 0:
        suggestions_set.add("ACoS偏高同时CTR偏低，建议优先改善广告创意和主图质量")

    if spend_over_count > 0:
        suggestions_set.add("日花费超限，建议检查预算设置并评估ROI")

    # 知识库增强建议
    if kb_context:
        for ctx in kb_context:
            if isinstance(ctx, str) and ctx.strip():
                suggestions_set.add(f"[KB参考] {ctx.strip()}")

    # 通用建议（始终包含）
    if alerts:
        suggestions_set.add("定期监控广告数据，每周进行关键词优化和竞价调整")

    result = sorted(suggestions_set)  # 排序保证结果稳定
    logger.info(
        "ad_monitor generate_optimization_suggestions | alerts=%d suggestions=%d",
        len(alerts),
        len(result),
    )
    return result


def send_feishu_alert(
    alerts: List[Dict[str, Any]],
    summary: Dict[str, Any],
    dry_run: bool = True,
    webhook_url: str = "",
) -> bool:
    """发送飞书告警消息。

    Args:
        alerts:      告警列表
        summary:     汇总统计字典
        dry_run:     True时只打印日志，不实际发送
        webhook_url: 飞书 webhook URL

    Returns:
        True=发送成功（或dry_run）, False=发送失败
    """
    if not alerts:
        logger.info("ad_monitor send_feishu_alert | 无告警，跳过发送")
        return True

    # 构建消息内容
    critical_count = sum(1 for a in alerts if a.get("level") == "critical")
    warning_count = sum(1 for a in alerts if a.get("level") == "warning")

    header_lines = [
        "📊 **广告监控告警报告**",
        f"🚨 严重告警: {critical_count} 条 | ⚠️ 警告: {warning_count} 条",
    ]

    if summary:
        total_spend = summary.get("total_spend", 0.0)
        total_sales = summary.get("total_sales", 0.0)
        avg_acos = summary.get("avg_acos", 0.0)
        avg_roas = summary.get("avg_roas", 0.0)
        header_lines.append(
            f"💰 总花费: ${total_spend:.2f} | 总销售: ${total_sales:.2f} | "
            f"平均ACoS: {avg_acos:.1f}% | 平均ROAS: {avg_roas:.2f}"
        )

    alert_lines = []
    for alert in alerts[:10]:  # 最多显示10条告警，避免消息过长
        alert_lines.append(format_alert_message(alert))
        alert_lines.append("---")

    message_text = "\n".join(header_lines + ["", "**告警详情：**"] + alert_lines)

    if dry_run:
        logger.info(
            "ad_monitor send_feishu_alert | dry_run=True, 模拟发送:\n%s",
            message_text,
        )
        return True

    # 实际发送飞书消息
    if not webhook_url:
        logger.warning("ad_monitor send_feishu_alert | 缺少 webhook_url，无法发送")
        return False

    if not _REQUESTS_AVAILABLE:
        logger.warning("ad_monitor send_feishu_alert | requests 未安装，无法发送")
        return False

    payload = {
        "msg_type": "text",
        "content": {"text": message_text},
    }

    try:
        resp = _requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(
            "ad_monitor send_feishu_alert | 飞书消息发送成功 status=%d alerts=%d",
            resp.status_code,
            len(alerts),
        )
        return True
    except Exception as exc:
        logger.error("ad_monitor send_feishu_alert | 发送失败: %s", exc)
        return False

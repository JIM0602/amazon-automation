"""Policy Engine — 与决策流程的集成工具。

提供 submit_for_approval() 包装函数，在提交审批前自动进行规则检查。
违规时阻止提交并返回违规详情；合规时委托 create_approval_request()。

使用方式::

    from src.policy.integration import submit_for_approval

    result = submit_for_approval(
        decision_type="price_adjustment",
        action_type="price_adjustment",
        description="调整 SKU-123 价格",
        impact="1 个 SKU",
        reason="竞品降价",
        risks="收益下降",
        payload={"current_price": 19.99, "new_price": 22.99, "sku": "SKU-123"},
    )

    if result["allowed"]:
        approval_id = result["approval_id"]
    else:
        violations = result["violations"]
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.policy.engine import get_policy_engine
from src.policy.models import Violation

logger = logging.getLogger(__name__)


def submit_for_approval(
    decision_type: str,
    action_type: str,
    description: str,
    impact: str,
    reason: str,
    risks: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout_hours: float = 24.0,
    chat_id: Optional[str] = None,
    skip_policy_check: bool = False,
) -> Dict[str, Any]:
    """执行 Policy 检查后提交审批请求。

    Args:
        decision_type:      决策类型（用于规则过滤），如 "price_adjustment"
        action_type:        审批 action_type（存储到 DB），通常与 decision_type 相同
        description:        操作描述
        impact:             影响范围
        reason:             操作原因
        risks:              潜在风险
        payload:            决策 payload，用于规则检查（不存储到 DB）
        timeout_hours:      审批超时小时数（默认 24）
        chat_id:            飞书群 ID（None 时从 settings 读取）
        skip_policy_check:  是否跳过规则检查（不应在生产中使用）

    Returns:
        dict，格式如下：
        {
            "allowed": bool,           # 是否通过规则检查
            "approval_id": str | None, # 审批 ID（违规时为 None）
            "violations": List[dict],  # 违规列表
            "warnings": List[dict],    # 警告列表
            "decision_type": str,
        }
    """
    payload = payload or {}

    # === 1. Policy 检查 ===
    if not skip_policy_check:
        engine = get_policy_engine()
        policy_result = engine.check(decision_type, payload)

        if not policy_result.allowed:
            logger.warning(
                "Policy 检查未通过，阻止提交审批: decision_type=%s violations=%d",
                decision_type,
                len(policy_result.violations),
            )
            return {
                "allowed": False,
                "approval_id": None,
                "violations": [v.to_dict() for v in policy_result.violations],
                "warnings": [w.to_dict() for w in policy_result.warnings],
                "decision_type": decision_type,
                "message": f"规则检查失败，共 {len(policy_result.violations)} 条违规",
            }
    else:
        logger.warning("Policy 检查已跳过（skip_policy_check=True）: decision_type=%s", decision_type)
        policy_result = None

    # === 2. 提交审批 ===
    try:
        from src.feishu.approval import create_approval_request
        approval_id = create_approval_request(
            action_type=action_type,
            description=description,
            impact=impact,
            reason=reason,
            risks=risks,
            timeout_hours=timeout_hours,
            chat_id=chat_id,
        )
        logger.info(
            "审批请求已提交: approval_id=%s decision_type=%s",
            approval_id, decision_type,
        )
        warnings = [w.to_dict() for w in policy_result.warnings] if policy_result else []
        return {
            "allowed": True,
            "approval_id": approval_id,
            "violations": [],
            "warnings": warnings,
            "decision_type": decision_type,
            "message": "审批请求已提交",
        }
    except Exception as exc:
        logger.error("提交审批请求失败: %s", exc)
        return {
            "allowed": True,  # 规则检查通过，但提交失败
            "approval_id": None,
            "violations": [],
            "warnings": [],
            "decision_type": decision_type,
            "message": f"审批提交失败: {exc}",
            "error": str(exc),
        }

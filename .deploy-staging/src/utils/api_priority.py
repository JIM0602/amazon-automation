"""API 调用优先级定义模块。

定义系统中各类 API 调用的优先级枚举，用于限流控制器按优先级分配令牌。

优先级顺序（高 → 低）：
  critical  — 风控/紧急调价，weight=1.0，不可被降级
  normal    — 广告执行，weight=0.6
  batch     — 市场调研/批量任务，weight=0.3
"""
from __future__ import annotations

from enum import Enum


class ApiPriority(Enum):
    """API 调用优先级枚举。

    值为优先级权重（float），用于令牌桶调度时的权重计算。

    Examples::

        priority = ApiPriority.CRITICAL
        weight = priority.weight  # 1.0
    """

    CRITICAL = "critical"   # 风控/紧急调价 — 最高优先级
    NORMAL = "normal"       # 广告执行 — 正常优先级
    BATCH = "batch"         # 市场调研/批量任务 — 最低优先级

    @property
    def weight(self) -> float:
        """返回优先级对应的令牌权重。

        Returns:
            float: critical=1.0, normal=0.6, batch=0.3
        """
        _weights = {
            "critical": 1.0,
            "normal": 0.6,
            "batch": 0.3,
        }
        return _weights[self.value]

    @property
    def order(self) -> int:
        """返回优先级排序值（越小越高优先级），用于优先级队列排序。

        Returns:
            int: critical=0, normal=1, batch=2
        """
        _orders = {
            "critical": 0,
            "normal": 1,
            "batch": 2,
        }
        return _orders[self.value]


# ---------------------------------------------------------------------------
# API 分组到优先级的映射
# ---------------------------------------------------------------------------

#: 各 API 组名到优先级的映射
API_GROUP_PRIORITY: dict[str, ApiPriority] = {
    # 风控/紧急调价 — critical
    "risk_control": ApiPriority.CRITICAL,
    "emergency_pricing": ApiPriority.CRITICAL,
    # 广告执行 — normal
    "ad_execution": ApiPriority.NORMAL,
    "pricing": ApiPriority.NORMAL,
    "llm": ApiPriority.NORMAL,
    # 市场调研/批量任务 — batch
    "market_research": ApiPriority.BATCH,
    "seller_sprite": ApiPriority.BATCH,
    "batch": ApiPriority.BATCH,
}


def get_priority(api_group: str) -> ApiPriority:
    """根据 API 分组名称获取对应优先级。

    未知分组默认返回 BATCH 优先级。

    Args:
        api_group: API 分组名称，如 "llm"、"seller_sprite"

    Returns:
        ApiPriority 枚举值
    """
    return API_GROUP_PRIORITY.get(api_group.lower(), ApiPriority.BATCH)

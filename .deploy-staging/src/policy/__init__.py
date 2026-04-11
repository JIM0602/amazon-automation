"""Policy Engine — 业务规则硬约束模块。

防止 AI 做出违规决策。提供：
- PolicyEngine：规则引擎核心，支持注册自定义规则
- 内置规则：价格规则、广告规则、库存规则
- PolicyResult / Violation / Warning：结果模型
"""
from src.policy.engine import PolicyEngine, get_policy_engine
from src.policy.models import PolicyResult, Violation, Warning

__all__ = [
    "PolicyEngine",
    "get_policy_engine",
    "PolicyResult",
    "Violation",
    "Warning",
]

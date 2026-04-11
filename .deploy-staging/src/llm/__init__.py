"""LLM 模块公共接口。

导出:
  - chat           — 统一 LLM 调用接口
  - DailyCostLimitExceeded — 每日费用超限异常
  - filter_pii     — PII 过滤函数
  - get_daily_cost — 查询今日总费用
  - check_daily_limit — 检查每日限额状态
"""

from src.llm.client import chat, DailyCostLimitExceeded
from src.llm.cost_monitor import filter_pii, get_daily_cost, check_daily_limit

__all__ = [
    "chat",
    "DailyCostLimitExceeded",
    "filter_pii",
    "get_daily_cost",
    "check_daily_limit",
]

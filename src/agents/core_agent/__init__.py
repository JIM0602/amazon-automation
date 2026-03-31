"""Core management agents package.

Exports:
    DailyReportAgent    — 每日数据汇报 Agent
    generate_daily_report — 快捷函数，生成日报数据
    generate_feishu_card  — 生成飞书卡片 JSON
"""
from src.agents.core_agent.daily_report import (
    DailyReportAgent,
    generate_daily_report,
    generate_feishu_card,
)

__all__ = [
    "DailyReportAgent",
    "generate_daily_report",
    "generate_feishu_card",
]

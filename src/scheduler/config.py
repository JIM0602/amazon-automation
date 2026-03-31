"""调度器任务配置 — 预定义3个定时任务。"""
from __future__ import annotations

SCHEDULED_JOBS = [
    {
        "id": "daily_report",
        "func": "src.scheduler.jobs:run_daily_report",
        "trigger": "cron",
        "hour": 9,
        "minute": 0,
        "description": "每日09:00发送数据日报到飞书",
    },
    {
        "id": "selection_analysis",
        "func": "src.scheduler.jobs:run_selection_analysis",
        "trigger": "cron",
        "day_of_week": "mon",
        "hour": 10,
        "minute": 0,
        "description": "每周一10:00运行选品分析",
    },
    {
        "id": "llm_cost_report",
        "func": "src.scheduler.jobs:run_llm_cost_report",
        "trigger": "cron",
        "hour": 23,
        "minute": 0,
        "description": "每日23:00发送LLM费用日报",
    },
]

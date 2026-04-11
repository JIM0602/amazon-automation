"""选品分析 Agent 包。

公开接口：
    run(category, dry_run, subcategory) -> dict
        执行选品分析，返回包含≥3个候选产品的报告。

用法：
    from src.agents.selection_agent import run
    report = run(category='pet_supplies', dry_run=True)
"""
from src.agents.selection_agent.agent import execute as run
from src.agents.selection_agent.schema import (
    ProductCandidate,
    SelectionReport,
    SelectionState,
    RESTRICTED_CATEGORIES,
)

__all__ = [
    "run",
    "ProductCandidate",
    "SelectionReport",
    "SelectionState",
    "RESTRICTED_CATEGORIES",
]

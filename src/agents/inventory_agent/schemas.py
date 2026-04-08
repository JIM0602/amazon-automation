"""库存监控 Agent 数据结构定义。"""
from __future__ import annotations

from typing import Any, Optional


class InventoryState(dict[str, Any]):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。"""

    def __init__(
        self,
        sku_list: Optional[list[str]] = None,
        threshold_days: int = 30,
        dry_run: bool = True,
        **kwargs: Any,
    ):
        super().__init__(
            sku_list=sku_list or [],
            threshold_days=threshold_days,
            dry_run=dry_run,
            inventory_data=[],
            analysis={},
            alerts=[],
            agent_run_id=None,
            status="running",
            error=None,
            **kwargs,
        )

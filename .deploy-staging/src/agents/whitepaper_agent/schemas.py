"""白皮书 Agent 状态定义。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class WhitepaperState(dict[str, Any]):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。"""

    def __init__(
        self,
        dry_run: bool = True,
        product_name: str = "",
        asin: str = "",
        category: str = "",
        target_audience: str = "",
        kb_research: Optional[List[str]] = None,
        market_data: Optional[Dict[str, Any]] = None,
        competitor_summary: Optional[Dict[str, Any]] = None,
        whitepaper_sections: Optional[Dict[str, Any]] = None,
        report: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(
            dry_run=dry_run,
            agent_run_id=None,
            error=None,
            status="running",
            product_name=product_name,
            asin=asin,
            category=category,
            target_audience=target_audience,
            kb_research=kb_research or [],
            market_data=market_data or {},
            competitor_summary=competitor_summary or {},
            whitepaper_sections=whitepaper_sections or {},
            report=report or {},
            **kwargs,
        )

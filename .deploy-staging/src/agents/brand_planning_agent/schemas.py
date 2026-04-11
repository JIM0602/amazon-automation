"""品牌规划 Agent 状态定义。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class BrandPlanningState(dict[str, Any]):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。

    键说明：
      dry_run        (bool)  — 是否 dry run 模式
      agent_run_id   (str)  — agent_runs 表主键
      error          (str)  — 错误信息（若有）
      status         (str)  — 当前状态 running/completed/failed
      brand_name     (str)  — 品牌名称
      category       (str)  — 类目
      target_market  (str)  — 目标市场
      budget_range   (str)  — 预算范围
      market_analysis (dict) — 市场分析结果
      kb_insights    (list) — 知识库洞察
      brand_strategy  (dict) — 品牌策略
      report         (dict) — 最终报告
    """

    def __init__(
        self,
        dry_run: bool = True,
        brand_name: str = "",
        category: str = "",
        target_market: str = "US",
        budget_range: str = "",
        kb_insights: Optional[List[str]] = None,
        market_analysis: Optional[Dict[str, Any]] = None,
        brand_strategy: Optional[Dict[str, Any]] = None,
        report: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(
            dry_run=dry_run,
            agent_run_id=None,
            error=None,
            status="running",
            brand_name=brand_name,
            category=category,
            target_market=target_market,
            budget_range=budget_range,
            kb_insights=kb_insights or [],
            market_analysis=market_analysis or {},
            brand_strategy=brand_strategy or {},
            report=report or {},
            **kwargs,
        )

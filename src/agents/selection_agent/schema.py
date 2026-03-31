"""选品分析 Agent 数据结构定义（Schema）。

包含：
  - SelectionState   — LangGraph 工作流状态
  - ProductCandidate — 候选产品数据结构
  - SelectionReport  — 最终分析报告
  - RESTRICTED_CATEGORIES — 亚马逊限制类目列表
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 亚马逊限制类目（不推荐进入的类目）
# ---------------------------------------------------------------------------
RESTRICTED_CATEGORIES = [
    "weapons",
    "firearms",
    "ammunition",
    "drugs",
    "tobacco",
    "alcohol",
    "hazardous_materials",
    "adult_content",
    "gambling",
    "medical_devices_class_iii",
    "live_plants_seeds",  # 有检疫限制
]


@dataclass
class ProductCandidate:
    """单个候选产品信息。"""

    asin: str
    product_name: str
    reason: str                        # 选品理由（必须引用知识库内容）
    market_data: Dict[str, Any]        # 市场数据（来自 SellerSprite）
    risks: List[str]                   # 风险提示
    score: float                       # 综合评分 0-10
    kb_references: List[str] = field(default_factory=list)  # 引用的知识库原则

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asin": self.asin,
            "product_name": self.product_name,
            "reason": self.reason,
            "market_data": self.market_data,
            "risks": self.risks,
            "score": self.score,
            "kb_references": self.kb_references,
        }


@dataclass
class SelectionReport:
    """选品分析最终报告。"""

    category: str
    analysis_date: str
    candidates: List[ProductCandidate]
    kb_principles_used: List[str]
    agent_run_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "analysis_date": self.analysis_date,
            "candidates": [c.to_dict() for c in self.candidates],
            "kb_principles_used": self.kb_principles_used,
            "agent_run_id": self.agent_run_id,
        }


# ---------------------------------------------------------------------------
# LangGraph 状态定义（TypedDict 兼容格式）
# ---------------------------------------------------------------------------

class SelectionState(dict):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。

    键说明：
      category       (str)  — 分析类目
      dry_run        (bool) — 是否 dry run 模式
      subcategory    (str)  — 子类目（可选，来自飞书指令）
      agent_run_id   (str)  — agent_runs 表主键
      raw_market_data (dict) — SellerSprite 采集的原始数据
      kb_results     (list) — 知识库检索结果
      llm_analysis   (str)  — LLM 分析文本
      candidates     (list) — 最终候选产品列表（ProductCandidate.to_dict()）
      report         (dict) — 最终报告 JSON
      error          (str)  — 错误信息（若有）
      status         (str)  — 当前状态 running/completed/failed
    """

    def __init__(
        self,
        category: str = "pet_supplies",
        dry_run: bool = True,
        subcategory: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            category=category,
            dry_run=dry_run,
            subcategory=subcategory,
            agent_run_id=None,
            raw_market_data={},
            kb_results=[],
            llm_analysis="",
            candidates=[],
            report={},
            error=None,
            status="running",
            **kwargs,
        )

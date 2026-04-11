"""用户画像Agent输出Schema — 使用Pydantic定义数据结构。

包含：
  - UserPersona   — 用户画像（人口特征/痛点/动机/触发词/人群标签）
  - PersonaState  — LangGraph工作流状态
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, field_validator
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False
    BaseModel = object  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Pydantic 输出 Schema
# ---------------------------------------------------------------------------

if _PYDANTIC_AVAILABLE:
    class UserPersona(BaseModel):
        """用户画像（使用Pydantic验证）。"""

        category: str = Field(default="", description="产品类目，如'宠物水杯'")
        asin: str = Field(default="", description="来源ASIN（可选）")
        demographics: Dict[str, str] = Field(
            default_factory=lambda: {
                "age_range": "",
                "gender": "",
                "income_level": "",
                "lifestyle": "",
            },
            description="人口特征: age_range/gender/income_level/lifestyle",
        )
        pain_points: List[str] = Field(default_factory=list, description="用户痛点列表")
        motivations: List[str] = Field(default_factory=list, description="购买动机列表")
        trigger_words: List[str] = Field(default_factory=list, description="购买触发词列表")
        persona_tags: List[str] = Field(
            default_factory=list,
            description="人群标签，如'养宠人士'/'爱干净'/'重品质'",
        )
        data_sources: List[str] = Field(default_factory=list, description="数据来源列表")

        def to_dict(self) -> Dict[str, Any]:
            return self.model_dump()

else:
    # Pydantic 不可用时的降级版本
    class UserPersona:  # type: ignore[no-redef]
        def __init__(
            self,
            category: str = "",
            asin: str = "",
            demographics: Dict[str, str] = None,
            pain_points: List[str] = None,
            motivations: List[str] = None,
            trigger_words: List[str] = None,
            persona_tags: List[str] = None,
            data_sources: List[str] = None,
        ):
            self.category = category
            self.asin = asin
            self.demographics = demographics or {
                "age_range": "",
                "gender": "",
                "income_level": "",
                "lifestyle": "",
            }
            self.pain_points = pain_points or []
            self.motivations = motivations or []
            self.trigger_words = trigger_words or []
            self.persona_tags = persona_tags or []
            self.data_sources = data_sources or []

        def to_dict(self) -> Dict[str, Any]:
            return {
                "category": self.category,
                "asin": self.asin,
                "demographics": self.demographics,
                "pain_points": self.pain_points,
                "motivations": self.motivations,
                "trigger_words": self.trigger_words,
                "persona_tags": self.persona_tags,
                "data_sources": self.data_sources,
            }


# ---------------------------------------------------------------------------
# LangGraph 状态定义
# ---------------------------------------------------------------------------

class PersonaState(dict):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。

    键说明：
      category        (str)  — 产品类目，如'宠物水杯'
      asin            (str)  — 来源ASIN（可选）
      raw_reviews     (list) — 原始评论/Q&A数据
      kb_context      (list) — 知识库检索结果
      analysis_result (dict) — 分析中间结果
      user_persona    (dict) — 最终用户画像（UserPersona.to_dict()）
      dry_run         (bool) — 是否dry run模式（True=使用Mock数据）
      agent_run_id    (str)  — agent_runs表主键
      error           (str)  — 错误信息（若有）
      status          (str)  — 当前状态 running/completed/failed
    """

    def __init__(
        self,
        category: str = "",
        asin: str = "",
        raw_reviews: List[Any] = None,
        kb_context: List[Any] = None,
        analysis_result: Dict[str, Any] = None,
        user_persona: Dict[str, Any] = None,
        dry_run: bool = True,
        **kwargs,
    ):
        super().__init__(
            category=category,
            asin=asin,
            raw_reviews=raw_reviews or [],
            kb_context=kb_context or [],
            analysis_result=analysis_result or {},
            user_persona=user_persona or {},
            dry_run=dry_run,
            agent_run_id=None,
            error=None,
            status="running",
            **kwargs,
        )

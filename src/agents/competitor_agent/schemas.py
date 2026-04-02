"""竞品调研Agent输出Schema — 使用Pydantic定义数据结构。

包含：
  - CompetitorProfile   — 单个竞品的竞争力画像
  - CompetitorAnalysis  — 完整竞品分析报告
  - CompetitorState     — LangGraph工作流状态
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

_VALID_COMPETITIVE_POSITIONS = {"strong", "moderate", "weak", "unknown"}

if _PYDANTIC_AVAILABLE:
    class CompetitorProfile(BaseModel):
        """单个竞品画像（使用Pydantic验证）。"""

        asin: str = Field(default="", description="竞品ASIN")
        brand: str = Field(default="", description="品牌名称")
        title: str = Field(default="", description="产品标题")
        price: float = Field(default=0.0, description="售价（美元）")
        bsr_rank: int = Field(default=0, description="BSR排名")
        rating: float = Field(default=0.0, description="评分（0-5）")
        review_count: int = Field(default=0, description="评论数量")
        bullet_points: List[str] = Field(default_factory=list, description="产品要点")
        strengths: List[str] = Field(default_factory=list, description="优势列表")
        weaknesses: List[str] = Field(default_factory=list, description="劣势列表")
        opportunities: List[str] = Field(default_factory=list, description="机会列表")
        competitive_position: str = Field(default="unknown", description="竞争位置: strong/moderate/weak/unknown")

        @field_validator("rating")
        @classmethod
        def rating_must_be_valid(cls, v: float) -> float:
            if not (0.0 <= v <= 5.0):
                raise ValueError(f"评分必须在0-5之间，实际值: {v}")
            return v

        @field_validator("competitive_position")
        @classmethod
        def position_must_be_valid(cls, v: str) -> str:
            if v not in _VALID_COMPETITIVE_POSITIONS:
                raise ValueError(f"竞争位置必须是 {_VALID_COMPETITIVE_POSITIONS} 之一，实际值: {v}")
            return v

        def to_dict(self) -> Dict[str, Any]:
            return self.model_dump()

    class CompetitorAnalysis(BaseModel):
        """完整竞品分析报告。"""

        target_asin: str = Field(default="", description="目标产品ASIN")
        competitor_profiles: List[CompetitorProfile] = Field(
            default_factory=list,
            description="竞品画像列表",
        )
        market_summary: str = Field(default="", description="市场概要")
        price_range: Dict[str, float] = Field(
            default_factory=lambda: {"min": 0.0, "max": 0.0, "avg": 0.0},
            description="价格区间（min/max/avg）",
        )
        avg_rating: float = Field(default=0.0, description="竞品平均评分")
        top_keywords: List[str] = Field(default_factory=list, description="高频关键词")
        differentiation_suggestions: List[str] = Field(
            default_factory=list,
            description="差异化建议",
        )

        def to_dict(self) -> Dict[str, Any]:
            result = self.model_dump()
            result["competitor_profiles"] = [p.to_dict() for p in self.competitor_profiles]
            return result

else:
    # Pydantic 不可用时的降级版本
    class CompetitorProfile:  # type: ignore[no-redef]
        def __init__(
            self,
            asin: str = "",
            brand: str = "",
            title: str = "",
            price: float = 0.0,
            bsr_rank: int = 0,
            rating: float = 0.0,
            review_count: int = 0,
            bullet_points: List[str] = None,
            strengths: List[str] = None,
            weaknesses: List[str] = None,
            opportunities: List[str] = None,
            competitive_position: str = "unknown",
        ):
            if not (0.0 <= rating <= 5.0):
                raise ValueError(f"评分必须在0-5之间，实际值: {rating}")
            if competitive_position not in _VALID_COMPETITIVE_POSITIONS:
                raise ValueError(f"竞争位置必须是 {_VALID_COMPETITIVE_POSITIONS} 之一，实际值: {competitive_position}")
            self.asin = asin
            self.brand = brand
            self.title = title
            self.price = price
            self.bsr_rank = bsr_rank
            self.rating = rating
            self.review_count = review_count
            self.bullet_points = bullet_points or []
            self.strengths = strengths or []
            self.weaknesses = weaknesses or []
            self.opportunities = opportunities or []
            self.competitive_position = competitive_position

        def to_dict(self) -> Dict[str, Any]:
            return {
                "asin": self.asin,
                "brand": self.brand,
                "title": self.title,
                "price": self.price,
                "bsr_rank": self.bsr_rank,
                "rating": self.rating,
                "review_count": self.review_count,
                "bullet_points": self.bullet_points,
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
                "opportunities": self.opportunities,
                "competitive_position": self.competitive_position,
            }

    class CompetitorAnalysis:  # type: ignore[no-redef]
        def __init__(
            self,
            target_asin: str = "",
            competitor_profiles: List = None,
            market_summary: str = "",
            price_range: Dict[str, float] = None,
            avg_rating: float = 0.0,
            top_keywords: List[str] = None,
            differentiation_suggestions: List[str] = None,
        ):
            self.target_asin = target_asin
            self.competitor_profiles = competitor_profiles or []
            self.market_summary = market_summary
            self.price_range = price_range or {"min": 0.0, "max": 0.0, "avg": 0.0}
            self.avg_rating = avg_rating
            self.top_keywords = top_keywords or []
            self.differentiation_suggestions = differentiation_suggestions or []

        def to_dict(self) -> Dict[str, Any]:
            return {
                "target_asin": self.target_asin,
                "competitor_profiles": [
                    p.to_dict() if hasattr(p, "to_dict") else p
                    for p in self.competitor_profiles
                ],
                "market_summary": self.market_summary,
                "price_range": self.price_range,
                "avg_rating": self.avg_rating,
                "top_keywords": self.top_keywords,
                "differentiation_suggestions": self.differentiation_suggestions,
            }


# ---------------------------------------------------------------------------
# LangGraph 状态定义
# ---------------------------------------------------------------------------

class CompetitorState(dict):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。

    键说明：
      target_asin         (str)  — 目标产品ASIN
      competitor_asins    (list) — 待分析的竞品ASIN列表
      competitor_data     (dict) — 抓取到的竞品原始数据
      analysis_result     (dict) — 分析结果中间数据
      competitor_profile  (dict) — 最终竞品分析报告（CompetitorAnalysis.to_dict()）
      dry_run             (bool) — 是否dry run模式（True=使用Mock数据）
      agent_run_id        (str)  — agent_runs表主键
      error               (str)  — 错误信息（若有）
      status              (str)  — 当前状态 running/completed/failed
    """

    def __init__(
        self,
        target_asin: str = "",
        competitor_asins: List[str] = None,
        competitor_data: Dict[str, Any] = None,
        analysis_result: Dict[str, Any] = None,
        competitor_profile: Dict[str, Any] = None,
        dry_run: bool = True,
        **kwargs,
    ):
        super().__init__(
            target_asin=target_asin,
            competitor_asins=competitor_asins or [],
            competitor_data=competitor_data or {},
            analysis_result=analysis_result or {},
            competitor_profile=competitor_profile or {},
            dry_run=dry_run,
            agent_run_id=None,
            error=None,
            status="running",
            **kwargs,
        )

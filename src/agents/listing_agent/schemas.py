"""Listing文案Agent输出Schema — 使用Pydantic定义数据结构。

包含：
  - ListingCopy      — 完整Listing文案输出
  - ListingState     — LangGraph工作流状态
  - ProductInfo      — 产品信息输入结构
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    class ListingCopySchema(BaseModel):
        """亚马逊Listing文案输出Schema（使用Pydantic验证）。"""

        asin: str = Field(default="", description="产品ASIN")
        title: str = Field(
            default="",
            description="产品标题，不超过200字符",
            max_length=200,
        )
        bullet_points: List[str] = Field(
            default_factory=list,
            description="五点描述，每条描述产品关键卖点",
            min_length=5,
            max_length=5,
        )
        search_terms: str = Field(
            default="",
            description="后台关键词，不超过250字符",
            max_length=250,
        )
        aplus_copy: Optional[str] = Field(
            default=None,
            description="A+文案建议（可选）",
        )
        compliance_passed: bool = Field(
            default=False,
            description="是否通过合规检查",
        )
        compliance_issues: List[str] = Field(
            default_factory=list,
            description="合规问题列表",
        )
        kb_tips_used: List[str] = Field(
            default_factory=list,
            description="使用的知识库文案技巧",
        )

        @field_validator("title")
        @classmethod
        def title_must_not_be_empty(cls, v: str) -> str:
            if not v.strip():
                raise ValueError("标题不能为空")
            return v

        @field_validator("bullet_points")
        @classmethod
        def bullet_points_must_have_5(cls, v: List[str]) -> List[str]:
            if len(v) != 5:
                raise ValueError(f"五点描述必须恰好5条，实际: {len(v)}")
            return v

        def to_dict(self) -> Dict[str, Any]:
            return self.model_dump()

else:
    # Pydantic 不可用时的降级版本（普通 dataclass）
    class ListingCopySchema:  # type: ignore[no-redef]
        def __init__(
            self,
            asin: str = "",
            title: str = "",
            bullet_points: List[str] = None,
            search_terms: str = "",
            aplus_copy: Optional[str] = None,
            compliance_passed: bool = False,
            compliance_issues: List[str] = None,
            kb_tips_used: List[str] = None,
        ):
            self.asin = asin
            self.title = title
            self.bullet_points = bullet_points or []
            self.search_terms = search_terms
            self.aplus_copy = aplus_copy
            self.compliance_passed = compliance_passed
            self.compliance_issues = compliance_issues or []
            self.kb_tips_used = kb_tips_used or []

        def to_dict(self) -> Dict[str, Any]:
            return {
                "asin": self.asin,
                "title": self.title,
                "bullet_points": self.bullet_points,
                "search_terms": self.search_terms,
                "aplus_copy": self.aplus_copy,
                "compliance_passed": self.compliance_passed,
                "compliance_issues": self.compliance_issues,
                "kb_tips_used": self.kb_tips_used,
            }


# ---------------------------------------------------------------------------
# 产品信息输入结构
# ---------------------------------------------------------------------------

@dataclass
class ProductInfo:
    """产品基本信息，作为Listing生成的核心输入。"""

    asin: str = ""
    product_name: str = ""
    category: str = ""
    features: List[str] = field(default_factory=list)
    price: float = 0.0
    brand: str = ""
    target_market: str = "US"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asin": self.asin,
            "product_name": self.product_name,
            "category": self.category,
            "features": self.features,
            "price": self.price,
            "brand": self.brand,
            "target_market": self.target_market,
        }


# ---------------------------------------------------------------------------
# LangGraph 状态定义
# ---------------------------------------------------------------------------

class ListingState(dict):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。

    键说明：
      asin             (str)  — 产品ASIN
      product_name     (str)  — 产品名称
      category         (str)  — 产品类目
      features         (list) — 产品特性
      persona_data     (dict) — 用户画像数据（来自persona_agent）
      competitor_data  (dict) — 竞品差异数据（来自competitor_agent）
      dry_run          (bool) — 是否dry run模式
      agent_run_id     (str)  — agent_runs表主键
      kb_tips          (list) — 知识库检索到的文案技巧
      generated_copy   (dict) — LLM生成的原始文案
      listing_copy     (dict) — 最终文案（经合规检查后）
      compliance_result (dict) — 合规检查结果
      error            (str)  — 错误信息（若有）
      status           (str)  — 当前状态 running/completed/failed
    """

    def __init__(
        self,
        asin: str = "",
        product_name: str = "",
        category: str = "",
        features: List[str] = None,
        persona_data: Dict[str, Any] = None,
        competitor_data: Dict[str, Any] = None,
        dry_run: bool = True,
        **kwargs,
    ):
        super().__init__(
            asin=asin,
            product_name=product_name,
            category=category,
            features=features or [],
            persona_data=persona_data or {},
            competitor_data=competitor_data or {},
            dry_run=dry_run,
            agent_run_id=None,
            kb_tips=[],
            generated_copy={},
            listing_copy={},
            compliance_result={},
            error=None,
            status="running",
            **kwargs,
        )

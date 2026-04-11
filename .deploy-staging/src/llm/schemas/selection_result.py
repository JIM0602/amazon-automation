"""选品结果 Schema。

定义 selection_agent 的 LLM 输出结构。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from src.llm.schemas.base import BaseOutputSchema


class MarketDataSchema(BaseOutputSchema):
    """产品市场数据。"""

    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="产品评分 (0-5)")
    review_count: int = Field(default=0, ge=0, description="评论数量")
    price: float = Field(default=0.0, ge=0.0, description="定价 (USD)")
    bsr_rank: int = Field(default=99999, ge=0, description="BSR 排名")
    monthly_sales: int = Field(default=0, ge=0, description="月销量 (件)")
    category: Optional[str] = Field(default=None, description="产品类目")


class ProductCandidateSchema(BaseOutputSchema):
    """单个候选产品 Schema。"""

    asin: str = Field(..., description="亚马逊 ASIN 编号", min_length=1)
    product_name: str = Field(..., description="产品名称", min_length=1)
    reason: str = Field(..., description="选品理由（应引用知识库原则）", min_length=1)
    market_data: MarketDataSchema = Field(
        default_factory=MarketDataSchema, description="市场数据"
    )
    risks: List[str] = Field(default_factory=list, description="风险提示列表")
    score: float = Field(default=0.0, ge=0.0, le=10.0, description="综合评分 (0-10)")
    kb_references: List[str] = Field(
        default_factory=list, description="引用的知识库原则列表"
    )

    @field_validator("asin")
    @classmethod
    def validate_asin(cls, v: str) -> str:
        """ASIN 格式校验（简单检查：字母+数字，10位）。"""
        v = v.strip().upper()
        if not v:
            raise ValueError("ASIN 不能为空")
        return v

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """评分精度限制到小数点后1位。"""
        return round(v, 1)


class SelectionResultSchema(BaseOutputSchema):
    """选品分析结果 Schema（selection_agent 主输出）。

    对应 generate_report 节点输出的 report 字段。
    """

    category: str = Field(..., description="分析类目", min_length=1)
    analysis_date: str = Field(..., description="分析日期 (YYYY-MM-DD)")
    candidates: List[ProductCandidateSchema] = Field(
        default_factory=list,
        description="候选产品列表",
    )
    kb_principles_used: List[str] = Field(
        default_factory=list, description="使用的知识库原则"
    )
    agent_run_id: Optional[str] = Field(default=None, description="Agent 运行 ID")

    @field_validator("candidates")
    @classmethod
    def validate_candidates(cls, v: List[ProductCandidateSchema]) -> List[ProductCandidateSchema]:
        """候选产品列表至少需要1个。"""
        if len(v) == 0:
            raise ValueError("候选产品列表不能为空，至少需要1个候选产品")
        return v

    @model_validator(mode="after")
    def validate_candidates_not_empty(self) -> "SelectionResultSchema":
        """在所有字段解析后再次验证候选产品非空（含默认值情况）。"""
        if len(self.candidates) == 0:
            raise ValueError("候选产品列表不能为空，至少需要1个候选产品")
        return self

    @field_validator("analysis_date")
    @classmethod
    def validate_analysis_date(cls, v: str) -> str:
        """日期格式校验。"""
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"analysis_date 格式错误，应为 YYYY-MM-DD，实际为: {v!r}")
        return v

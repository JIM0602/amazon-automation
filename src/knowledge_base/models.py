"""
知识库 Pydantic 元数据模型。

DOC_TYPE 枚举限定文档类型，DocumentMetadata 描述文档级别属性，
ChunkMetadata 在文档元数据基础上额外携带分块相关属性。
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# 文档类型枚举
# ---------------------------------------------------------------------------

DOC_TYPE = Literal[
    "tutorial",    # 教程 / 操作手册
    "case_study",  # 案例研究
    "rule",        # 规则 / 政策
    "guide",       # 指南 / 最佳实践
    "faq",         # 常见问题
    "report",      # 报告 / 分析
    "other",       # 其他
]

DOC_TYPE_VALUES: tuple[str, ...] = (
    "tutorial",
    "case_study",
    "rule",
    "guide",
    "faq",
    "report",
    "other",
)

# 分块策略枚举（保留扩展性）
CHUNK_STRATEGY = Literal[
    "paragraph",   # 按段落切分（默认）
    "heading",     # 按标题切分
    "fixed",       # 固定窗口切分
]


# ---------------------------------------------------------------------------
# 文档级元数据
# ---------------------------------------------------------------------------

class DocumentMetadata(BaseModel):
    """文档级元数据，包含来源、分类、类型和有效期等信息。"""

    source: str = Field(..., description="文档来源路径或 URL")
    title: str = Field(..., description="文档标题")
    category: str = Field(..., description="知识库分类（如'广告策略'）")
    doc_type: DOC_TYPE = Field(default="other", description="文档类型")
    version: Optional[str] = Field(default=None, description="文档版本号，如 '1.2'")
    effective_date: Optional[date] = Field(default=None, description="文档生效日期")
    expires_date: Optional[date] = Field(default=None, description="文档过期日期")
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="优先级 1-10，10 最高，影响检索排序权重",
    )

    model_config = ConfigDict()


# ---------------------------------------------------------------------------
# 分块级元数据（继承文档元数据，追加分块属性）
# ---------------------------------------------------------------------------

class ChunkMetadata(DocumentMetadata):
    """分块级元数据，在文档元数据基础上附加分块索引和分块策略。"""

    chunk_index: int = Field(default=0, ge=0, description="分块在文档中的顺序索引")
    chunk_strategy: CHUNK_STRATEGY = Field(
        default="paragraph", description="使用的分块策略"
    )

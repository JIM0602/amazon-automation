"""Listing文案生成Agent — 亚马逊智能化运营系统 Phase 2。

功能：
    - 生成标题（Title）— 200字符内
    - 生成五点描述（Bullet Points）— 5条
    - 生成后台关键词（Search Terms）— 250字符内
    - 生成A+文案建议（可选）
    - 合规词检查（禁用词、敏感词、字符长度）

输入：
    - 产品信息（ASIN / 产品名称 / 类目 / 特性）
    - 用户画像（来自 persona_agent T28 输出）
    - 竞品差异分析（来自 competitor_agent T27 输出）

输出：符合 ListingCopy Schema 的结构化文案
"""
from src.agents.listing_agent.agent import execute

def run(
    asin: str = "",
    product_name: str = "",
    category: str = "",
    features: list = None,
    persona_data: dict = None,
    competitor_data: dict = None,
    dry_run: bool = True,
) -> dict:
    """执行 Listing 文案生成 Agent 工作流。

    Args:
        asin:            产品 ASIN（如 B0XXX）
        product_name:    产品名称
        category:        产品类目
        features:        产品特性列表
        persona_data:    用户画像数据（来自 persona_agent）
        competitor_data: 竞品差异数据（来自 competitor_agent）
        dry_run:         True = 不调用真实外部 API

    Returns:
        {
            "asin": str,
            "title": str,
            "bullet_points": list[str],
            "search_terms": str,
            "aplus_copy": str | None,
            "compliance_passed": bool,
            "compliance_issues": list[str],
            "status": "completed" | "failed",
            "error": str | None,
        }
    """
    return execute(
        asin=asin,
        product_name=product_name,
        category=category,
        features=features or [],
        persona_data=persona_data or {},
        competitor_data=competitor_data or {},
        dry_run=dry_run,
    )

__all__ = ["run", "execute"]

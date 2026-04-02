"""Listing文案生成核心逻辑 — 调用LLM生成并后处理文案。

功能：
  - generate_full_listing: 一次性生成完整Listing文案
  - parse_llm_response:    解析LLM返回的JSON
  - _build_persona_summary: 构建用户画像摘要
  - _build_competitor_summary: 构建竞品差异摘要
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 可选依赖（与 selection_agent 保持一致的导入模式）
# ---------------------------------------------------------------------------
try:
    from src.llm.client import chat
    _LLM_AVAILABLE = True
except ImportError:
    chat = None  # type: ignore[assignment]
    _LLM_AVAILABLE = False

from src.agents.listing_agent.prompts import (
    LISTING_SYSTEM_PROMPT,
    FULL_LISTING_TEMPLATE,
)
from src.agents.listing_agent.compliance import run_compliance_check, sanitize_text


# ---------------------------------------------------------------------------
# Mock 数据（dry_run=True 时使用）
# ---------------------------------------------------------------------------

_MOCK_LISTING_OUTPUT = {
    "title": "PUDIWIND Pet Water Fountain 2.5L - Automatic Circulating Dog Cat Drinking Fountain with Filter, Ultra-Quiet Pump, Flower Design",
    "bullet_points": [
        "ULTRA-QUIET OPERATION — Advanced submersible pump operates at under 30dB, ensuring peaceful environment for both pets and owners, perfect for use in bedroom or living room without disturbing sleep",
        "TRIPLE FILTRATION SYSTEM — Activated carbon + ion exchange resin + PP cotton filter removes hair, debris, and odors, providing fresh and clean water that encourages pets to drink more and stay hydrated",
        "2.5L LARGE CAPACITY — Spacious water reservoir reduces refilling frequency, suitable for multiple cats or dogs, ideal for busy pet owners who want worry-free hydration for their beloved companions",
        "EASY TO CLEAN DESIGN — Completely disassemblable components are dishwasher safe, saving time on maintenance while ensuring thorough cleaning to prevent bacteria buildup for your pet's health",
        "360° DRINKING ACCESS — Unique flower-shaped design allows pets to drink from any angle at their preferred height, reducing neck strain and encouraging natural drinking posture for better health",
    ],
    "search_terms": "pet fountain automatic cat water dispenser dog drinking fountain electric quiet pump filter replacement circulating fountain",
    "aplus_copy": "A+文案建议：以宠物健康为核心主题，展示三级过滤系统的工作原理图解；对比普通水碗与循环喷泉的健康优势；突出超静音泵的实测数据（<30dB）；添加客户实拍图和宠物使用场景图；设置常见问题FAQ模块解答换水频率和滤芯更换周期。",
}


# ---------------------------------------------------------------------------
# 核心生成函数
# ---------------------------------------------------------------------------

def generate_full_listing(
    asin: str,
    product_name: str,
    category: str,
    features: List[str],
    persona_data: Dict[str, Any],
    competitor_data: Dict[str, Any],
    kb_tips: List[str],
    dry_run: bool = True,
) -> Dict[str, Any]:
    """生成完整Listing文案（标题+五点描述+后台关键词+A+文案）。

    Args:
        asin:            产品ASIN
        product_name:    产品名称
        category:        产品类目
        features:        产品特性列表
        persona_data:    用户画像数据
        competitor_data: 竞品差异数据
        kb_tips:         知识库文案技巧
        dry_run:         True = 返回Mock数据

    Returns:
        {
            "title": str,
            "bullet_points": list[str],
            "search_terms": str,
            "aplus_copy": str | None,
            "raw_llm_output": str,
        }
    """
    if dry_run:
        logger.info("generator.generate_full_listing | dry_run=True, 返回Mock数据")
        return {**_MOCK_LISTING_OUTPUT, "raw_llm_output": json.dumps(_MOCK_LISTING_OUTPUT, ensure_ascii=False)}

    if not _LLM_AVAILABLE or chat is None:
        logger.warning("generator.generate_full_listing | LLM不可用，返回Mock数据")
        return {**_MOCK_LISTING_OUTPUT, "raw_llm_output": ""}

    # 构建Prompt输入
    features_text = "\n".join(f"- {f}" for f in features) if features else "（未提供）"
    persona_summary = _build_persona_summary(persona_data)
    competitor_advantages = _build_competitor_summary(competitor_data)
    kb_tips_text = "\n".join(f"- {tip}" for tip in kb_tips[:5]) if kb_tips else "（暂无知识库技巧）"

    user_msg = FULL_LISTING_TEMPLATE.format(
        asin=asin or "N/A",
        product_name=product_name or "未知产品",
        category=category or "General",
        features=features_text,
        brand=persona_data.get("brand", ""),
        price=competitor_data.get("avg_price", ""),
        target_market="US",
        persona_summary=persona_summary,
        competitor_advantages=competitor_advantages,
        kb_tips=kb_tips_text,
    )

    raw_output = ""
    try:
        result = chat(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LISTING_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=2000,
        )
        raw_output = result.get("content", "")
        logger.info(
            "generator.generate_full_listing | tokens_used=%d",
            result.get("input_tokens", 0) + result.get("output_tokens", 0),
        )
    except Exception as exc:
        logger.error("generator.generate_full_listing | LLM调用失败: %s", exc)
        return {**_MOCK_LISTING_OUTPUT, "raw_llm_output": ""}

    # 解析LLM输出
    parsed = parse_llm_response(raw_output)
    parsed["raw_llm_output"] = raw_output
    return parsed


def parse_llm_response(raw_output: str) -> Dict[str, Any]:
    """解析LLM返回的JSON文案输出。

    支持两种格式：
    1. 纯JSON字符串
    2. Markdown代码块中的JSON（```json ... ```）

    Args:
        raw_output: LLM原始输出文本

    Returns:
        {
            "title": str,
            "bullet_points": list[str],
            "search_terms": str,
            "aplus_copy": str | None,
        }
    """
    if not raw_output:
        logger.warning("parse_llm_response | 输入为空，返回Mock数据")
        return dict(_MOCK_LISTING_OUTPUT)

    # 尝试提取代码块中的JSON
    json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', raw_output)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 直接尝试解析整个输出
        json_str = raw_output.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # 最后尝试找到第一个 { 到最后一个 }
        try:
            start = raw_output.index('{')
            end = raw_output.rindex('}') + 1
            data = json.loads(raw_output[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("parse_llm_response | JSON解析失败: %s，使用Mock数据", exc)
            return dict(_MOCK_LISTING_OUTPUT)

    # 提取并清理各字段
    title = sanitize_text(data.get("title", ""))
    bullet_points_raw = data.get("bullet_points", [])
    search_terms = sanitize_text(data.get("search_terms", ""))
    aplus_copy = data.get("aplus_copy")

    # 处理 bullet_points
    if isinstance(bullet_points_raw, list):
        bullet_points = [sanitize_text(bp) for bp in bullet_points_raw if bp]
    else:
        bullet_points = []

    # 确保5条 bullet points
    if len(bullet_points) < 5:
        while len(bullet_points) < 5:
            idx = len(bullet_points) + 1
            bullet_points.append(f"FEATURE {idx} — Additional product feature and benefit")
    elif len(bullet_points) > 5:
        bullet_points = bullet_points[:5]

    # 确保标题不为空
    if not title:
        title = f"{data.get('product_name', 'Product')} - High Quality"

    # 截断超长文本
    if len(title) > 200:
        title = title[:197] + "..."
    if len(search_terms) > 250:
        search_terms = search_terms[:250]

    return {
        "title": title,
        "bullet_points": bullet_points,
        "search_terms": search_terms,
        "aplus_copy": aplus_copy,
    }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _build_persona_summary(persona_data: Dict[str, Any]) -> str:
    """从用户画像数据构建摘要文本。

    Args:
        persona_data: 用户画像数据字典（来自 persona_agent）

    Returns:
        格式化的用户画像摘要文本
    """
    if not persona_data:
        return "（未提供用户画像数据，使用通用文案策略）"

    lines = []

    # 目标用户群体
    target_users = persona_data.get("target_users", persona_data.get("personas", []))
    if target_users:
        if isinstance(target_users, list):
            lines.append(f"目标用户群体: {', '.join(str(u) for u in target_users[:3])}")
        else:
            lines.append(f"目标用户群体: {target_users}")

    # 核心痛点
    pain_points = persona_data.get("pain_points", [])
    if pain_points:
        if isinstance(pain_points, list):
            lines.append(f"核心痛点: {'; '.join(str(p) for p in pain_points[:3])}")
        else:
            lines.append(f"核心痛点: {pain_points}")

    # 购买动机
    motivations = persona_data.get("purchase_motivations", persona_data.get("motivations", []))
    if motivations:
        if isinstance(motivations, list):
            lines.append(f"购买动机: {'; '.join(str(m) for m in motivations[:3])}")
        else:
            lines.append(f"购买动机: {motivations}")

    # 关键词偏好
    keywords = persona_data.get("preferred_keywords", persona_data.get("keywords", []))
    if keywords:
        if isinstance(keywords, list):
            lines.append(f"用户常用搜索词: {', '.join(str(k) for k in keywords[:5])}")
        else:
            lines.append(f"用户常用搜索词: {keywords}")

    return "\n".join(lines) if lines else "（用户画像数据结构未识别，使用通用文案策略）"


def _build_competitor_summary(competitor_data: Dict[str, Any]) -> str:
    """从竞品差异数据构建摘要文本。

    Args:
        competitor_data: 竞品分析数据字典（来自 competitor_agent）

    Returns:
        格式化的竞品差异摘要文本
    """
    if not competitor_data:
        return "（未提供竞品分析数据，使用通用差异化策略）"

    lines = []

    # 竞品弱点/用户投诉
    weaknesses = competitor_data.get("competitor_weaknesses", competitor_data.get("weaknesses", []))
    if weaknesses:
        if isinstance(weaknesses, list):
            lines.append(f"竞品弱点（我们的机会）: {'; '.join(str(w) for w in weaknesses[:3])}")
        else:
            lines.append(f"竞品弱点: {weaknesses}")

    # 我们的差异化优势
    advantages = competitor_data.get("our_advantages", competitor_data.get("advantages", []))
    if advantages:
        if isinstance(advantages, list):
            lines.append(f"我们的差异化优势: {'; '.join(str(a) for a in advantages[:3])}")
        else:
            lines.append(f"我们的差异化优势: {advantages}")

    # 竞品主要卖点（供参考）
    competitor_strengths = competitor_data.get("competitor_strengths", [])
    if competitor_strengths:
        if isinstance(competitor_strengths, list):
            lines.append(f"竞品主要卖点（参考）: {', '.join(str(s) for s in competitor_strengths[:2])}")

    # 定价策略
    avg_price = competitor_data.get("avg_price", "")
    if avg_price:
        lines.append(f"竞品平均价格: ${avg_price}")

    return "\n".join(lines) if lines else "（竞品数据结构未识别，强调产品核心卖点）"

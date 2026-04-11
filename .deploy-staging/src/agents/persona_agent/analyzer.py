"""用户画像Agent分析工具函数。

提供：
  - analyze_reviews_for_persona  — 从评论数据中提取用户特征
  - extract_pain_points          — 从评论文本中提取高频痛点
  - extract_motivations          — 提取购买动机
  - extract_trigger_words        — 提取购买触发词
  - build_user_persona           — 构建完整用户画像
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 关键词库（用于规则匹配）
# ---------------------------------------------------------------------------

_PAIN_POINT_KEYWORDS = {
    "噪音": ["noise", "noisy", "loud", "sound", "pump noise", "makes noise"],
    "清洁困难": ["hard to clean", "difficult to clean", "clean", "cleaning", "wash"],
    "滤芯成本": ["filter", "replacement filter", "expensive filter", "filter cost"],
    "耐用性差": ["broke", "broken", "cracked", "stopped working", "failed", "cheap"],
    "漏水": ["leaking", "leak", "water leak", "spill"],
    "安装复杂": ["assemble", "assembly", "confusing", "instructions", "setup"],
    "材质问题": ["plastic", "cheap plastic", "quality", "material", "smell"],
    "容量不足": ["small", "capacity", "not enough water", "too small"],
    "电机故障": ["motor", "pump", "stopped", "not working", "malfunction"],
}

_MOTIVATION_KEYWORDS = {
    "宠物健康": ["health", "healthy", "drink more", "hydration", "fresh water", "clean water"],
    "便利省时": ["easy", "convenient", "time-saving", "automatic", "simple"],
    "静音体验": ["quiet", "silent", "sleep", "night"],
    "安全材质": ["safe", "bpa-free", "non-toxic", "food grade", "stainless"],
    "美观设计": ["cute", "design", "beautiful", "look", "style"],
    "大容量": ["large", "capacity", "multiple cats", "multiple pets", "big"],
    "过滤功能": ["filter", "filtered", "clean", "fresh"],
    "性价比高": ["value", "affordable", "price", "cheap", "worth"],
}

_TRIGGER_WORD_CANDIDATES = [
    "BPA-free", "静音", "quiet", "easy clean", "filter", "stainless steel",
    "自动循环", "大容量", "宠物健康", "fresh water", "便捷", "安全",
    "耐用", "durable", "食品级", "food-grade", "多宠家庭", "省电",
    "一键清洗", "智能提醒", "360°过滤", "活性炭", "防溅",
]

_PERSONA_TAG_MAPPING = {
    "pet": "养宠人士",
    "cat": "猫奴",
    "dog": "狗主人",
    "clean": "爱干净",
    "quiet": "注重品质",
    "health": "重视健康",
    "quality": "重品质",
    "design": "颜值控",
    "budget": "价格敏感",
    "premium": "高端消费",
    "multiple": "多宠家庭",
}


# ---------------------------------------------------------------------------
# 核心分析函数
# ---------------------------------------------------------------------------

def analyze_reviews_for_persona(reviews: list, category: str = "") -> dict:
    """从评论数据中提取用户特征。

    Args:
        reviews: 评论数据列表，每条包含 text/rating/helpful_votes/verified
        category: 产品类目

    Returns:
        包含 demographics/pain_points/motivations/trigger_words/persona_tags 的字典
    """
    if not reviews:
        logger.warning("analyze_reviews_for_persona | 评论数据为空，返回默认画像")
        return {
            "demographics": {
                "age_range": "unknown",
                "gender": "unknown",
                "income_level": "unknown",
                "lifestyle": "unknown",
            },
            "pain_points": [],
            "motivations": [],
            "trigger_words": [],
            "persona_tags": [],
        }

    pain_points = extract_pain_points(reviews)
    motivations = extract_motivations(reviews)
    persona_tags = _extract_persona_tags(reviews, category)
    trigger_words = extract_trigger_words(reviews, persona_tags)
    demographics = _infer_demographics(reviews, category, persona_tags)

    logger.info(
        "analyze_reviews_for_persona | reviews=%d pain_points=%d motivations=%d",
        len(reviews),
        len(pain_points),
        len(motivations),
    )

    return {
        "demographics": demographics,
        "pain_points": pain_points,
        "motivations": motivations,
        "trigger_words": trigger_words,
        "persona_tags": persona_tags,
    }


def extract_pain_points(reviews: list) -> list:
    """从评论文本中提取高频痛点。

    Args:
        reviews: 评论数据列表

    Returns:
        痛点字符串列表
    """
    if not reviews:
        return []

    pain_point_counts: Dict[str, int] = {}

    for review in reviews:
        text = review.get("text", "").lower() if isinstance(review, dict) else str(review).lower()
        rating = review.get("rating", 5) if isinstance(review, dict) else 5

        # 低评分评论更可能包含痛点
        weight = 2 if rating <= 3 else 1

        for pain_category, keywords in _PAIN_POINT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    pain_point_counts[pain_category] = pain_point_counts.get(pain_category, 0) + weight
                    break  # 每个类别只计一次

    # 按频次排序，取前5个
    sorted_points = sorted(pain_point_counts.items(), key=lambda x: x[1], reverse=True)
    result = [pain for pain, _ in sorted_points[:5]]

    logger.debug("extract_pain_points | found %d pain points", len(result))
    return result


def extract_motivations(reviews: list) -> list:
    """提取购买动机。

    Args:
        reviews: 评论数据列表

    Returns:
        购买动机字符串列表
    """
    if not reviews:
        return []

    motivation_counts: Dict[str, int] = {}

    for review in reviews:
        text = review.get("text", "").lower() if isinstance(review, dict) else str(review).lower()
        rating = review.get("rating", 3) if isinstance(review, dict) else 3

        # 高评分评论更可能反映购买动机
        weight = 2 if rating >= 4 else 1

        for motivation, keywords in _MOTIVATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    motivation_counts[motivation] = motivation_counts.get(motivation, 0) + weight
                    break

    # 按频次排序，取前5个
    sorted_motivations = sorted(motivation_counts.items(), key=lambda x: x[1], reverse=True)
    result = [m for m, _ in sorted_motivations[:5]]

    logger.debug("extract_motivations | found %d motivations", len(result))
    return result


def extract_trigger_words(reviews: list, persona_tags: list) -> list:
    """提取购买触发词。

    Args:
        reviews: 评论数据列表
        persona_tags: 人群标签列表

    Returns:
        购买触发词字符串列表
    """
    trigger_word_counts: Dict[str, int] = {}

    # 从评论文本中匹配预定义触发词
    all_text = " ".join([
        review.get("text", "").lower() if isinstance(review, dict) else str(review).lower()
        for review in reviews
    ])

    for word in _TRIGGER_WORD_CANDIDATES:
        if word.lower() in all_text:
            trigger_word_counts[word] = all_text.count(word.lower())

    # 基于人群标签添加额外触发词
    tag_based_words = _get_tag_based_triggers(persona_tags)
    for word in tag_based_words:
        if word not in trigger_word_counts:
            trigger_word_counts[word] = 1

    # 按频次排序，取前10个
    sorted_words = sorted(trigger_word_counts.items(), key=lambda x: x[1], reverse=True)
    result = [w for w, _ in sorted_words[:10]]

    # 如果没有匹配到，返回默认触发词
    if not result:
        result = ["安全", "便捷", "耐用", "高品质"]

    logger.debug("extract_trigger_words | found %d trigger words", len(result))
    return result


def build_user_persona(
    category: str,
    asin: str,
    analysis: dict,
    data_sources: list,
) -> dict:
    """构建完整用户画像。

    Args:
        category:     产品类目
        asin:         来源ASIN（可选）
        analysis:     analyze_reviews_for_persona() 返回的分析结果
        data_sources: 数据来源列表

    Returns:
        UserPersona.to_dict() 结构的字典
    """
    from src.agents.persona_agent.schemas import UserPersona

    persona = UserPersona(
        category=category,
        asin=asin,
        demographics=analysis.get("demographics", {
            "age_range": "unknown",
            "gender": "unknown",
            "income_level": "unknown",
            "lifestyle": "unknown",
        }),
        pain_points=analysis.get("pain_points", []),
        motivations=analysis.get("motivations", []),
        trigger_words=analysis.get("trigger_words", []),
        persona_tags=analysis.get("persona_tags", []),
        data_sources=data_sources,
    )

    logger.info(
        "build_user_persona | category=%s pain_points=%d trigger_words=%d",
        category,
        len(analysis.get("pain_points", [])),
        len(analysis.get("trigger_words", [])),
    )

    return persona.to_dict()


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _extract_persona_tags(reviews: list, category: str) -> list:
    """从评论和类目中提取人群标签。"""
    tag_counts: Dict[str, int] = {}

    all_text = " ".join([
        review.get("text", "").lower() if isinstance(review, dict) else str(review).lower()
        for review in reviews
    ]).lower()

    # 类目关键词匹配
    category_lower = category.lower()

    for keyword, tag in _PERSONA_TAG_MAPPING.items():
        if keyword in all_text or keyword in category_lower:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # 默认标签
    if not tag_counts:
        tag_counts["消费者"] = 1

    return list(tag_counts.keys())[:6]  # 最多6个标签


def _infer_demographics(reviews: list, category: str, persona_tags: list) -> dict:
    """从评论和标签推断人口特征。"""
    all_text = " ".join([
        review.get("text", "").lower() if isinstance(review, dict) else str(review).lower()
        for review in reviews
    ])

    # 推断年龄段（基于关键词）
    age_range = "25-45"
    if "senior" in all_text or "elderly" in all_text or "老年" in all_text:
        age_range = "45-65"
    elif "young" in all_text or "student" in all_text:
        age_range = "18-30"

    # 推断性别倾向
    gender = "female-dominant"
    male_words = ["husband", "my dog", "he ", "his "]
    female_words = ["she ", "her ", "wife", "my cat"]
    male_count = sum(1 for w in male_words if w in all_text)
    female_count = sum(1 for w in female_words if w in all_text)
    if male_count > female_count:
        gender = "male-dominant"
    elif male_count == female_count:
        gender = "mixed"

    # 推断收入水平
    income_level = "middle"
    if "expensive" in all_text or "too pricey" in all_text:
        income_level = "lower-middle"
    elif "premium" in all_text or "worth the price" in all_text:
        income_level = "upper-middle"

    # 生活方式（基于类目和标签）
    lifestyle = "pet-focused"
    category_lower = category.lower()
    if "宠物" in category_lower or "pet" in category_lower:
        lifestyle = "pet-focused"
    elif "健身" in category_lower or "fitness" in category_lower:
        lifestyle = "fitness-oriented"
    elif "厨房" in category_lower or "kitchen" in category_lower:
        lifestyle = "home-focused"

    return {
        "age_range": age_range,
        "gender": gender,
        "income_level": income_level,
        "lifestyle": lifestyle,
    }


def _get_tag_based_triggers(persona_tags: list) -> list:
    """根据人群标签返回相关触发词。"""
    trigger_map = {
        "养宠人士": ["宠物友好", "安全无毒", "动物医生推荐"],
        "猫奴": ["猫咪专属", "静音设计", "多只猫适用"],
        "狗主人": ["犬用设计", "大容量", "抗菌材质"],
        "爱干净": ["易清洁", "防细菌", "食品级材质"],
        "重品质": ["高品质", "耐用材质", "品牌保障"],
        "重视健康": ["健康饮水", "过滤净化", "BPA-free"],
        "颜值控": ["时尚设计", "多色可选", "精致外观"],
        "价格敏感": ["性价比高", "实惠价格", "经济实用"],
    }

    result = []
    for tag in persona_tags:
        if tag in trigger_map:
            result.extend(trigger_map[tag])

    return list(dict.fromkeys(result))  # 去重保持顺序

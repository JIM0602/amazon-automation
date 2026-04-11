"""竞品调研Agent分析工具函数。

提供：
  - analyze_competitor_data         — 分析单个竞品数据
  - extract_strengths_weaknesses    — 提取优势劣势
  - calculate_competitive_position  — 计算竞争位置
  - build_competitor_analysis       — 构建完整竞品分析报告
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 竞品分析核心函数
# ---------------------------------------------------------------------------

def analyze_competitor_data(competitor_data: dict) -> dict:
    """分析单个竞品数据，返回分析结果。

    Args:
        competitor_data: 竞品原始数据，包含 asin/title/brand/price/bsr_rank/rating/review_count/bullet_points

    Returns:
        包含 strengths/weaknesses/opportunities/competitive_position 的分析结果字典
    """
    if not competitor_data:
        return {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "competitive_position": "unknown",
        }

    asin = competitor_data.get("asin", "")
    rating = float(competitor_data.get("rating", 0.0))
    review_count = int(competitor_data.get("review_count", 0))
    price = float(competitor_data.get("price", 0.0))
    bsr_rank = int(competitor_data.get("bsr_rank", 0))
    bullet_points = competitor_data.get("bullet_points", [])
    title = competitor_data.get("title", "")
    brand = competitor_data.get("brand", "")

    strengths, weaknesses = extract_strengths_weaknesses(competitor_data)

    # 生成机会列表（基于劣势）
    opportunities = _derive_opportunities(weaknesses, rating, review_count)

    # 计算市场均值（单独分析时使用产品自身数据作为基准）
    market_avg = {"avg_price": price, "avg_rating": rating, "avg_reviews": review_count}
    competitive_position = calculate_competitive_position(rating, review_count, price, market_avg)

    return {
        "asin": asin,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "competitive_position": competitive_position,
    }


def extract_strengths_weaknesses(profile_data: dict) -> Tuple[List[str], List[str]]:
    """从竞品数据中提取优劣势，返回(strengths, weaknesses)。

    Args:
        profile_data: 竞品数据字典

    Returns:
        (strengths, weaknesses) 元组，均为字符串列表
    """
    strengths = []
    weaknesses = []

    rating = float(profile_data.get("rating", 0.0))
    review_count = int(profile_data.get("review_count", 0))
    price = float(profile_data.get("price", 0.0))
    bsr_rank = int(profile_data.get("bsr_rank", 0))
    bullet_points = profile_data.get("bullet_points", [])
    brand = profile_data.get("brand", "")
    title = profile_data.get("title", "")

    # 基于评分判断
    if rating >= 4.5:
        strengths.append(f"高评分（{rating}/5.0），用户满意度极高")
    elif rating >= 4.0:
        strengths.append(f"良好评分（{rating}/5.0），用户认可度较高")
    elif rating < 3.5 and rating > 0:
        weaknesses.append(f"评分偏低（{rating}/5.0），存在较多用户抱怨")

    # 基于评论数判断
    if review_count >= 1000:
        strengths.append(f"评论数量充足（{review_count}条），市场验证充分")
    elif review_count >= 100:
        strengths.append(f"有一定评论积累（{review_count}条）")
    elif review_count < 50:
        weaknesses.append(f"评论数量不足（{review_count}条），市场认知度有限")

    # 基于BSR排名判断
    if 0 < bsr_rank <= 100:
        strengths.append(f"BSR排名极佳（#{bsr_rank}），销量领先")
    elif 0 < bsr_rank <= 500:
        strengths.append(f"BSR排名良好（#{bsr_rank}），稳定销售")
    elif bsr_rank > 1000:
        weaknesses.append(f"BSR排名靠后（#{bsr_rank}），市场份额有限")

    # 基于产品要点判断
    if len(bullet_points) >= 5:
        strengths.append("产品要点描述完整，内容丰富")
    elif len(bullet_points) < 3:
        weaknesses.append("产品要点不够完整，内容单薄")

    # 基于价格判断
    if price > 0:
        if price < 20:
            strengths.append(f"价格具有竞争力（${price:.2f}），门槛低")
        elif price > 50:
            weaknesses.append(f"价格较高（${price:.2f}），可能影响转化")

    # 如果没有识别出任何优劣势，给出默认值
    if not strengths:
        strengths.append("产品已上市销售，具备基本市场竞争力")
    if not weaknesses:
        weaknesses.append("暂无明显劣势，需关注用户评论详情")

    return strengths, weaknesses


def calculate_competitive_position(
    rating: float,
    review_count: int,
    price: float,
    market_avg: dict,
) -> str:
    """根据数据判断竞争位置。

    Args:
        rating:       产品评分（0-5）
        review_count: 评论数量
        price:        售价
        market_avg:   市场均值字典，包含 avg_price/avg_rating/avg_reviews

    Returns:
        "strong" / "moderate" / "weak" / "unknown"
    """
    if rating == 0 and review_count == 0 and price == 0:
        return "unknown"

    avg_rating = float(market_avg.get("avg_rating", 0.0))
    avg_reviews = float(market_avg.get("avg_reviews", 0.0))
    avg_price = float(market_avg.get("avg_price", 0.0))

    score = 0

    # 评分维度（权重最高）
    if rating >= 4.5:
        score += 3
    elif rating >= 4.0:
        score += 2
    elif rating >= 3.5:
        score += 1
    elif rating > 0:
        score -= 1

    # 评论数维度
    if avg_reviews > 0:
        if review_count >= avg_reviews * 2:
            score += 2
        elif review_count >= avg_reviews:
            score += 1
        elif review_count < avg_reviews * 0.5:
            score -= 1
    elif review_count >= 500:
        score += 2
    elif review_count >= 100:
        score += 1

    # 价格竞争力（价格低于均值加分）
    if avg_price > 0:
        if price <= avg_price * 0.8:
            score += 1
        elif price > avg_price * 1.2:
            score -= 1

    # 映射到竞争位置
    if score >= 4:
        return "strong"
    elif score >= 2:
        return "moderate"
    elif score >= 0:
        return "weak"
    else:
        return "weak"


def build_competitor_analysis(
    target_asin: str,
    competitor_profiles: list,
    dry_run: bool = True,
) -> dict:
    """构建完整竞品分析报告。

    Args:
        target_asin:          目标产品ASIN
        competitor_profiles:  竞品画像列表（dict 或 CompetitorProfile 对象）
        dry_run:              是否为dry run模式

    Returns:
        CompetitorAnalysis 结构的字典
    """
    if not competitor_profiles:
        return {
            "target_asin": target_asin,
            "competitor_profiles": [],
            "market_summary": "暂无竞品数据",
            "price_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
            "avg_rating": 0.0,
            "top_keywords": [],
            "differentiation_suggestions": [],
        }

    # 将对象转为字典
    profiles_as_dicts = []
    for p in competitor_profiles:
        if hasattr(p, "to_dict"):
            profiles_as_dicts.append(p.to_dict())
        elif isinstance(p, dict):
            profiles_as_dicts.append(p)
        else:
            profiles_as_dicts.append({})

    # 计算价格区间
    prices = [float(p.get("price", 0.0)) for p in profiles_as_dicts if p.get("price", 0.0) > 0]
    if prices:
        price_range = {
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "avg": round(sum(prices) / len(prices), 2),
        }
    else:
        price_range = {"min": 0.0, "max": 0.0, "avg": 0.0}

    # 计算平均评分
    ratings = [float(p.get("rating", 0.0)) for p in profiles_as_dicts if p.get("rating", 0.0) > 0]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    # 提取高频关键词（来自标题和bullet_points）
    top_keywords = _extract_top_keywords(profiles_as_dicts)

    # 生成差异化建议
    differentiation_suggestions = _generate_differentiation_suggestions(
        profiles_as_dicts, price_range, avg_rating
    )

    # 生成市场概要
    market_summary = _generate_market_summary(
        len(profiles_as_dicts), price_range, avg_rating, profiles_as_dicts
    )

    return {
        "target_asin": target_asin,
        "competitor_profiles": profiles_as_dicts,
        "market_summary": market_summary,
        "price_range": price_range,
        "avg_rating": avg_rating,
        "top_keywords": top_keywords,
        "differentiation_suggestions": differentiation_suggestions,
    }


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _derive_opportunities(weaknesses: List[str], rating: float, review_count: int) -> List[str]:
    """根据劣势生成机会列表。"""
    opportunities = []

    if rating < 4.0 and rating > 0:
        opportunities.append("竞品评分不高，有机会通过更优质的产品质量和用户体验超越")

    if review_count < 200:
        opportunities.append("竞品评论积累不足，新品有机会通过精准运营快速追赶")

    for weakness in weaknesses:
        if "价格" in weakness or "price" in weakness.lower():
            opportunities.append("价格敏感市场，可提供更具性价比的选项")
        if "评分" in weakness or "rating" in weakness.lower():
            opportunities.append("通过优化产品设计解决用户痛点，建立更高评分优势")

    if not opportunities:
        opportunities.append("持续关注用户反馈，寻找产品改进和差异化机会")

    return list(dict.fromkeys(opportunities))  # 去重保持顺序


def _extract_top_keywords(profiles: List[dict]) -> List[str]:
    """从竞品标题和bullet_points提取高频关键词。"""
    # 收集所有文本内容
    all_words: Dict[str, int] = {}
    stop_words = {
        "the", "a", "an", "and", "or", "for", "with", "in", "of", "to",
        "is", "are", "be", "at", "by", "from", "on", "this", "that",
        "-", "&", "+", "/", "1", "2", "3",
    }

    for profile in profiles:
        title = profile.get("title", "")
        bullets = profile.get("bullet_points", [])

        words = title.lower().split()
        for bp in bullets:
            words.extend(bp.lower().split())

        for word in words:
            # 清理标点
            clean_word = word.strip(".,!?()[]{}\"'")
            if len(clean_word) >= 4 and clean_word not in stop_words:
                all_words[clean_word] = all_words.get(clean_word, 0) + 1

    # 按频次排序，取前10个
    sorted_words = sorted(all_words.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:10]]


def _generate_differentiation_suggestions(
    profiles: List[dict],
    price_range: dict,
    avg_rating: float,
) -> List[str]:
    """生成差异化建议列表。"""
    suggestions = []

    avg_price = price_range.get("avg", 0.0)
    min_price = price_range.get("min", 0.0)
    max_price = price_range.get("max", 0.0)

    # 价格策略建议
    if avg_price > 0:
        mid_price = (min_price + avg_price) / 2
        suggestions.append(
            f"价格策略：市场均价 ${avg_price:.2f}，建议定价 ${mid_price:.2f}-${avg_price:.2f} 区间，兼顾利润与竞争力"
        )

    # 评分建议
    if avg_rating < 4.3:
        suggestions.append(
            f"品质突破：竞品平均评分 {avg_rating:.1f}，通过提升产品质量和售后服务，目标评分达到 4.5+"
        )
    else:
        suggestions.append(
            f"维持高分：竞品平均评分已达 {avg_rating:.1f}，需要在功能创新上寻找差异化"
        )

    # 通用建议
    suggestions.extend([
        "内容差异化：优化Listing文案，突出竞品普遍未覆盖的使用场景",
        "功能创新：针对用户评论中的高频痛点，开发改进版本",
        "视觉优化：高质量产品图片和视频内容，提升点击率和转化率",
        "关键词布局：分析竞品排名关键词，寻找低竞争高转化的长尾词机会",
    ])

    return suggestions[:8]


def _generate_market_summary(
    competitor_count: int,
    price_range: dict,
    avg_rating: float,
    profiles: List[dict],
) -> str:
    """生成市场竞争概要文字。"""
    min_price = price_range.get("min", 0.0)
    max_price = price_range.get("max", 0.0)
    avg_price = price_range.get("avg", 0.0)

    # 找出评分最高的竞品
    if profiles:
        top = max(profiles, key=lambda p: (p.get("rating", 0), p.get("review_count", 0)))
        top_info = f"，市场领先者为 {top.get('asin', '')}（评分{top.get('rating', 0)}/5.0，{top.get('review_count', 0)}条评论）"
    else:
        top_info = ""

    # 判断竞争激烈程度
    if competitor_count >= 5 or (avg_rating >= 4.0 and sum(p.get("review_count", 0) for p in profiles) >= 5000):
        competition_level = "竞争较为激烈"
    elif competitor_count >= 3:
        competition_level = "竞争中等"
    else:
        competition_level = "竞争相对温和"

    summary = (
        f"当前市场共分析 {competitor_count} 款竞品，{competition_level}。"
        f"价格区间 ${min_price:.2f}-${max_price:.2f}（均价 ${avg_price:.2f}），"
        f"竞品平均评分 {avg_rating:.1f}/5.0{top_info}。"
        f"市场存在一定差异化空间，建议聚焦用户评论痛点制定产品优化策略。"
    )
    return summary

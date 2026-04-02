"""合规词检查模块 — 过滤亚马逊禁用词和敏感词，验证字符长度。

亚马逊Listing合规要求：
  - 标题：不超过200字符
  - 五点描述：每条不超过500字符
  - 后台关键词：不超过250字符（总计）
  - 禁用词：best, #1, guarantee, 等（亚马逊政策禁止主观声明）
  - 敏感词：价格比较、竞品名称等
"""
from __future__ import annotations

import re
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 亚马逊禁用词列表（来自亚马逊政策）
# ---------------------------------------------------------------------------
PROHIBITED_WORDS = [
    # 主观/夸大性词汇
    "best",
    "best seller",
    "bestseller",
    "#1",
    "number one",
    "number 1",
    "top seller",
    "top rated",
    "most popular",
    "cheapest",
    "lowest price",
    "best price",
    "best value",
    "best deal",
    # 保证类词汇
    "guarantee",
    "guaranteed",
    "lifetime guarantee",
    "money back guarantee",
    "warranty",  # 注意：warranty本身可用，但"lifetime warranty"受限
    "100% satisfaction",
    # 医疗/健康声明
    "cure",
    "treat",
    "diagnose",
    "prevent",
    "heal",
    # Amazon专有词
    "amazon's choice",
    "amazon choice",
    "prime",  # 在标题中不可单独使用
    # 其他违规词
    "free shipping",
    "sale",
    "discount",
    "hot deal",
]

# ---------------------------------------------------------------------------
# 敏感词/需要谨慎使用的词
# ---------------------------------------------------------------------------
SENSITIVE_WORDS = [
    "exclusive",
    "authentic",
    "original",
    "genuine",
    "official",
    "luxury",
    "premium",  # 可用但需谨慎
    "professional",  # 可用但需谨慎
]

# ---------------------------------------------------------------------------
# 字符长度限制
# ---------------------------------------------------------------------------
TITLE_MAX_CHARS = 200
BULLET_POINT_MAX_CHARS = 500
SEARCH_TERMS_MAX_CHARS = 250
APLUS_MAX_CHARS = 2000


def check_prohibited_words(text: str) -> List[str]:
    """检查文本中的禁用词，返回找到的禁用词列表。

    Args:
        text: 待检查的文本

    Returns:
        找到的禁用词列表（小写）
    """
    if not text:
        return []

    text_lower = text.lower()
    found = []

    for word in PROHIBITED_WORDS:
        # 使用词边界匹配，避免误判（如 "best" 不应匹配 "bestiary"）
        # 对于特殊符号开头的词（如 #1），使用不同的匹配策略
        escaped = re.escape(word.lower())
        if word.startswith('#'):
            # 特殊符号开头：确保 #1 在词边界内（前后不是字母数字）
            pattern = r'(?<!\w)' + escaped + r'(?!\w)'
        else:
            pattern = r'\b' + escaped + r'\b'
        if re.search(pattern, text_lower):
            found.append(word)

    return found


def check_sensitive_words(text: str) -> List[str]:
    """检查文本中的敏感词，返回找到的敏感词列表。

    Args:
        text: 待检查的文本

    Returns:
        找到的敏感词列表
    """
    if not text:
        return []

    text_lower = text.lower()
    found = []

    for word in SENSITIVE_WORDS:
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(word)

    return found


def check_length(text: str, max_chars: int, field_name: str) -> List[str]:
    """检查文本长度是否超过限制。

    Args:
        text:       待检查文本
        max_chars:  最大字符数
        field_name: 字段名称（用于错误信息）

    Returns:
        违规信息列表（空表示通过）
    """
    if not text:
        return []

    char_count = len(text)
    if char_count > max_chars:
        return [f"{field_name}超出字符限制：{char_count}/{max_chars}字符"]

    return []


def run_compliance_check(
    title: str,
    bullet_points: List[str],
    search_terms: str,
    aplus_copy: str = "",
) -> Dict[str, Any]:
    """对完整Listing文案执行合规检查。

    Args:
        title:         标题文本
        bullet_points: 五点描述列表
        search_terms:  后台关键词
        aplus_copy:    A+文案（可选）

    Returns:
        {
            "passed": bool,
            "issues": list[str],          # 所有违规问题
            "prohibited_found": list[str], # 发现的禁用词
            "sensitive_found": list[str],  # 发现的敏感词
            "length_issues": list[str],    # 字符长度问题
        }
    """
    issues = []
    prohibited_found = []
    sensitive_found = []
    length_issues = []

    # --- 检查标题 ---
    if title:
        # 长度检查
        length_issues.extend(check_length(title, TITLE_MAX_CHARS, "标题"))

        # 禁用词检查
        found = check_prohibited_words(title)
        if found:
            prohibited_found.extend(found)
            issues.append(f"标题包含禁用词: {', '.join(found)}")

        # 敏感词检查
        sens = check_sensitive_words(title)
        if sens:
            sensitive_found.extend(sens)
            issues.append(f"标题包含敏感词（建议检查）: {', '.join(sens)}")

    # --- 检查五点描述 ---
    for i, bp in enumerate(bullet_points, 1):
        if not bp:
            continue

        # 长度检查
        length_issues.extend(check_length(bp, BULLET_POINT_MAX_CHARS, f"第{i}条Bullet Point"))

        # 禁用词检查
        found = check_prohibited_words(bp)
        if found:
            prohibited_found.extend(found)
            issues.append(f"第{i}条Bullet Point包含禁用词: {', '.join(found)}")

        # 敏感词检查
        sens = check_sensitive_words(bp)
        if sens:
            sensitive_found.extend(sens)

    # --- 检查后台关键词 ---
    if search_terms:
        length_issues.extend(check_length(search_terms, SEARCH_TERMS_MAX_CHARS, "后台关键词"))

        # 后台关键词不能包含ASIN、品牌名等（简化检查：禁用词）
        found = check_prohibited_words(search_terms)
        if found:
            prohibited_found.extend(found)
            issues.append(f"后台关键词包含禁用词: {', '.join(found)}")

    # --- 检查A+文案 ---
    if aplus_copy:
        length_issues.extend(check_length(aplus_copy, APLUS_MAX_CHARS, "A+文案"))
        found = check_prohibited_words(aplus_copy)
        if found:
            prohibited_found.extend(found)
            issues.append(f"A+文案包含禁用词: {', '.join(found)}")

    # 汇总长度问题
    issues.extend(length_issues)

    # 去重
    prohibited_found = list(set(prohibited_found))
    sensitive_found = list(set(sensitive_found))

    passed = len(issues) == 0

    logger.info(
        "compliance_check | passed=%s issue_count=%d prohibited=%s",
        passed,
        len(issues),
        prohibited_found,
    )

    return {
        "passed": passed,
        "issues": issues,
        "prohibited_found": prohibited_found,
        "sensitive_found": sensitive_found,
        "length_issues": length_issues,
    }


def sanitize_text(text: str) -> str:
    """对文本进行基础清理（去除多余空白、特殊字符）。

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    # 去除首尾空白
    text = text.strip()

    # 将多个空格合并为一个
    text = re.sub(r'\s+', ' ', text)

    # 去除特殊控制字符（保留换行）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text

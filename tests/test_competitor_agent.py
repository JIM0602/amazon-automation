"""竞品调研Agent单元测试。

覆盖范围（共≥50个测试）：
  1. schemas 测试（~12个）— CompetitorProfile/CompetitorAnalysis/CompetitorState
  2. analyzer 测试（~12个）— analyze_competitor_data/extract_strengths_weaknesses/
                             calculate_competitive_position/build_competitor_analysis
  3. nodes 测试（~16个）— 每个节点正常路径、错误传播、dry_run行为
  4. agent.execute 测试（~10个）— 完整流程、返回字段、错误处理
"""
from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================ #
#  Helpers
# ============================================================================ #

def _make_mock_db_session():
    """创建 mock db_session 上下文管理器。"""
    mock_session = MagicMock()

    @contextmanager
    def _mock_cm():
        yield mock_session

    return _mock_cm, mock_session


def _make_mock_db_with_agent_run():
    """创建 mock db_session，其中 session.get 返回 mock AgentRun。"""
    mock_session = MagicMock()
    mock_run = MagicMock()
    mock_session.get.return_value = mock_run

    @contextmanager
    def _mock_cm():
        yield mock_session

    return _mock_cm, mock_session, mock_run


def _sample_competitor_raw():
    """示例竞品原始数据。"""
    return {
        "asin": "B0TEST001",
        "title": "Premium Pet Water Fountain 3L",
        "brand": "PremiumBrand",
        "price": 39.99,
        "bsr_rank": 80,
        "rating": 4.6,
        "review_count": 2500,
        "bullet_points": [
            "3L Large Capacity",
            "Ultra Quiet Pump",
            "Triple Filtration",
            "Easy to Clean",
            "BPA Free",
        ],
    }


def _sample_weak_competitor_raw():
    """示例弱竞品原始数据。"""
    return {
        "asin": "B0TEST002",
        "title": "Basic Pet Fountain",
        "brand": "BasicBrand",
        "price": 12.99,
        "bsr_rank": 2500,
        "rating": 3.2,
        "review_count": 45,
        "bullet_points": ["Simple design"],
    }


# ============================================================================ #
#  1. schemas 测试
# ============================================================================ #

class TestCompetitorProfile:
    """CompetitorProfile Schema 测试。"""

    def test_create_with_defaults(self):
        """应能使用默认值创建 CompetitorProfile。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        p = CompetitorProfile()
        assert p.asin == ""
        assert p.brand == ""
        assert p.competitive_position == "unknown"

    def test_create_with_full_data(self):
        """应能使用完整数据创建 CompetitorProfile。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        p = CompetitorProfile(
            asin="B0TEST001",
            brand="TestBrand",
            title="Test Product",
            price=29.99,
            bsr_rank=100,
            rating=4.5,
            review_count=1000,
            bullet_points=["Feature 1", "Feature 2"],
            strengths=["High rating"],
            weaknesses=["Expensive"],
            opportunities=["Price reduction"],
            competitive_position="strong",
        )
        assert p.asin == "B0TEST001"
        assert p.price == 29.99
        assert p.rating == 4.5
        assert p.competitive_position == "strong"

    def test_rating_validator_valid_range(self):
        """评分在 0-5 范围内应通过验证。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        for rating in [0.0, 1.0, 2.5, 4.5, 5.0]:
            p = CompetitorProfile(rating=rating)
            assert p.rating == rating

    def test_rating_validator_too_high(self):
        """评分超过 5.0 应抛出 ValueError。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        with pytest.raises((ValueError, Exception)):
            CompetitorProfile(rating=5.1)

    def test_rating_validator_negative(self):
        """评分为负数应抛出 ValueError。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        with pytest.raises((ValueError, Exception)):
            CompetitorProfile(rating=-0.1)

    def test_competitive_position_validator_valid(self):
        """合法的 competitive_position 值应通过验证。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        for pos in ["strong", "moderate", "weak", "unknown"]:
            p = CompetitorProfile(competitive_position=pos)
            assert p.competitive_position == pos

    def test_competitive_position_validator_invalid(self):
        """非法的 competitive_position 值应抛出 ValueError。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        with pytest.raises((ValueError, Exception)):
            CompetitorProfile(competitive_position="excellent")

    def test_to_dict_returns_dict(self):
        """to_dict() 应返回字典。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        p = CompetitorProfile(asin="B0TEST001", rating=4.0)
        d = p.to_dict()
        assert isinstance(d, dict)
        assert d["asin"] == "B0TEST001"
        assert d["rating"] == 4.0

    def test_to_dict_contains_all_fields(self):
        """to_dict() 应包含所有字段。"""
        from src.agents.competitor_agent.schemas import CompetitorProfile
        p = CompetitorProfile()
        d = p.to_dict()
        expected_keys = {
            "asin", "brand", "title", "price", "bsr_rank", "rating",
            "review_count", "bullet_points", "strengths", "weaknesses",
            "opportunities", "competitive_position",
        }
        assert expected_keys.issubset(d.keys())


class TestCompetitorState:
    """CompetitorState 测试。"""

    def test_state_is_dict_subclass(self):
        """CompetitorState 应继承 dict。"""
        from src.agents.competitor_agent.schemas import CompetitorState
        s = CompetitorState()
        assert isinstance(s, dict)

    def test_state_default_values(self):
        """CompetitorState 默认值应正确初始化。"""
        from src.agents.competitor_agent.schemas import CompetitorState
        s = CompetitorState()
        assert s["target_asin"] == ""
        assert s["competitor_asins"] == []
        assert s["competitor_data"] == {}
        assert s["analysis_result"] == {}
        assert s["competitor_profile"] == {}
        assert s["dry_run"] is True
        assert s["agent_run_id"] is None
        assert s["error"] is None
        assert s["status"] == "running"

    def test_state_with_target_asin(self):
        """CompetitorState 应正确存储 target_asin。"""
        from src.agents.competitor_agent.schemas import CompetitorState
        s = CompetitorState(target_asin="B0MYPRODUCT")
        assert s["target_asin"] == "B0MYPRODUCT"

    def test_state_supports_dict_operations(self):
        """CompetitorState 应支持标准 dict 操作。"""
        from src.agents.competitor_agent.schemas import CompetitorState
        s = CompetitorState()
        s["error"] = "test error"
        assert s.get("error") == "test error"
        assert "error" in s


# ============================================================================ #
#  2. analyzer 测试
# ============================================================================ #

class TestAnalyzeCompetitorData:
    """analyze_competitor_data 函数测试。"""

    def test_analyze_empty_data(self):
        """空数据应返回默认分析结果。"""
        from src.agents.competitor_agent.analyzer import analyze_competitor_data
        result = analyze_competitor_data({})
        assert result["strengths"] == []
        assert result["weaknesses"] == []
        assert result["opportunities"] == []
        assert result["competitive_position"] == "unknown"

    def test_analyze_strong_competitor(self):
        """高评分高评论数竞品应被识别。"""
        from src.agents.competitor_agent.analyzer import analyze_competitor_data
        data = _sample_competitor_raw()
        result = analyze_competitor_data(data)
        assert isinstance(result["strengths"], list)
        assert len(result["strengths"]) > 0

    def test_analyze_weak_competitor(self):
        """低评分低评论数竞品应有劣势分析。"""
        from src.agents.competitor_agent.analyzer import analyze_competitor_data
        data = _sample_weak_competitor_raw()
        result = analyze_competitor_data(data)
        assert isinstance(result["weaknesses"], list)
        assert len(result["weaknesses"]) > 0

    def test_analyze_returns_required_keys(self):
        """分析结果应包含必需字段。"""
        from src.agents.competitor_agent.analyzer import analyze_competitor_data
        result = analyze_competitor_data(_sample_competitor_raw())
        assert "strengths" in result
        assert "weaknesses" in result
        assert "opportunities" in result
        assert "competitive_position" in result


class TestExtractStrengthsWeaknesses:
    """extract_strengths_weaknesses 函数测试。"""

    def test_high_rating_creates_strength(self):
        """高评分应产生优势。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        strengths, _ = extract_strengths_weaknesses({"rating": 4.8, "review_count": 100})
        assert any("4.8" in s or "高评分" in s or "极高" in s for s in strengths)

    def test_low_rating_creates_weakness(self):
        """低评分应产生劣势。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        _, weaknesses = extract_strengths_weaknesses({"rating": 3.1, "review_count": 50})
        assert len(weaknesses) > 0

    def test_high_review_count_creates_strength(self):
        """高评论数应产生优势。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        strengths, _ = extract_strengths_weaknesses({"rating": 4.0, "review_count": 2000})
        assert any("2000" in s or "充足" in s or "积累" in s for s in strengths)

    def test_low_review_count_creates_weakness(self):
        """低评论数应产生劣势。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        _, weaknesses = extract_strengths_weaknesses({"rating": 4.0, "review_count": 10})
        assert any("10" in w or "不足" in w for w in weaknesses)

    def test_returns_tuple(self):
        """应返回 (strengths, weaknesses) 元组。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        result = extract_strengths_weaknesses({"rating": 4.0})
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_empty_data_returns_defaults(self):
        """空数据应返回非空的默认优劣势。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        strengths, weaknesses = extract_strengths_weaknesses({})
        assert len(strengths) > 0 or len(weaknesses) > 0


class TestCalculateCompetitivePosition:
    """calculate_competitive_position 函数测试。"""

    def test_all_zero_returns_unknown(self):
        """全零数据应返回 unknown。"""
        from src.agents.competitor_agent.analyzer import calculate_competitive_position
        result = calculate_competitive_position(0, 0, 0, {})
        assert result == "unknown"

    def test_high_rating_high_reviews_is_strong(self):
        """高评分+高评论数应返回 strong 或 moderate。"""
        from src.agents.competitor_agent.analyzer import calculate_competitive_position
        result = calculate_competitive_position(
            4.8, 5000, 25.0, {"avg_rating": 4.0, "avg_reviews": 500, "avg_price": 30.0}
        )
        assert result in ("strong", "moderate")

    def test_low_rating_is_weak(self):
        """低评分应返回 weak。"""
        from src.agents.competitor_agent.analyzer import calculate_competitive_position
        result = calculate_competitive_position(
            2.5, 10, 100.0, {"avg_rating": 4.2, "avg_reviews": 1000, "avg_price": 30.0}
        )
        assert result == "weak"

    def test_valid_position_values(self):
        """返回值应为合法的竞争位置字符串。"""
        from src.agents.competitor_agent.analyzer import calculate_competitive_position
        valid_positions = {"strong", "moderate", "weak", "unknown"}
        result = calculate_competitive_position(4.0, 300, 25.0, {"avg_rating": 4.0, "avg_reviews": 300, "avg_price": 25.0})
        assert result in valid_positions

    def test_strong_competitor_beats_market(self):
        """明显高于市场均值应返回 strong。"""
        from src.agents.competitor_agent.analyzer import calculate_competitive_position
        result = calculate_competitive_position(
            5.0, 10000, 20.0, {"avg_rating": 3.5, "avg_reviews": 200, "avg_price": 35.0}
        )
        assert result == "strong"


class TestBuildCompetitorAnalysis:
    """build_competitor_analysis 函数测试。"""

    def test_empty_profiles_returns_default(self):
        """空竞品列表应返回默认分析结果。"""
        from src.agents.competitor_agent.analyzer import build_competitor_analysis
        result = build_competitor_analysis("B0TARGET", [])
        assert result["target_asin"] == "B0TARGET"
        assert result["competitor_profiles"] == []
        assert result["price_range"] == {"min": 0.0, "max": 0.0, "avg": 0.0}

    def test_calculates_price_range(self):
        """应正确计算价格区间。"""
        from src.agents.competitor_agent.analyzer import build_competitor_analysis
        profiles = [
            {"asin": "A1", "price": 10.0, "rating": 4.0, "review_count": 100, "bullet_points": []},
            {"asin": "A2", "price": 30.0, "rating": 4.0, "review_count": 200, "bullet_points": []},
            {"asin": "A3", "price": 20.0, "rating": 4.0, "review_count": 150, "bullet_points": []},
        ]
        result = build_competitor_analysis("B0TARGET", profiles)
        assert result["price_range"]["min"] == 10.0
        assert result["price_range"]["max"] == 30.0
        assert result["price_range"]["avg"] == 20.0

    def test_calculates_avg_rating(self):
        """应正确计算平均评分。"""
        from src.agents.competitor_agent.analyzer import build_competitor_analysis
        profiles = [
            {"asin": "A1", "price": 20.0, "rating": 4.0, "review_count": 100, "bullet_points": []},
            {"asin": "A2", "price": 25.0, "rating": 5.0, "review_count": 200, "bullet_points": []},
        ]
        result = build_competitor_analysis("B0TARGET", profiles)
        assert result["avg_rating"] == 4.5

    def test_returns_required_keys(self):
        """返回结果应包含所有必需字段。"""
        from src.agents.competitor_agent.analyzer import build_competitor_analysis
        result = build_competitor_analysis("B0TARGET", [])
        expected_keys = {
            "target_asin", "competitor_profiles", "market_summary",
            "price_range", "avg_rating", "top_keywords", "differentiation_suggestions"
        }
        assert expected_keys.issubset(result.keys())

    def test_generates_differentiation_suggestions(self):
        """应生成差异化建议。"""
        from src.agents.competitor_agent.analyzer import build_competitor_analysis
        profiles = [_sample_competitor_raw()]
        result = build_competitor_analysis("B0TARGET", profiles)
        assert isinstance(result["differentiation_suggestions"], list)
        assert len(result["differentiation_suggestions"]) > 0

    def test_extracts_top_keywords(self):
        """应从标题和bullet_points提取关键词。"""
        from src.agents.competitor_agent.analyzer import build_competitor_analysis
        profiles = [_sample_competitor_raw()]
        result = build_competitor_analysis("B0TARGET", profiles)
        assert isinstance(result["top_keywords"], list)


# ============================================================================ #
#  3. nodes 测试
# ============================================================================ #

class TestNodeInitRun:
    """init_run 节点测试。"""

    def test_init_run_valid_asin(self):
        """有效 target_asin 应创建 agent_run_id 并继续。"""
        from src.agents.competitor_agent.nodes import init_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0MYPRODUCT", dry_run=True)
        result = init_run(state)
        assert result.get("error") is None
        assert result.get("agent_run_id") is not None
        assert len(result["agent_run_id"]) > 0

    def test_init_run_empty_asin_sets_error(self):
        """空 target_asin 应设置 error 并返回 failed 状态。"""
        from src.agents.competitor_agent.nodes import init_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="", dry_run=True)
        result = init_run(state)
        assert result["error"] is not None
        assert result["status"] == "failed"

    def test_init_run_whitespace_asin_sets_error(self):
        """仅空白的 target_asin 应设置 error。"""
        from src.agents.competitor_agent.nodes import init_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="   ", dry_run=True)
        result = init_run(state)
        assert result["error"] is not None

    def test_init_run_agent_run_id_is_uuid(self):
        """agent_run_id 应是有效的 UUID 字符串。"""
        from src.agents.competitor_agent.nodes import init_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0VALID", dry_run=True)
        result = init_run(state)
        # 验证是有效UUID
        uuid.UUID(result["agent_run_id"])

    def test_init_run_skips_db_in_dry_run(self):
        """dry_run=True 时应跳过 DB 写入。"""
        from src.agents.competitor_agent.nodes import init_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0VALID", dry_run=True)
        with patch("src.agents.competitor_agent.nodes.db_session") as mock_db:
            result = init_run(state)
            mock_db.assert_not_called()


class TestNodeFetchAsinData:
    """fetch_asin_data 节点测试。"""

    def test_fetch_skips_on_error(self):
        """state 有 error 时应直接返回。"""
        from src.agents.competitor_agent.nodes import fetch_asin_data
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TEST", dry_run=True)
        state["error"] = "previous error"
        result = fetch_asin_data(state)
        assert result["error"] == "previous error"
        assert result.get("competitor_data") == {}

    def test_fetch_dry_run_uses_mock_data(self):
        """dry_run=True 时应使用 Mock 数据。"""
        from src.agents.competitor_agent.nodes import fetch_asin_data
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        result = fetch_asin_data(state)
        assert isinstance(result["competitor_data"], dict)
        assert len(result["competitor_data"]) > 0

    def test_fetch_dry_run_with_specific_asins(self):
        """dry_run=True 且指定竞品ASIN时，应从Mock中加载数据。"""
        from src.agents.competitor_agent.nodes import fetch_asin_data
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(
            target_asin="B0TARGET",
            competitor_asins=["B0COMPETITOR1"],
            dry_run=True,
        )
        result = fetch_asin_data(state)
        assert "B0COMPETITOR1" in result["competitor_data"]

    def test_fetch_dry_run_unknown_asin_uses_placeholder(self):
        """dry_run=True 且指定的竞品ASIN不在Mock中，应返回占位数据。"""
        from src.agents.competitor_agent.nodes import fetch_asin_data
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(
            target_asin="B0TARGET",
            competitor_asins=["B0UNKNOWN999"],
            dry_run=True,
        )
        result = fetch_asin_data(state)
        assert "B0UNKNOWN999" in result["competitor_data"]
        placeholder = result["competitor_data"]["B0UNKNOWN999"]
        assert placeholder["asin"] == "B0UNKNOWN999"


class TestNodeAnalyzeCompetitors:
    """analyze_competitors 节点测试。"""

    def test_analyze_skips_on_error(self):
        """state 有 error 时应直接返回。"""
        from src.agents.competitor_agent.nodes import analyze_competitors
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(dry_run=True)
        state["error"] = "previous error"
        result = analyze_competitors(state)
        assert result["error"] == "previous error"

    def test_analyze_no_data_sets_error(self):
        """无竞品数据时应设置 error。"""
        from src.agents.competitor_agent.nodes import analyze_competitors
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["competitor_data"] = {}
        result = analyze_competitors(state)
        assert result["error"] is not None

    def test_analyze_produces_analysis_result(self):
        """有竞品数据时应产生分析结果。"""
        from src.agents.competitor_agent.nodes import analyze_competitors
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["competitor_data"] = {"B0COMPETITOR1": _sample_competitor_raw()}
        result = analyze_competitors(state)
        assert result.get("error") is None
        assert "B0COMPETITOR1" in result["analysis_result"]

    def test_analyze_result_has_required_fields(self):
        """分析结果应包含必需字段。"""
        from src.agents.competitor_agent.nodes import analyze_competitors
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["competitor_data"] = {"B0TEST": _sample_competitor_raw()}
        result = analyze_competitors(state)
        analysis = result["analysis_result"]["B0TEST"]
        assert "strengths" in analysis
        assert "weaknesses" in analysis
        assert "competitive_position" in analysis


class TestNodeGenerateProfile:
    """generate_profile 节点测试。"""

    def test_generate_skips_on_error(self):
        """state 有 error 时应直接返回。"""
        from src.agents.competitor_agent.nodes import generate_profile
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(dry_run=True)
        state["error"] = "previous error"
        result = generate_profile(state)
        assert result["error"] == "previous error"
        assert result["competitor_profile"] == {}

    def test_generate_profile_produces_report(self):
        """应生成完整竞品画像报告。"""
        from src.agents.competitor_agent.nodes import (
            fetch_asin_data, analyze_competitors, generate_profile
        )
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state = fetch_asin_data(state)
        state = analyze_competitors(state)
        state = generate_profile(state)
        assert state.get("error") is None
        assert isinstance(state["competitor_profile"], dict)
        assert "market_summary" in state["competitor_profile"]

    def test_generate_profile_contains_profiles_list(self):
        """竞品画像报告应包含 competitor_profiles 列表。"""
        from src.agents.competitor_agent.nodes import (
            fetch_asin_data, analyze_competitors, generate_profile
        )
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state = fetch_asin_data(state)
        state = analyze_competitors(state)
        state = generate_profile(state)
        profile = state["competitor_profile"]
        assert "competitor_profiles" in profile
        assert isinstance(profile["competitor_profiles"], list)


class TestNodeFinalizeRun:
    """finalize_run 节点测试。"""

    def test_finalize_sets_completed_on_success(self):
        """无 error 时应设置 status=completed。"""
        from src.agents.competitor_agent.nodes import finalize_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["agent_run_id"] = str(uuid.uuid4())
        result = finalize_run(state)
        assert result["status"] == "completed"

    def test_finalize_sets_failed_on_error(self):
        """有 error 时应设置 status=failed。"""
        from src.agents.competitor_agent.nodes import finalize_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["error"] = "something went wrong"
        state["agent_run_id"] = str(uuid.uuid4())
        result = finalize_run(state)
        assert result["status"] == "failed"

    def test_finalize_skips_db_in_dry_run(self):
        """dry_run=True 时应跳过 DB 写入。"""
        from src.agents.competitor_agent.nodes import finalize_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["agent_run_id"] = str(uuid.uuid4())
        with patch("src.agents.competitor_agent.nodes.db_session") as mock_db:
            finalize_run(state)
            mock_db.assert_not_called()

    def test_finalize_writes_db_when_not_dry_run(self):
        """dry_run=False 且DB可用时应写入DB。"""
        from src.agents.competitor_agent.nodes import finalize_run
        from src.agents.competitor_agent.schemas import CompetitorState

        mock_cm, mock_session, mock_run = _make_mock_db_with_agent_run()
        run_id = str(uuid.uuid4())
        state = CompetitorState(target_asin="B0TARGET", dry_run=False)
        state["agent_run_id"] = run_id

        with patch("src.agents.competitor_agent.nodes.db_session", mock_cm), \
             patch("src.agents.competitor_agent.nodes._DB_AVAILABLE", True), \
             patch("src.agents.competitor_agent.nodes.AgentRun", MagicMock()):
            result = finalize_run(state)

        assert result["status"] == "completed"

    def test_finalize_handles_audit_log_failure(self):
        """审计日志写入失败不应影响节点返回。"""
        from src.agents.competitor_agent.nodes import finalize_run
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["agent_run_id"] = str(uuid.uuid4())
        with patch("src.utils.audit.log_action", side_effect=Exception("audit error")):
            result = finalize_run(state)
        assert result["status"] == "completed"


# ============================================================================ #
#  4. agent.execute 测试
# ============================================================================ #

class TestAgentExecute:
    """agent.execute 函数测试。"""

    def test_execute_dry_run_basic(self):
        """dry_run=True 基本调用应成功。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT", dry_run=True)
        assert result["status"] == "completed"
        assert result["error"] is None

    def test_execute_missing_target_asin_fails(self):
        """未提供 target_asin 时应返回 failed 状态。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="", dry_run=True)
        assert result["status"] == "failed"
        assert result["error"] is not None

    def test_execute_returns_all_required_fields(self):
        """返回结果应包含所有必需字段。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT", dry_run=True)
        expected_keys = {
            "target_asin", "competitor_profiles", "market_summary",
            "price_range", "avg_rating", "top_keywords",
            "differentiation_suggestions", "agent_run_id",
            "status", "error",
        }
        assert expected_keys.issubset(result.keys())

    def test_execute_target_asin_in_result(self):
        """返回结果中的 target_asin 应与输入一致。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT123", dry_run=True)
        assert result["target_asin"] == "B0MYPRODUCT123"

    def test_execute_competitor_profiles_is_list(self):
        """competitor_profiles 应为列表类型。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT", dry_run=True)
        assert isinstance(result["competitor_profiles"], list)

    def test_execute_price_range_has_required_keys(self):
        """price_range 应包含 min/max/avg 字段。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT", dry_run=True)
        price_range = result["price_range"]
        assert "min" in price_range
        assert "max" in price_range
        assert "avg" in price_range

    def test_execute_agent_run_id_is_nonempty(self):
        """成功执行时 agent_run_id 应非空。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT", dry_run=True)
        assert result["agent_run_id"] != "" and result["agent_run_id"] is not None

    def test_execute_with_specific_competitor_asins(self):
        """指定竞品ASIN时应分析指定的竞品。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(
            target_asin="B0MYPRODUCT",
            competitor_asins=["B0COMPETITOR1", "B0COMPETITOR2"],
            dry_run=True,
        )
        assert result["status"] == "completed"
        assert len(result["competitor_profiles"]) == 2

    def test_execute_differentiation_suggestions_nonempty(self):
        """成功执行时差异化建议应非空。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT", dry_run=True)
        assert isinstance(result["differentiation_suggestions"], list)
        assert len(result["differentiation_suggestions"]) > 0

    def test_execute_market_summary_is_string(self):
        """市场概要应为非空字符串。"""
        from src.agents.competitor_agent.agent import execute
        result = execute(target_asin="B0MYPRODUCT", dry_run=True)
        assert isinstance(result["market_summary"], str)
        assert len(result["market_summary"]) > 0


# ============================================================================ #
#  5. 导入测试
# ============================================================================ #

class TestImports:
    """模块导入测试。"""

    def test_can_import_execute(self):
        """应能从 competitor_agent 导入 execute 函数。"""
        from src.agents.competitor_agent import execute
        assert callable(execute)

    def test_can_import_schemas(self):
        """应能导入 Schema 类。"""
        from src.agents.competitor_agent.schemas import (
            CompetitorProfile, CompetitorAnalysis, CompetitorState
        )
        assert issubclass(CompetitorState, dict)

    def test_can_import_analyzer(self):
        """应能导入 analyzer 函数。"""
        from src.agents.competitor_agent.analyzer import (
            analyze_competitor_data,
            extract_strengths_weaknesses,
            calculate_competitive_position,
            build_competitor_analysis,
        )
        assert callable(analyze_competitor_data)
        assert callable(extract_strengths_weaknesses)
        assert callable(calculate_competitive_position)
        assert callable(build_competitor_analysis)

    def test_can_import_nodes(self):
        """应能导入 nodes 函数。"""
        from src.agents.competitor_agent.nodes import (
            init_run, fetch_asin_data, analyze_competitors, generate_profile, finalize_run
        )
        for fn in [init_run, fetch_asin_data, analyze_competitors, generate_profile, finalize_run]:
            assert callable(fn)

    def test_can_import_prompts(self):
        """应能导入提示词常量。"""
        from src.agents.competitor_agent.prompts import (
            COMPETITOR_ANALYSIS_PROMPT, SWOT_PROMPT, MARKET_SUMMARY_PROMPT
        )
        assert isinstance(COMPETITOR_ANALYSIS_PROMPT, str)
        assert isinstance(SWOT_PROMPT, str)
        assert isinstance(MARKET_SUMMARY_PROMPT, str)


# ============================================================================ #
#  6. prompts 测试
# ============================================================================ #

class TestPrompts:
    """提示词模板测试。"""

    def test_competitor_analysis_prompt_not_empty(self):
        """COMPETITOR_ANALYSIS_PROMPT 应非空。"""
        from src.agents.competitor_agent.prompts import COMPETITOR_ANALYSIS_PROMPT
        assert len(COMPETITOR_ANALYSIS_PROMPT.strip()) > 0

    def test_swot_prompt_not_empty(self):
        """SWOT_PROMPT 应非空。"""
        from src.agents.competitor_agent.prompts import SWOT_PROMPT
        assert len(SWOT_PROMPT.strip()) > 0

    def test_market_summary_prompt_not_empty(self):
        """MARKET_SUMMARY_PROMPT 应非空。"""
        from src.agents.competitor_agent.prompts import MARKET_SUMMARY_PROMPT
        assert len(MARKET_SUMMARY_PROMPT.strip()) > 0

    def test_competitor_analysis_prompt_has_placeholders(self):
        """COMPETITOR_ANALYSIS_PROMPT 应包含 {asin} 占位符。"""
        from src.agents.competitor_agent.prompts import COMPETITOR_ANALYSIS_PROMPT
        assert "{asin}" in COMPETITOR_ANALYSIS_PROMPT

    def test_swot_prompt_has_placeholders(self):
        """SWOT_PROMPT 应包含模板占位符。"""
        from src.agents.competitor_agent.prompts import SWOT_PROMPT
        assert "{" in SWOT_PROMPT and "}" in SWOT_PROMPT


# ============================================================================ #
#  7. 边界条件与集成测试
# ============================================================================ #

class TestEdgeCases:
    """边界条件测试。"""

    def test_analyze_competitor_with_bsr_rank_100(self):
        """BSR排名100以内应识别为优势。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        strengths, _ = extract_strengths_weaknesses({"rating": 4.0, "bsr_rank": 50, "review_count": 100})
        assert any("BSR" in s or "排名" in s or "销量" in s for s in strengths)

    def test_analyze_competitor_with_high_bsr_rank(self):
        """BSR排名过高应识别为劣势。"""
        from src.agents.competitor_agent.analyzer import extract_strengths_weaknesses
        _, weaknesses = extract_strengths_weaknesses({"rating": 4.0, "bsr_rank": 5000, "review_count": 100})
        assert any("BSR" in w or "排名" in w or "靠后" in w for w in weaknesses)

    def test_calculate_position_returns_string(self):
        """calculate_competitive_position 始终返回字符串。"""
        from src.agents.competitor_agent.analyzer import calculate_competitive_position
        result = calculate_competitive_position(4.0, 100, 25.0, {"avg_rating": 4.0, "avg_reviews": 100, "avg_price": 25.0})
        assert isinstance(result, str)

    def test_state_error_propagation_through_nodes(self):
        """错误状态应在各节点间传播（跳过节点）。"""
        from src.agents.competitor_agent.nodes import fetch_asin_data, analyze_competitors
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0TARGET", dry_run=True)
        state["error"] = "early error"
        state["competitor_data"] = {"B0TEST": _sample_competitor_raw()}
        result_after_fetch = fetch_asin_data(state)
        assert result_after_fetch["error"] == "early error"
        result_after_analyze = analyze_competitors(result_after_fetch)
        assert result_after_analyze["error"] == "early error"

    def test_build_analysis_with_profile_objects(self):
        """build_competitor_analysis 应接受 CompetitorProfile 对象。"""
        from src.agents.competitor_agent.analyzer import build_competitor_analysis
        from src.agents.competitor_agent.schemas import CompetitorProfile
        profile = CompetitorProfile(
            asin="B0TEST",
            price=25.0,
            rating=4.2,
            review_count=500,
        )
        result = build_competitor_analysis("B0TARGET", [profile])
        assert result["target_asin"] == "B0TARGET"
        assert len(result["competitor_profiles"]) == 1

    def test_full_workflow_sequential(self):
        """完整顺序工作流应成功执行。"""
        from src.agents.competitor_agent.agent import _run_sequential
        from src.agents.competitor_agent.schemas import CompetitorState
        state = CompetitorState(target_asin="B0MYPRODUCT", dry_run=True)
        result = _run_sequential(state)
        assert result["status"] == "completed"
        assert result.get("error") is None

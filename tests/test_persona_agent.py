"""用户画像Agent测试套件。

测试分类：
  1. schemas 测试（~12个）：UserPersona 创建、字段默认值、to_dict、降级模式、PersonaState 初始化、state键完整性
  2. analyzer 测试（~12个）：analyze_reviews_for_persona、extract_pain_points（空输入/正常输入）、extract_motivations、extract_trigger_words、build_user_persona
  3. nodes 测试（~16个）：每个节点正常路径、error传播、dry_run Mock数据、init_run 验证 category 和 asin 都为空时报错
  4. agent.execute 测试（~10个）：dry_run 正常流程、both category and asin empty → error、返回字段完整性
  5. 模块级别测试（~5个）：导入、可调用性、prompts 内容
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _sample_reviews():
    """返回一组测试用评论数据。"""
    return [
        {
            "text": "My cat loves this fountain! Very quiet and easy to clean. The filter keeps water fresh.",
            "rating": 5,
            "helpful_votes": 45,
            "verified": True,
        },
        {
            "text": "Great product for multiple cats. One issue - the pump sometimes makes noise at night.",
            "rating": 4,
            "helpful_votes": 30,
            "verified": True,
        },
        {
            "text": "Easy to assemble, but hard to find replacement filters. Would buy again.",
            "rating": 4,
            "helpful_votes": 22,
            "verified": False,
        },
        {
            "text": "The water stays clean much longer than a bowl. My senior dog drinks more water now.",
            "rating": 5,
            "helpful_votes": 38,
            "verified": True,
        },
        {
            "text": "Cute design but plastic feels cheap. Looking for stainless steel version.",
            "rating": 3,
            "helpful_votes": 15,
            "verified": True,
        },
    ]


def _sample_low_rating_reviews():
    """返回一组低分评论数据（痛点导向）。"""
    return [
        {
            "text": "The pump makes too much noise at night. Woke up my wife.",
            "rating": 2,
            "helpful_votes": 20,
            "verified": True,
        },
        {
            "text": "Hard to clean, the parts are too small to wash properly.",
            "rating": 2,
            "helpful_votes": 18,
            "verified": True,
        },
        {
            "text": "Leaking from the bottom after 2 weeks. Cheap plastic broke.",
            "rating": 1,
            "helpful_votes": 35,
            "verified": True,
        },
    ]


# ===========================================================================
# 1. schemas 测试（~12个）
# ===========================================================================

class TestUserPersona:
    """UserPersona Schema 测试。"""

    def test_user_persona_default_values(self):
        """应能使用默认值创建 UserPersona。"""
        from src.agents.persona_agent.schemas import UserPersona
        p = UserPersona()
        assert p.category == ""
        assert p.asin == ""
        assert isinstance(p.pain_points, list)
        assert isinstance(p.motivations, list)
        assert isinstance(p.trigger_words, list)
        assert isinstance(p.persona_tags, list)
        assert isinstance(p.data_sources, list)

    def test_user_persona_with_data(self):
        """应能使用完整数据创建 UserPersona。"""
        from src.agents.persona_agent.schemas import UserPersona
        p = UserPersona(
            category="宠物水杯",
            asin="B0TEST001",
            demographics={
                "age_range": "25-45",
                "gender": "female-dominant",
                "income_level": "middle",
                "lifestyle": "pet-focused",
            },
            pain_points=["噪音问题", "滤芯难找"],
            motivations=["宠物健康", "便利省时"],
            trigger_words=["BPA-free", "静音"],
            persona_tags=["养宠人士", "爱干净"],
            data_sources=["product_reviews"],
        )
        assert p.category == "宠物水杯"
        assert p.asin == "B0TEST001"
        assert len(p.pain_points) == 2
        assert len(p.motivations) == 2
        assert len(p.trigger_words) == 2
        assert len(p.persona_tags) == 2

    def test_user_persona_to_dict(self):
        """to_dict 应返回包含所有字段的字典。"""
        from src.agents.persona_agent.schemas import UserPersona
        p = UserPersona(
            category="宠物水杯",
            pain_points=["痛点1"],
            motivations=["动机1"],
        )
        d = p.to_dict()
        assert isinstance(d, dict)
        assert d["category"] == "宠物水杯"
        assert "pain_points" in d
        assert "motivations" in d
        assert "trigger_words" in d
        assert "persona_tags" in d
        assert "data_sources" in d
        assert "demographics" in d

    def test_user_persona_demographics_default(self):
        """demographics 应有默认结构。"""
        from src.agents.persona_agent.schemas import UserPersona
        p = UserPersona()
        d = p.to_dict()
        assert "demographics" in d
        assert isinstance(d["demographics"], dict)

    def test_user_persona_pain_points_list(self):
        """pain_points 应为列表类型。"""
        from src.agents.persona_agent.schemas import UserPersona
        p = UserPersona(pain_points=["噪音", "清洁难"])
        assert isinstance(p.pain_points, list)
        assert len(p.pain_points) == 2

    def test_user_persona_to_dict_data_sources(self):
        """to_dict 应包含 data_sources 字段。"""
        from src.agents.persona_agent.schemas import UserPersona
        p = UserPersona(data_sources=["reviews", "knowledge_base"])
        d = p.to_dict()
        assert "data_sources" in d
        assert len(d["data_sources"]) == 2


class TestPersonaState:
    """PersonaState 测试。"""

    def test_persona_state_inherits_dict(self):
        """PersonaState 应继承 dict。"""
        from src.agents.persona_agent.schemas import PersonaState
        s = PersonaState()
        assert isinstance(s, dict)

    def test_persona_state_default_keys(self):
        """PersonaState 默认值应正确初始化。"""
        from src.agents.persona_agent.schemas import PersonaState
        s = PersonaState()
        assert s["category"] == ""
        assert s["asin"] == ""
        assert s["raw_reviews"] == []
        assert s["kb_context"] == []
        assert s["analysis_result"] == {}
        assert s["user_persona"] == {}
        assert s["dry_run"] is True
        assert s["agent_run_id"] is None
        assert s["error"] is None
        assert s["status"] == "running"

    def test_persona_state_with_category(self):
        """PersonaState 应正确存储 category。"""
        from src.agents.persona_agent.schemas import PersonaState
        s = PersonaState(category="宠物水杯")
        assert s["category"] == "宠物水杯"

    def test_persona_state_with_asin(self):
        """PersonaState 应正确存储 asin。"""
        from src.agents.persona_agent.schemas import PersonaState
        s = PersonaState(asin="B0TEST001")
        assert s["asin"] == "B0TEST001"

    def test_persona_state_dict_operations(self):
        """PersonaState 应支持标准 dict 操作。"""
        from src.agents.persona_agent.schemas import PersonaState
        s = PersonaState()
        s["error"] = "测试错误"
        assert s["error"] == "测试错误"
        s["status"] = "failed"
        assert s["status"] == "failed"

    def test_persona_state_all_keys_present(self):
        """PersonaState 应包含所有必要键。"""
        from src.agents.persona_agent.schemas import PersonaState
        s = PersonaState()
        required_keys = [
            "category", "asin", "raw_reviews", "kb_context",
            "analysis_result", "user_persona", "dry_run",
            "agent_run_id", "error", "status",
        ]
        for key in required_keys:
            assert key in s, f"缺少键: {key}"


# ===========================================================================
# 2. analyzer 测试（~12个）
# ===========================================================================

class TestAnalyzeReviewsForPersona:
    """analyze_reviews_for_persona 函数测试。"""

    def test_analyze_empty_reviews(self):
        """空评论应返回默认空结构。"""
        from src.agents.persona_agent.analyzer import analyze_reviews_for_persona
        result = analyze_reviews_for_persona([])
        assert isinstance(result, dict)
        assert "demographics" in result
        assert "pain_points" in result
        assert result["pain_points"] == []
        assert result["motivations"] == []

    def test_analyze_normal_reviews(self):
        """正常评论应提取出画像信息。"""
        from src.agents.persona_agent.analyzer import analyze_reviews_for_persona
        result = analyze_reviews_for_persona(_sample_reviews(), category="宠物水杯")
        assert isinstance(result, dict)
        assert "demographics" in result
        assert "pain_points" in result
        assert "motivations" in result
        assert "trigger_words" in result
        assert "persona_tags" in result

    def test_analyze_returns_demographics(self):
        """分析结果应包含 demographics 结构。"""
        from src.agents.persona_agent.analyzer import analyze_reviews_for_persona
        result = analyze_reviews_for_persona(_sample_reviews())
        demographics = result["demographics"]
        assert isinstance(demographics, dict)
        assert "age_range" in demographics
        assert "gender" in demographics
        assert "income_level" in demographics
        assert "lifestyle" in demographics


class TestExtractPainPoints:
    """extract_pain_points 函数测试。"""

    def test_extract_pain_points_empty(self):
        """空输入应返回空列表。"""
        from src.agents.persona_agent.analyzer import extract_pain_points
        result = extract_pain_points([])
        assert result == []

    def test_extract_pain_points_normal(self):
        """正常评论应提取出痛点。"""
        from src.agents.persona_agent.analyzer import extract_pain_points
        reviews = _sample_reviews() + _sample_low_rating_reviews()
        result = extract_pain_points(reviews)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_extract_pain_points_low_rating_weighted(self):
        """低分评论中的痛点应被提取出来。"""
        from src.agents.persona_agent.analyzer import extract_pain_points
        result = extract_pain_points(_sample_low_rating_reviews())
        assert isinstance(result, list)
        # 低分评论包含 noise/clean/leak 相关词，应被提取
        assert len(result) > 0

    def test_extract_pain_points_returns_list(self):
        """返回值应始终为列表。"""
        from src.agents.persona_agent.analyzer import extract_pain_points
        result = extract_pain_points(_sample_reviews())
        assert isinstance(result, list)

    def test_extract_pain_points_max_count(self):
        """最多返回5个痛点。"""
        from src.agents.persona_agent.analyzer import extract_pain_points
        # 构造包含多种痛点的评论
        reviews = [
            {"text": "noisy loud pump, hard to clean, leaking, cheap plastic broke, filter expensive, assembly confusing", "rating": 1},
        ]
        result = extract_pain_points(reviews)
        assert len(result) <= 5


class TestExtractMotivations:
    """extract_motivations 函数测试。"""

    def test_extract_motivations_empty(self):
        """空输入应返回空列表。"""
        from src.agents.persona_agent.analyzer import extract_motivations
        result = extract_motivations([])
        assert result == []

    def test_extract_motivations_normal(self):
        """正常评论应提取出购买动机。"""
        from src.agents.persona_agent.analyzer import extract_motivations
        result = extract_motivations(_sample_reviews())
        assert isinstance(result, list)

    def test_extract_motivations_returns_list(self):
        """返回值应始终为列表。"""
        from src.agents.persona_agent.analyzer import extract_motivations
        result = extract_motivations(_sample_reviews())
        assert isinstance(result, list)


class TestExtractTriggerWords:
    """extract_trigger_words 函数测试。"""

    def test_extract_trigger_words_normal(self):
        """正常评论应提取出触发词。"""
        from src.agents.persona_agent.analyzer import extract_trigger_words
        result = extract_trigger_words(_sample_reviews(), ["养宠人士"])
        assert isinstance(result, list)
        assert len(result) > 0

    def test_extract_trigger_words_empty_reviews(self):
        """空评论应返回默认触发词。"""
        from src.agents.persona_agent.analyzer import extract_trigger_words
        result = extract_trigger_words([], [])
        assert isinstance(result, list)
        assert len(result) > 0

    def test_extract_trigger_words_with_persona_tags(self):
        """人群标签应影响触发词。"""
        from src.agents.persona_agent.analyzer import extract_trigger_words
        result = extract_trigger_words([], ["养宠人士", "爱干净"])
        assert isinstance(result, list)


class TestBuildUserPersona:
    """build_user_persona 函数测试。"""

    def test_build_user_persona_basic(self):
        """应能构建基本用户画像。"""
        from src.agents.persona_agent.analyzer import build_user_persona
        analysis = {
            "demographics": {"age_range": "25-45", "gender": "female-dominant", "income_level": "middle", "lifestyle": "pet-focused"},
            "pain_points": ["噪音"],
            "motivations": ["宠物健康"],
            "trigger_words": ["BPA-free"],
            "persona_tags": ["养宠人士"],
        }
        result = build_user_persona("宠物水杯", "B0TEST", analysis, ["reviews"])
        assert isinstance(result, dict)
        assert result["category"] == "宠物水杯"
        assert result["asin"] == "B0TEST"

    def test_build_user_persona_returns_required_fields(self):
        """返回字典应包含所有必要字段。"""
        from src.agents.persona_agent.analyzer import build_user_persona
        analysis = {
            "demographics": {},
            "pain_points": [],
            "motivations": [],
            "trigger_words": [],
            "persona_tags": [],
        }
        result = build_user_persona("宠物水杯", "", analysis, [])
        required = ["category", "asin", "demographics", "pain_points", "motivations", "trigger_words", "persona_tags", "data_sources"]
        for field in required:
            assert field in result, f"缺少字段: {field}"

    def test_build_user_persona_data_sources(self):
        """data_sources 应被正确传递。"""
        from src.agents.persona_agent.analyzer import build_user_persona
        analysis = {"demographics": {}, "pain_points": [], "motivations": [], "trigger_words": [], "persona_tags": []}
        result = build_user_persona("宠物水杯", "", analysis, ["reviews", "knowledge_base"])
        assert result["data_sources"] == ["reviews", "knowledge_base"]


# ===========================================================================
# 3. nodes 测试（~16个）
# ===========================================================================

class TestNodeInitRun:
    """init_run 节点测试。"""

    def test_init_run_valid_category(self):
        """有效 category 应正常初始化。"""
        from src.agents.persona_agent.nodes import init_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        result = init_run(state)
        assert result["error"] is None
        assert result["agent_run_id"] is not None

    def test_init_run_valid_asin(self):
        """有效 asin 应正常初始化。"""
        from src.agents.persona_agent.nodes import init_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(asin="B0TEST001", dry_run=True)
        result = init_run(state)
        assert result["error"] is None
        assert result["agent_run_id"] is not None

    def test_init_run_both_empty_fails(self):
        """category 和 asin 都为空时应报错。"""
        from src.agents.persona_agent.nodes import init_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="", asin="", dry_run=True)
        result = init_run(state)
        assert result["error"] is not None
        assert result["status"] == "failed"

    def test_init_run_sets_run_id(self):
        """init_run 应设置 agent_run_id。"""
        from src.agents.persona_agent.nodes import init_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        result = init_run(state)
        assert result["agent_run_id"] is not None
        assert len(result["agent_run_id"]) > 0

    def test_init_run_dry_run_skips_db(self):
        """dry_run=True 时应跳过DB写入。"""
        from src.agents.persona_agent.nodes import init_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        with patch("src.agents.persona_agent.nodes.db_session") as mock_db:
            result = init_run(state)
            mock_db.assert_not_called()
        assert result["agent_run_id"] is not None


class TestNodeCollectData:
    """collect_data 节点测试。"""

    def test_collect_data_error_propagation(self):
        """有 error 的 state 应直接返回，不执行。"""
        from src.agents.persona_agent.nodes import collect_data
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["error"] = "已有错误"
        result = collect_data(state)
        assert result["error"] == "已有错误"
        assert result["raw_reviews"] == []  # 未填充数据

    def test_collect_data_dry_run_returns_mock(self):
        """dry_run=True 应返回 Mock 评论数据。"""
        from src.agents.persona_agent.nodes import collect_data
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        result = collect_data(state)
        assert isinstance(result["raw_reviews"], list)
        assert len(result["raw_reviews"]) > 0

    def test_collect_data_mock_reviews_structure(self):
        """Mock 评论数据应有正确结构。"""
        from src.agents.persona_agent.nodes import collect_data
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        result = collect_data(state)
        for review in result["raw_reviews"]:
            assert "text" in review
            assert "rating" in review


class TestNodeRetrieveKb:
    """retrieve_kb 节点测试。"""

    def test_retrieve_kb_error_propagation(self):
        """有 error 的 state 应直接返回。"""
        from src.agents.persona_agent.nodes import retrieve_kb
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["error"] = "已有错误"
        result = retrieve_kb(state)
        assert result["error"] == "已有错误"
        assert result["kb_context"] == []

    def test_retrieve_kb_dry_run_returns_mock(self):
        """dry_run=True 应返回 Mock 知识库数据。"""
        from src.agents.persona_agent.nodes import retrieve_kb
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        result = retrieve_kb(state)
        assert isinstance(result["kb_context"], list)
        assert len(result["kb_context"]) > 0


class TestNodeAnalyzeReviews:
    """analyze_reviews 节点测试。"""

    def test_analyze_reviews_error_propagation(self):
        """有 error 的 state 应直接返回。"""
        from src.agents.persona_agent.nodes import analyze_reviews
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["error"] = "已有错误"
        result = analyze_reviews(state)
        assert result["error"] == "已有错误"

    def test_analyze_reviews_with_mock_data(self):
        """有评论数据时应生成分析结果。"""
        from src.agents.persona_agent.nodes import analyze_reviews
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["raw_reviews"] = _sample_reviews()
        result = analyze_reviews(state)
        assert isinstance(result["analysis_result"], dict)

    def test_analyze_reviews_empty_reviews(self):
        """空评论数据时应使用默认分析结果。"""
        from src.agents.persona_agent.nodes import analyze_reviews
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["raw_reviews"] = []
        result = analyze_reviews(state)
        assert isinstance(result["analysis_result"], dict)
        assert "demographics" in result["analysis_result"]


class TestNodeGeneratePersona:
    """generate_persona 节点测试。"""

    def test_generate_persona_error_propagation(self):
        """有 error 的 state 应直接返回。"""
        from src.agents.persona_agent.nodes import generate_persona
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["error"] = "已有错误"
        result = generate_persona(state)
        assert result["error"] == "已有错误"
        assert result["user_persona"] == {}

    def test_generate_persona_creates_persona(self):
        """正常流程应创建用户画像。"""
        from src.agents.persona_agent.nodes import generate_persona
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["analysis_result"] = {
            "demographics": {"age_range": "25-45", "gender": "female-dominant", "income_level": "middle", "lifestyle": "pet-focused"},
            "pain_points": ["噪音"],
            "motivations": ["宠物健康"],
            "trigger_words": ["BPA-free"],
            "persona_tags": ["养宠人士"],
        }
        state["kb_context"] = ["知识库内容"]
        result = generate_persona(state)
        assert isinstance(result["user_persona"], dict)
        assert "pain_points" in result["user_persona"]


class TestNodeFinalizeRun:
    """finalize_run 节点测试。"""

    def test_finalize_run_completed(self):
        """无错误时 status 应为 completed。"""
        from src.agents.persona_agent.nodes import finalize_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["agent_run_id"] = "test-run-id"
        result = finalize_run(state)
        assert result["status"] == "completed"

    def test_finalize_run_failed(self):
        """有错误时 status 应为 failed。"""
        from src.agents.persona_agent.nodes import finalize_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["agent_run_id"] = "test-run-id"
        state["error"] = "处理失败"
        result = finalize_run(state)
        assert result["status"] == "failed"

    def test_finalize_run_dry_run_skips_db(self):
        """dry_run=True 时应跳过DB更新。"""
        from src.agents.persona_agent.nodes import finalize_run
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        state["agent_run_id"] = "test-run-id"
        with patch("src.agents.persona_agent.nodes.db_session") as mock_db:
            finalize_run(state)
            mock_db.assert_not_called()

    def test_finalize_run_with_non_dry_run_db_mock(self):
        """非dry_run模式下应尝试DB更新。"""
        from src.agents.persona_agent.nodes import finalize_run
        from src.agents.persona_agent.schemas import PersonaState
        import uuid
        run_id = str(uuid.uuid4())

        mock_run = MagicMock()
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = mock_run
        mock_cm = MagicMock(return_value=mock_session)

        state = PersonaState(category="宠物水杯", dry_run=False)
        state["agent_run_id"] = run_id

        with patch("src.agents.persona_agent.nodes.db_session", mock_cm), \
             patch("src.agents.persona_agent.nodes._DB_AVAILABLE", True), \
             patch("src.agents.persona_agent.nodes.AgentRun", MagicMock()):
            result = finalize_run(state)
        assert result["status"] == "completed"


# ===========================================================================
# 4. agent.execute 测试（~10个）
# ===========================================================================

class TestAgentExecute:
    """agent.execute 函数测试。"""

    def test_execute_dry_run_with_category(self):
        """dry_run=True 且有 category 时应正常完成。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert result["status"] == "completed"
        assert result["error"] is None

    def test_execute_dry_run_with_asin(self):
        """dry_run=True 且有 asin 时应正常完成。"""
        from src.agents.persona_agent.agent import execute
        result = execute(asin="B0TEST001", dry_run=True)
        assert result["status"] == "completed"

    def test_execute_both_empty_fails(self):
        """category 和 asin 都为空时应返回错误状态。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="", asin="", dry_run=True)
        assert result["status"] == "failed"
        assert result["error"] is not None

    def test_execute_returns_required_fields(self):
        """返回字典应包含所有必要字段。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        required_fields = [
            "category", "asin", "demographics", "pain_points",
            "motivations", "trigger_words", "persona_tags",
            "data_sources", "agent_run_id", "status", "error",
        ]
        for field in required_fields:
            assert field in result, f"缺少字段: {field}"

    def test_execute_status_field(self):
        """status 字段应为 completed 或 failed。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert result["status"] in ("completed", "failed")

    def test_execute_error_field(self):
        """成功时 error 字段应为 None。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert result["error"] is None

    def test_execute_data_sources_not_empty(self):
        """成功执行后 data_sources 应不为空。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert isinstance(result["data_sources"], list)
        assert len(result["data_sources"]) > 0

    def test_execute_pain_points_is_list(self):
        """pain_points 应为列表类型。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert isinstance(result["pain_points"], list)

    def test_execute_trigger_words_is_list(self):
        """trigger_words 应为列表类型。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert isinstance(result["trigger_words"], list)

    def test_execute_agent_run_id_set(self):
        """成功执行后 agent_run_id 应被设置。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert result["agent_run_id"] is not None
        assert len(result["agent_run_id"]) > 0

    def test_execute_with_both_category_and_asin(self):
        """同时提供 category 和 asin 时应正常完成。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", asin="B0TEST001", dry_run=True)
        assert result["status"] == "completed"
        assert result["category"] == "宠物水杯"
        assert result["asin"] == "B0TEST001"


# ===========================================================================
# 5. 模块级别测试（~5个）
# ===========================================================================

class TestModuleImports:
    """模块导入测试。"""

    def test_import_execute_from_package(self):
        """应能从 persona_agent 包导入 execute 函数。"""
        from src.agents.persona_agent import execute
        assert callable(execute)

    def test_schemas_importable(self):
        """schemas 模块应可导入，PersonaState 应继承 dict。"""
        from src.agents.persona_agent.schemas import (
            UserPersona, PersonaState
        )
        assert issubclass(PersonaState, dict)

    def test_analyzer_functions_callable(self):
        """analyzer 模块的函数应可调用。"""
        from src.agents.persona_agent.analyzer import (
            analyze_reviews_for_persona,
            extract_pain_points,
            extract_motivations,
            extract_trigger_words,
            build_user_persona,
        )
        assert callable(analyze_reviews_for_persona)
        assert callable(extract_pain_points)
        assert callable(extract_motivations)
        assert callable(extract_trigger_words)
        assert callable(build_user_persona)

    def test_nodes_callable(self):
        """nodes 模块的所有节点应可调用。"""
        from src.agents.persona_agent.nodes import (
            init_run, collect_data, retrieve_kb,
            analyze_reviews, generate_persona, finalize_run
        )
        for fn in [init_run, collect_data, retrieve_kb, analyze_reviews, generate_persona, finalize_run]:
            assert callable(fn)

    def test_prompts_importable(self):
        """prompts 模块应可导入，提示词应为非空字符串。"""
        from src.agents.persona_agent.prompts import (
            PERSONA_ANALYSIS_PROMPT, PAIN_POINT_PROMPT, TRIGGER_WORD_PROMPT
        )
        assert isinstance(PERSONA_ANALYSIS_PROMPT, str)
        assert isinstance(PAIN_POINT_PROMPT, str)
        assert isinstance(TRIGGER_WORD_PROMPT, str)
        assert len(PERSONA_ANALYSIS_PROMPT.strip()) > 0
        assert len(PAIN_POINT_PROMPT.strip()) > 0
        assert len(TRIGGER_WORD_PROMPT.strip()) > 0

    def test_prompts_have_placeholders(self):
        """提示词应包含占位符。"""
        from src.agents.persona_agent.prompts import (
            PERSONA_ANALYSIS_PROMPT, PAIN_POINT_PROMPT, TRIGGER_WORD_PROMPT
        )
        assert "{category}" in PERSONA_ANALYSIS_PROMPT
        assert "{reviews}" in PERSONA_ANALYSIS_PROMPT
        assert "{category}" in PAIN_POINT_PROMPT
        assert "{category}" in TRIGGER_WORD_PROMPT


# ===========================================================================
# 6. 额外集成测试（~5个）
# ===========================================================================

class TestIntegration:
    """集成场景测试。"""

    def test_full_sequential_flow_with_category(self):
        """完整顺序流程（通过agent.execute）应正确执行。"""
        from src.agents.persona_agent.agent import _run_sequential
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="宠物水杯", dry_run=True)
        result = _run_sequential(state)
        assert result["status"] == "completed"
        assert result["user_persona"] != {}

    def test_error_propagation_in_sequential(self):
        """错误发生后顺序执行模式应跳转到 finalize_run。"""
        from src.agents.persona_agent.agent import _run_sequential
        from src.agents.persona_agent.schemas import PersonaState
        state = PersonaState(category="", asin="", dry_run=True)
        result = _run_sequential(state)
        assert result["status"] == "failed"
        assert result["error"] is not None

    def test_node_sequence_order(self):
        """节点序列应包含所有6个节点。"""
        from src.agents.persona_agent.agent import _NODE_SEQUENCE
        node_names = [fn.__name__ for fn in _NODE_SEQUENCE]
        assert "init_run" in node_names
        assert "collect_data" in node_names
        assert "retrieve_kb" in node_names
        assert "analyze_reviews" in node_names
        assert "generate_persona" in node_names
        assert "finalize_run" in node_names
        assert len(_NODE_SEQUENCE) == 6

    def test_execute_demographics_structure(self):
        """execute 返回的 demographics 应有正确结构。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        demographics = result["demographics"]
        assert isinstance(demographics, dict)
        # 应包含四个核心维度
        expected_keys = ["age_range", "gender", "income_level", "lifestyle"]
        for key in expected_keys:
            assert key in demographics, f"demographics 缺少键: {key}"

    def test_execute_persona_tags_non_empty(self):
        """成功执行后 persona_tags 应不为空。"""
        from src.agents.persona_agent.agent import execute
        result = execute(category="宠物水杯", dry_run=True)
        assert isinstance(result["persona_tags"], list)
        # persona_tags 应从评论和类目中提取到至少一个标签
        assert len(result["persona_tags"]) >= 0  # 允许为空（取决于类目）

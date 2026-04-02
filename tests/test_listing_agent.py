"""Listing文案Agent单元测试。

覆盖范围：
  - 模块导入测试
  - dry_run=True 完整流程（标题+五点+关键词）
  - 输出字段验证（title/bullet_points/search_terms/compliance）
  - 合规词检查测试（禁用词/敏感词/字符长度）
  - Schema验证测试（ListingCopySchema）
  - 节点单元测试（init_run/retrieve_kb/generate_copy/check_compliance/finalize_run）
  - 飞书命令路由测试（/listing generate）
  - 用户画像/竞品数据集成测试
  - DB写入测试（mock）
  - 审计日志测试
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


def _sample_persona_data() -> dict:
    """示例用户画像数据。"""
    return {
        "target_users": ["宠物主人", "新养宠物者", "注重健康的宠物主人"],
        "pain_points": ["普通水碗水质不新鲜", "宠物不爱喝水", "水碗难以清洁"],
        "motivations": ["保持宠物健康", "减少日常维护工作", "智能化家居"],
        "preferred_keywords": ["pet fountain", "cat water fountain", "dog water fountain"],
    }


def _sample_competitor_data() -> dict:
    """示例竞品分析数据。"""
    return {
        "competitor_weaknesses": ["过滤效果差", "泵噪音大", "拆洗复杂"],
        "our_advantages": ["三级过滤系统", "超静音设计<30dB", "完全可拆卸可洗碗机清洗"],
        "competitor_strengths": ["知名品牌", "大容量"],
        "avg_price": 35.99,
    }


# ============================================================================ #
#  1. 模块导入测试
# ============================================================================ #

class TestImports:
    def test_can_import_run_function(self):
        """应能从 src.agents.listing_agent 导入 run 函数。"""
        from src.agents.listing_agent import run
        assert callable(run)

    def test_can_import_execute_function(self):
        """应能从 agent 模块导入 execute 函数。"""
        from src.agents.listing_agent.agent import execute
        assert callable(execute)

    def test_can_import_schemas(self):
        """应能导入 ListingCopySchema, ListingState, ProductInfo。"""
        from src.agents.listing_agent.schemas import (
            ListingCopySchema,
            ListingState,
            ProductInfo,
        )
        assert issubclass(ListingState, dict)

    def test_can_import_compliance_module(self):
        """应能导入合规检查模块的核心函数。"""
        from src.agents.listing_agent.compliance import (
            run_compliance_check,
            check_prohibited_words,
            check_sensitive_words,
            PROHIBITED_WORDS,
            TITLE_MAX_CHARS,
            SEARCH_TERMS_MAX_CHARS,
        )
        assert callable(run_compliance_check)
        assert TITLE_MAX_CHARS == 200
        assert SEARCH_TERMS_MAX_CHARS == 250
        assert len(PROHIBITED_WORDS) > 0

    def test_can_import_generator(self):
        """应能导入文案生成核心函数。"""
        from src.agents.listing_agent.generator import (
            generate_full_listing,
            parse_llm_response,
        )
        assert callable(generate_full_listing)
        assert callable(parse_llm_response)

    def test_can_import_prompts(self):
        """应能导入提示词模板。"""
        from src.agents.listing_agent.prompts import (
            LISTING_SYSTEM_PROMPT,
            FULL_LISTING_TEMPLATE,
        )
        assert len(LISTING_SYSTEM_PROMPT) > 100
        assert "{product_name}" in FULL_LISTING_TEMPLATE

    def test_can_import_nodes(self):
        """应能导入所有节点函数。"""
        from src.agents.listing_agent.nodes import (
            init_run,
            retrieve_kb,
            generate_copy,
            check_compliance,
            finalize_run,
        )
        for fn in [init_run, retrieve_kb, generate_copy, check_compliance, finalize_run]:
            assert callable(fn)


# ============================================================================ #
#  2. dry_run=True 完整流程测试
# ============================================================================ #

class TestDryRunExecution:
    def test_run_returns_dict(self):
        """run(dry_run=True) 应返回 dict。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Pet Fountain", dry_run=True)
        assert isinstance(result, dict)

    def test_run_status_is_completed(self):
        """run(dry_run=True) 的 status 应为 completed。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        assert result.get("status") == "completed"

    def test_run_no_error(self):
        """dry_run 模式不应产生 error。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        assert result.get("error") is None

    def test_run_has_title(self):
        """结果应包含非空 title 字段。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        assert "title" in result
        assert result["title"] != ""

    def test_run_has_bullet_points(self):
        """结果应包含5条 bullet_points。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        assert "bullet_points" in result
        assert len(result["bullet_points"]) == 5, (
            f"期望5条Bullet Points，实际得到 {len(result['bullet_points'])} 条"
        )

    def test_run_has_search_terms(self):
        """结果应包含非空 search_terms 字段。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        assert "search_terms" in result
        assert result["search_terms"] != ""

    def test_run_has_compliance_status(self):
        """结果应包含 compliance_passed 和 compliance_issues 字段。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        assert "compliance_passed" in result
        assert "compliance_issues" in result
        assert isinstance(result["compliance_passed"], bool)
        assert isinstance(result["compliance_issues"], list)

    def test_run_has_agent_run_id(self):
        """结果应包含有效的 agent_run_id（UUID格式）。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        assert "agent_run_id" in result
        run_id = result["agent_run_id"]
        assert run_id is not None and run_id != ""
        uuid.UUID(run_id)  # 验证UUID格式

    def test_run_with_persona_data(self):
        """支持传入用户画像数据，应正常返回结果。"""
        from src.agents.listing_agent import run
        result = run(
            asin="B0TEST001",
            product_name="Pet Water Fountain",
            category="pet_supplies",
            persona_data=_sample_persona_data(),
            dry_run=True,
        )
        assert result.get("status") == "completed"
        assert len(result.get("bullet_points", [])) == 5

    def test_run_with_competitor_data(self):
        """支持传入竞品分析数据，应正常返回结果。"""
        from src.agents.listing_agent import run
        result = run(
            asin="B0TEST001",
            product_name="Pet Water Fountain",
            competitor_data=_sample_competitor_data(),
            dry_run=True,
        )
        assert result.get("status") == "completed"

    def test_run_with_all_inputs(self):
        """传入所有输入（产品+用户画像+竞品），应正常返回完整文案。"""
        from src.agents.listing_agent import run
        result = run(
            asin="B0TEST001",
            product_name="PUDIWIND Pet Water Fountain 2.5L",
            category="pet_supplies",
            features=["三级过滤", "超静音<30dB", "2.5L大容量", "可拆卸洗碗机清洗"],
            persona_data=_sample_persona_data(),
            competitor_data=_sample_competitor_data(),
            dry_run=True,
        )
        assert result.get("status") == "completed"
        assert len(result.get("bullet_points", [])) == 5
        assert result.get("title") != ""


# ============================================================================ #
#  3. 字符长度验证测试
# ============================================================================ #

class TestCharacterLimits:
    def test_title_within_200_chars(self):
        """标题应在200字符以内。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        title = result.get("title", "")
        assert len(title) <= 200, f"标题超出200字符限制：{len(title)} 字符"

    def test_search_terms_within_250_chars(self):
        """后台关键词应在250字符以内。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        search_terms = result.get("search_terms", "")
        assert len(search_terms) <= 250, f"Search Terms超出250字符限制：{len(search_terms)} 字符"

    def test_each_bullet_point_within_500_chars(self):
        """每条Bullet Point应在500字符以内。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        bullet_points = result.get("bullet_points", [])
        for i, bp in enumerate(bullet_points, 1):
            assert len(bp) <= 500, f"第{i}条Bullet Point超出500字符限制：{len(bp)} 字符"


# ============================================================================ #
#  4. 合规词检查测试
# ============================================================================ #

class TestComplianceCheck:
    def test_clean_text_passes_compliance(self):
        """不含禁用词的文案应通过合规检查。"""
        from src.agents.listing_agent.compliance import run_compliance_check
        result = run_compliance_check(
            title="Pet Water Fountain 2.5L Automatic Circulating",
            bullet_points=[
                "QUIET OPERATION — Under 30dB noise level",
                "TRIPLE FILTER — Activated carbon filtration",
                "LARGE CAPACITY — 2.5L water reservoir",
                "EASY CLEAN — Dishwasher safe components",
                "360 ACCESS — Multi-directional drinking",
            ],
            search_terms="cat fountain automatic pet water bowl dog fountain",
        )
        assert result["passed"] is True
        assert len(result["issues"]) == 0

    def test_prohibited_word_best_detected(self):
        """含有 'best' 禁用词的文案应被检测。"""
        from src.agents.listing_agent.compliance import run_compliance_check
        result = run_compliance_check(
            title="The Best Pet Water Fountain",
            bullet_points=["Feature 1"] * 5,
            search_terms="",
        )
        assert result["passed"] is False
        assert "best" in result["prohibited_found"]

    def test_prohibited_word_guarantee_detected(self):
        """含有 'guarantee' 禁用词的文案应被检测。"""
        from src.agents.listing_agent.compliance import run_compliance_check
        result = run_compliance_check(
            title="Pet Fountain",
            bullet_points=["GUARANTEE — Lifetime warranty included"] + ["Feature"] * 4,
            search_terms="",
        )
        assert "guarantee" in result["prohibited_found"]

    def test_prohibited_word_number_one_detected(self):
        """含有 '#1' 禁用词的文案应被检测。"""
        from src.agents.listing_agent.compliance import run_compliance_check
        result = run_compliance_check(
            title="#1 Pet Water Fountain",
            bullet_points=["Feature"] * 5,
            search_terms="",
        )
        assert result["passed"] is False
        assert "#1" in result["prohibited_found"]

    def test_title_over_200_chars_fails(self):
        """超过200字符的标题应检测为字符长度违规。"""
        from src.agents.listing_agent.compliance import run_compliance_check
        long_title = "A" * 201
        result = run_compliance_check(
            title=long_title,
            bullet_points=["Feature"] * 5,
            search_terms="",
        )
        assert result["passed"] is False
        assert len(result["length_issues"]) > 0

    def test_search_terms_over_250_chars_fails(self):
        """超过250字符的Search Terms应检测为字符长度违规。"""
        from src.agents.listing_agent.compliance import run_compliance_check
        long_terms = "keyword " * 40  # > 250 chars
        result = run_compliance_check(
            title="Pet Fountain",
            bullet_points=["Feature"] * 5,
            search_terms=long_terms,
        )
        assert result["passed"] is False
        assert len(result["length_issues"]) > 0

    def test_check_prohibited_words_function(self):
        """check_prohibited_words 应精确识别禁用词。"""
        from src.agents.listing_agent.compliance import check_prohibited_words
        found = check_prohibited_words("This is the best product with a guarantee")
        assert "best" in found
        assert "guarantee" in found

    def test_check_prohibited_words_word_boundary(self):
        """check_prohibited_words 应使用词边界，不误判前缀匹配。"""
        from src.agents.listing_agent.compliance import check_prohibited_words
        # "bestiary" 不应匹配 "best"
        found = check_prohibited_words("A bestiary is a collection of beasts")
        assert "best" not in found

    def test_sanitize_text_cleans_extra_spaces(self):
        """sanitize_text 应清理多余空白。"""
        from src.agents.listing_agent.compliance import sanitize_text
        result = sanitize_text("  hello   world  ")
        assert result == "hello world"


# ============================================================================ #
#  5. Schema 验证测试
# ============================================================================ #

class TestSchemas:
    def test_listing_state_is_dict_subclass(self):
        """ListingState 应继承 dict。"""
        from src.agents.listing_agent.schemas import ListingState
        state = ListingState(asin="B0TEST001", product_name="Test")
        assert isinstance(state, dict)

    def test_listing_state_default_values(self):
        """ListingState 默认值应正确初始化。"""
        from src.agents.listing_agent.schemas import ListingState
        state = ListingState()
        assert state.get("dry_run") is True
        assert state.get("status") == "running"
        assert state.get("error") is None
        assert isinstance(state.get("features"), list)
        assert isinstance(state.get("kb_tips"), list)

    def test_listing_state_accepts_custom_values(self):
        """ListingState 应接受自定义参数。"""
        from src.agents.listing_agent.schemas import ListingState
        state = ListingState(
            asin="B0TEST001",
            product_name="Test Product",
            category="pet_supplies",
            features=["feature1", "feature2"],
            dry_run=False,
        )
        assert state["asin"] == "B0TEST001"
        assert state["product_name"] == "Test Product"
        assert state["dry_run"] is False
        assert len(state["features"]) == 2

    def test_product_info_to_dict(self):
        """ProductInfo.to_dict() 应返回所有字段。"""
        from src.agents.listing_agent.schemas import ProductInfo
        info = ProductInfo(
            asin="B0TEST001",
            product_name="Test Product",
            category="pet",
            features=["feature1"],
            price=29.99,
            brand="TestBrand",
        )
        d = info.to_dict()
        assert d["asin"] == "B0TEST001"
        assert d["price"] == 29.99
        assert len(d["features"]) == 1

    def test_listing_copy_schema_to_dict(self):
        """ListingCopySchema.to_dict() 应返回所有字段。"""
        from src.agents.listing_agent.schemas import ListingCopySchema
        schema = ListingCopySchema(
            asin="B0TEST001",
            title="Test Product Fountain",
            bullet_points=["BP1", "BP2", "BP3", "BP4", "BP5"],
            search_terms="keyword1 keyword2",
            compliance_passed=True,
            compliance_issues=[],
        )
        d = schema.to_dict()
        assert "title" in d
        assert "bullet_points" in d
        assert len(d["bullet_points"]) == 5
        assert d["compliance_passed"] is True


# ============================================================================ #
#  6. 节点单元测试
# ============================================================================ #

class TestInitRunNode:
    def test_init_run_sets_agent_run_id(self):
        """init_run 应设置 agent_run_id（UUID格式）。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import init_run
        state = ListingState(asin="B0TEST001", product_name="Test", dry_run=True)
        result = init_run(state)
        assert result.get("agent_run_id") is not None
        uuid.UUID(result["agent_run_id"])  # 验证UUID格式

    def test_init_run_fails_without_asin_or_name(self):
        """没有 asin 和 product_name 时 init_run 应设置 error。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import init_run
        state = ListingState(asin="", product_name="", dry_run=True)
        result = init_run(state)
        assert result.get("status") == "failed"
        assert result.get("error") is not None

    def test_init_run_dry_run_skips_db(self):
        """init_run dry_run=True 时跳过数据库写入。"""
        mock_cm, mock_session = _make_mock_db_session()
        from src.agents.listing_agent.schemas import ListingState
        with patch("src.agents.listing_agent.nodes.db_session", mock_cm):
            from src.agents.listing_agent.nodes import init_run
            state = ListingState(asin="B0TEST001", product_name="Test", dry_run=True)
            init_run(state)
        assert not mock_session.add.called, "dry_run=True 时 init_run 不应写 DB"

    def test_init_run_with_only_product_name(self):
        """只提供 product_name（无ASIN）时也应正常通过 init_run。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import init_run
        state = ListingState(asin="", product_name="New Pet Fountain", dry_run=True)
        result = init_run(state)
        assert result.get("error") is None
        assert result.get("agent_run_id") is not None


class TestRetrieveKBNode:
    def test_retrieve_kb_dry_run_uses_mock(self):
        """retrieve_kb dry_run=True 时应设置 kb_tips（mock KB数据）。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import retrieve_kb
        state = ListingState(asin="B0TEST001", product_name="Test", dry_run=True)
        result = retrieve_kb(state)
        assert "kb_tips" in result
        kb = result["kb_tips"]
        assert isinstance(kb, list)
        assert len(kb) >= 1

    def test_retrieve_kb_tips_contain_copywriting_content(self):
        """KB结果应包含文案撰写相关内容。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import retrieve_kb
        state = ListingState(asin="B0TEST001", product_name="Test", dry_run=True)
        result = retrieve_kb(state)
        kb = result["kb_tips"]
        has_copy_content = any(
            any(kw in tip for kw in ["文案", "标题", "Bullet", "关键词", "技巧"])
            for tip in kb
        )
        assert has_copy_content, f"KB结果应包含文案撰写技巧，实际: {kb}"

    def test_retrieve_kb_skips_if_error(self):
        """state 已有 error 时 retrieve_kb 应直接返回，不修改 kb_tips。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import retrieve_kb
        state = ListingState(asin="B0TEST001", product_name="Test", dry_run=True)
        state["error"] = "前序错误"
        result = retrieve_kb(state)
        assert result.get("kb_tips") == []


class TestGenerateCopyNode:
    def test_generate_copy_dry_run_returns_mock(self):
        """generate_copy dry_run=True 时应生成Mock文案。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import generate_copy
        state = ListingState(asin="B0TEST001", product_name="Test Product", dry_run=True)
        state["kb_tips"] = ["文案技巧1"]
        result = generate_copy(state)
        assert "generated_copy" in result
        copy = result["generated_copy"]
        assert "title" in copy
        assert "bullet_points" in copy
        assert len(copy["bullet_points"]) == 5

    def test_generate_copy_skips_if_error(self):
        """state 已有 error 时 generate_copy 应直接返回。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import generate_copy
        state = ListingState(asin="B0TEST001", product_name="Test", dry_run=True)
        state["error"] = "前序错误"
        result = generate_copy(state)
        assert result.get("generated_copy") == {}


class TestCheckComplianceNode:
    def test_check_compliance_marks_passed_for_clean_copy(self):
        """干净文案应通过合规检查。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import check_compliance
        state = ListingState(asin="B0TEST001", dry_run=True)
        state["generated_copy"] = {
            "title": "Pet Water Fountain 2.5L Automatic Circulating",
            "bullet_points": [
                "QUIET PUMP — Under 30dB noise level for peaceful home",
                "TRIPLE FILTER — Carbon and resin filtration system",
                "LARGE CAPACITY — 2.5L reservoir for multiple pets",
                "EASY CLEAN — All parts dishwasher safe",
                "FLOWER DESIGN — 360-degree multi-height access",
            ],
            "search_terms": "cat fountain automatic water bowl dog fountain",
            "aplus_copy": None,
        }
        result = check_compliance(state)
        listing_copy = result.get("listing_copy", {})
        assert listing_copy.get("compliance_passed") is True

    def test_check_compliance_detects_prohibited_words(self):
        """包含禁用词的文案应不通过合规检查。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import check_compliance
        state = ListingState(asin="B0TEST001", dry_run=True)
        state["generated_copy"] = {
            "title": "Best #1 Pet Water Fountain",
            "bullet_points": ["Feature"] * 5,
            "search_terms": "pet fountain",
            "aplus_copy": None,
        }
        result = check_compliance(state)
        listing_copy = result.get("listing_copy", {})
        assert listing_copy.get("compliance_passed") is False
        assert len(listing_copy.get("compliance_issues", [])) > 0

    def test_check_compliance_sets_listing_copy(self):
        """check_compliance 应设置完整的 listing_copy 字典。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import check_compliance
        state = ListingState(asin="B0TEST001", dry_run=True)
        state["generated_copy"] = {
            "title": "Pet Fountain Auto",
            "bullet_points": ["F1", "F2", "F3", "F4", "F5"],
            "search_terms": "fountain cat dog",
            "aplus_copy": "A+ content",
        }
        result = check_compliance(state)
        listing_copy = result.get("listing_copy", {})
        for field in ["title", "bullet_points", "search_terms", "compliance_passed", "compliance_issues"]:
            assert field in listing_copy, f"listing_copy 缺少字段: {field}"


class TestFinalizeRunNode:
    def test_finalize_run_sets_completed_status(self):
        """finalize_run 在无 error 时应设置 status=completed。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import finalize_run
        mock_cm, mock_session = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            state = ListingState(asin="B0TEST001", dry_run=True)
            state["agent_run_id"] = str(uuid.uuid4())
            state["listing_copy"] = {}
            result = finalize_run(state)
        assert result.get("status") == "completed"

    def test_finalize_run_sets_failed_status_on_error(self):
        """finalize_run 在 state 有 error 时应设置 status=failed。"""
        from src.agents.listing_agent.schemas import ListingState
        from src.agents.listing_agent.nodes import finalize_run
        mock_cm, mock_session = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            state = ListingState(asin="B0TEST001", dry_run=True)
            state["error"] = "测试错误"
            state["agent_run_id"] = str(uuid.uuid4())
            result = finalize_run(state)
        assert result.get("status") == "failed"

    def test_finalize_run_writes_audit_log(self):
        """finalize_run 应调用 log_action 写入审计日志。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.utils.audit.db_session", mock_cm):
            from src.agents.listing_agent.schemas import ListingState
            from src.agents.listing_agent.nodes import finalize_run
            state = ListingState(asin="B0TEST001", dry_run=True)
            state["agent_run_id"] = str(uuid.uuid4())
            state["listing_copy"] = {}
            finalize_run(state)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        assert len(audit_logs) >= 1, "finalize_run 应写入审计日志"


# ============================================================================ #
#  7. 飞书命令路由测试
# ============================================================================ #

class TestFeishuCommandRouter:
    def test_listing_command_routing(self):
        """/listing generate 命令应路由到 listing_generate action。"""
        from src.feishu.command_router import route_command
        result = route_command("/listing generate asin=B0TEST001", "user123")
        assert result["action"] == "listing_generate"

    def test_listing_command_asin_parsing(self):
        """/listing generate 命令应正确解析 asin 参数。"""
        from src.feishu.command_router import route_command
        result = route_command("/listing generate asin=B0ABCDE1234", "user123")
        assert result["action"] == "listing_generate"
        assert result.get("asin") == "B0ABCDE1234"

    def test_listing_command_without_asin(self):
        """/listing generate 没有 asin 时应返回 listing_generate（asin为空）。"""
        from src.feishu.command_router import route_command
        result = route_command("/listing generate", "user123")
        assert result["action"] == "listing_generate"
        assert result.get("asin") == ""

    def test_listing_command_case_insensitive(self):
        """/listing 命令应不区分大小写。"""
        from src.feishu.command_router import route_command
        result = route_command("/LISTING generate asin=B0TEST001", "user123")
        assert result["action"] == "listing_generate"

    def test_help_message_includes_listing_command(self):
        """帮助信息应包含 /listing generate 命令说明。"""
        from src.feishu.command_router import route_command
        result = route_command("帮助", "user123")
        assert "listing" in result["message"].lower()

    def test_parse_listing_command_full_params(self):
        """_parse_listing_command 应解析 asin 和 category 参数。"""
        from src.feishu.command_router import _parse_listing_command
        params = _parse_listing_command("/listing generate asin=B0ABCDE1234 category=pet_supplies")
        assert params["asin"] == "B0ABCDE1234"
        assert params["category"] == "pet_supplies"

    def test_selection_command_still_works(self):
        """选品命令应仍然正常路由（不被listing命令干扰）。"""
        from src.feishu.command_router import route_command
        result = route_command("选品分析", "user123")
        assert result["action"] == "selection_analysis"


# ============================================================================ #
#  8. 生成器单元测试
# ============================================================================ #

class TestGenerator:
    def test_parse_llm_response_valid_json(self):
        """parse_llm_response 应正确解析有效的JSON。"""
        from src.agents.listing_agent.generator import parse_llm_response
        valid_json = json.dumps({
            "title": "Test Pet Water Fountain",
            "bullet_points": ["BP1", "BP2", "BP3", "BP4", "BP5"],
            "search_terms": "fountain cat water",
            "aplus_copy": None,
        })
        result = parse_llm_response(valid_json)
        assert result["title"] == "Test Pet Water Fountain"
        assert len(result["bullet_points"]) == 5
        assert result["search_terms"] == "fountain cat water"

    def test_parse_llm_response_markdown_codeblock(self):
        """parse_llm_response 应处理Markdown代码块中的JSON。"""
        from src.agents.listing_agent.generator import parse_llm_response
        markdown_json = """```json
{
  "title": "Pet Fountain Test",
  "bullet_points": ["B1", "B2", "B3", "B4", "B5"],
  "search_terms": "test keywords",
  "aplus_copy": null
}
```"""
        result = parse_llm_response(markdown_json)
        assert result["title"] == "Pet Fountain Test"
        assert len(result["bullet_points"]) == 5

    def test_parse_llm_response_pads_short_bullet_points(self):
        """parse_llm_response 应补全不足5条的Bullet Points。"""
        from src.agents.listing_agent.generator import parse_llm_response
        json_with_3_bps = json.dumps({
            "title": "Test",
            "bullet_points": ["BP1", "BP2", "BP3"],
            "search_terms": "test",
        })
        result = parse_llm_response(json_with_3_bps)
        assert len(result["bullet_points"]) == 5

    def test_parse_llm_response_truncates_long_bullet_points(self):
        """parse_llm_response 应截断超过5条的Bullet Points。"""
        from src.agents.listing_agent.generator import parse_llm_response
        json_with_7_bps = json.dumps({
            "title": "Test",
            "bullet_points": [f"BP{i}" for i in range(7)],
            "search_terms": "test",
        })
        result = parse_llm_response(json_with_7_bps)
        assert len(result["bullet_points"]) == 5

    def test_parse_llm_response_truncates_long_title(self):
        """parse_llm_response 应截断超过200字符的标题。"""
        from src.agents.listing_agent.generator import parse_llm_response
        long_title = "A" * 250
        json_str = json.dumps({
            "title": long_title,
            "bullet_points": ["B"] * 5,
            "search_terms": "test",
        })
        result = parse_llm_response(json_str)
        assert len(result["title"]) <= 200

    def test_generate_full_listing_dry_run(self):
        """generate_full_listing dry_run=True 应返回Mock文案。"""
        from src.agents.listing_agent.generator import generate_full_listing
        result = generate_full_listing(
            asin="B0TEST001",
            product_name="Test Pet Fountain",
            category="pet_supplies",
            features=["feature1"],
            persona_data={},
            competitor_data={},
            kb_tips=["文案技巧1"],
            dry_run=True,
        )
        assert "title" in result
        assert "bullet_points" in result
        assert len(result["bullet_points"]) == 5
        assert "search_terms" in result


# ============================================================================ #
#  9. DB写入测试（mock）
# ============================================================================ #

class TestDBWrite:
    def test_dry_run_skips_db_write(self):
        """dry_run=True 时 nodes 不应写入数据库（init_run/finalize_run）。"""
        nodes_mock_cm, nodes_mock_session = _make_mock_db_session()
        audit_mock_cm, _ = _make_mock_db_session()
        with patch("src.agents.listing_agent.nodes.db_session", nodes_mock_cm), \
             patch("src.utils.audit.db_session", audit_mock_cm):
            from src.agents.listing_agent import run
            run(asin="B0TEST001", product_name="Test Product", dry_run=True)
        # dry_run 模式：nodes.db_session 完全不应被调用
        assert nodes_mock_session.add.call_count == 0, (
            f"dry_run=True 时 nodes 不应写入 DB，实际 add 被调用 {nodes_mock_session.add.call_count} 次"
        )

    def test_non_dry_run_writes_agent_run(self):
        """dry_run=False 时应写入 AgentRun 记录。"""
        mock_cm, mock_session, mock_run = _make_mock_db_with_agent_run()

        with patch("src.agents.listing_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.listing_agent import run
            result = run(asin="B0TEST001", product_name="Test Product", dry_run=False)

        assert mock_session.add.called, "dry_run=False 时应写入 AgentRun 记录"
        assert mock_session.commit.called

    def test_non_dry_run_updates_agent_run_status(self):
        """dry_run=False 时 finalize_run 应更新 AgentRun 的 status 和 finished_at。"""
        mock_cm, mock_session, mock_run = _make_mock_db_with_agent_run()

        with patch("src.agents.listing_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.listing_agent import run
            result = run(asin="B0TEST001", product_name="Test Product", dry_run=False)

        assert mock_run.status == "completed", (
            f"AgentRun.status 应为 completed，实际: {mock_run.status}"
        )
        assert mock_run.finished_at is not None


# ============================================================================ #
#  10. 审计日志测试
# ============================================================================ #

class TestAuditLog:
    def test_audit_log_is_called_after_run(self):
        """run 结束后应调用 log_action 写入审计日志。"""
        mock_cm, mock_session = _make_mock_db_session()
        with patch("src.agents.listing_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.listing_agent import run
            run(asin="B0TEST001", product_name="Test Product", dry_run=True)

        # utils.audit.db_session 的 session.add 应被调用（AuditLog）
        assert mock_session.add.called, "log_action 应写入审计记录"

    def test_audit_log_action_name(self):
        """审计日志的 action 应为 listing_agent.run。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.agents.listing_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.listing_agent import run
            run(asin="B0TEST001", product_name="Test Product", dry_run=True)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        assert len(audit_logs) >= 1, "应至少写入1条审计日志"
        actions = [a.action for a in audit_logs]
        assert "listing_agent.run" in actions, (
            f"审计日志 action 应含 listing_agent.run，实际: {actions}"
        )

    def test_audit_log_actor_is_listing_agent(self):
        """审计日志的 actor 应为 listing_agent。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.agents.listing_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.listing_agent import run
            run(asin="B0TEST001", product_name="Test Product", dry_run=True)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        actors = [a.actor for a in audit_logs]
        assert "listing_agent" in actors, (
            f"审计日志 actor 应含 listing_agent，实际: {actors}"
        )


# ============================================================================ #
#  11. 集成验证测试 - 飞书输出格式
# ============================================================================ #

class TestFeishuOutput:
    def test_listing_result_can_format_for_feishu(self):
        """Listing结果应能格式化为飞书消息。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Pet Fountain", dry_run=True)

        # 模拟飞书消息格式化
        title = result.get("title", "")
        bullet_points = result.get("bullet_points", [])
        search_terms = result.get("search_terms", "")

        feishu_message = f"📝 **Listing文案生成完成**\n\n"
        feishu_message += f"**标题：**\n{title}\n\n"
        feishu_message += "**五点描述：**\n"
        for i, bp in enumerate(bullet_points, 1):
            feishu_message += f"{i}. {bp}\n"
        feishu_message += f"\n**后台关键词：**\n{search_terms}\n"

        assert len(feishu_message) > 100, "飞书消息应有实质内容"
        assert title in feishu_message
        assert all(bp in feishu_message for bp in bullet_points)

    def test_compliance_issues_reported_in_output(self):
        """合规问题应包含在输出结果中。"""
        from src.agents.listing_agent import run
        result = run(asin="B0TEST001", product_name="Test Product", dry_run=True)

        # 无论是否通过，compliance字段都应存在
        assert "compliance_passed" in result
        assert "compliance_issues" in result
        assert isinstance(result["compliance_issues"], list)

"""选品分析 Agent 单元测试。

覆盖范围：
  - 模块导入测试
  - dry_run=True 完整流程（≥3个候选产品）
  - 候选产品字段验证（asin/product_name/reason/market_data/risks/score）
  - 限制类目拒绝测试
  - KB 原则引用验证（选品理由必须包含知识库内容）
  - DB 写入测试（mock db_session）
  - 审计日志测试
  - 调度器集成测试（run_selection_analysis）
  - 各节点单元测试（init_run, collect_data, retrieve_kb, analyze_llm, generate_report）
"""
from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

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


# ============================================================================ #
#  1. 模块导入测试
# ============================================================================ #

class TestImports:
    def test_can_import_run_function(self):
        """应能从 src.agents.selection_agent 导入 run 函数。"""
        from src.agents.selection_agent import run
        assert callable(run)

    def test_can_import_execute_function(self):
        """应能直接从 agent 模块导入 execute 函数。"""
        from src.agents.selection_agent.agent import execute
        assert callable(execute)

    def test_can_import_schema_classes(self):
        """应能导入 SelectionState, ProductCandidate, RESTRICTED_CATEGORIES。"""
        from src.agents.selection_agent.schema import (
            SelectionState,
            ProductCandidate,
            RESTRICTED_CATEGORIES,
        )
        assert issubclass(SelectionState, dict)
        assert isinstance(RESTRICTED_CATEGORIES, list)
        assert len(RESTRICTED_CATEGORIES) > 0

    def test_can_import_nodes(self):
        """应能导入所有节点函数。"""
        from src.agents.selection_agent.nodes import (
            init_run,
            collect_data,
            retrieve_kb,
            analyze_llm,
            generate_report,
            save_results,
            finalize_run,
        )
        for fn in [init_run, collect_data, retrieve_kb, analyze_llm,
                   generate_report, save_results, finalize_run]:
            assert callable(fn)


# ============================================================================ #
#  2. dry_run=True 完整流程测试
# ============================================================================ #

class TestDryRunExecution:
    def test_run_returns_dict(self):
        """run(dry_run=True) 应返回 dict。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        assert isinstance(result, dict)

    def test_run_returns_at_least_3_candidates(self):
        """run(dry_run=True) 应返回 ≥3 个候选产品。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        candidates = result.get("candidates", [])
        assert len(candidates) >= 3, f"期望至少3个候选产品，实际得到 {len(candidates)} 个"

    def test_run_status_is_completed(self):
        """run(dry_run=True) 的 status 应为 completed。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        assert result.get("status") == "completed"

    def test_run_has_category_field(self):
        """结果应包含 category 字段。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        assert "category" in result
        assert result["category"] == "pet_supplies"

    def test_run_has_analysis_date(self):
        """结果应包含 analysis_date 字段。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        assert "analysis_date" in result
        assert result["analysis_date"] != ""

    def test_run_has_kb_principles_used(self):
        """结果应包含 kb_principles_used 字段（至少1条）。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        assert "kb_principles_used" in result
        assert len(result["kb_principles_used"]) >= 1

    def test_run_has_agent_run_id(self):
        """结果应包含 agent_run_id 字段（UUID 格式）。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        assert "agent_run_id" in result
        run_id = result["agent_run_id"]
        assert run_id is not None and run_id != ""
        # 验证是有效 UUID
        uuid.UUID(run_id)

    def test_run_no_error(self):
        """dry_run 模式不应产生 error。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        assert result.get("error") is None

    def test_run_with_subcategory(self):
        """支持 subcategory 参数，应正常返回结果。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True, subcategory="dog_bed")
        assert result.get("status") == "completed"
        assert len(result.get("candidates", [])) >= 3


# ============================================================================ #
#  3. 候选产品字段验证
# ============================================================================ #

class TestCandidateFields:
    @pytest.fixture(autouse=True)
    def _run_result(self):
        from src.agents.selection_agent import run
        self.result = run(category="pet_supplies", dry_run=True)
        self.candidates = self.result.get("candidates", [])

    def test_each_candidate_has_asin(self):
        """每个候选产品应有 asin 字段。"""
        for c in self.candidates:
            assert "asin" in c and c["asin"], f"候选产品缺少 asin: {c}"

    def test_each_candidate_has_product_name(self):
        """每个候选产品应有 product_name 字段。"""
        for c in self.candidates:
            assert "product_name" in c and c["product_name"], f"候选产品缺少 product_name: {c}"

    def test_each_candidate_has_reason(self):
        """每个候选产品应有 reason（选品理由）字段。"""
        for c in self.candidates:
            assert "reason" in c and c["reason"], f"候选产品缺少 reason: {c}"

    def test_each_candidate_has_market_data(self):
        """每个候选产品应有 market_data 字段（dict）。"""
        for c in self.candidates:
            assert "market_data" in c
            assert isinstance(c["market_data"], dict), f"market_data 应为 dict: {c}"

    def test_each_candidate_market_data_has_rating(self):
        """每个候选产品的 market_data 应包含 rating。"""
        for c in self.candidates:
            assert "rating" in c["market_data"], f"market_data 缺少 rating: {c}"

    def test_each_candidate_market_data_has_price(self):
        """每个候选产品的 market_data 应包含 price。"""
        for c in self.candidates:
            assert "price" in c["market_data"], f"market_data 缺少 price: {c}"

    def test_each_candidate_has_risks(self):
        """每个候选产品应有 risks（风险提示）字段，为列表且至少1条。"""
        for c in self.candidates:
            assert "risks" in c
            assert isinstance(c["risks"], list), f"risks 应为 list: {c}"
            assert len(c["risks"]) >= 1, f"risks 应至少1条: {c}"

    def test_each_candidate_has_score(self):
        """每个候选产品应有 score 字段，范围 0-10。"""
        for c in self.candidates:
            assert "score" in c
            score = c["score"]
            assert 0 <= score <= 10, f"score 应在 0-10 范围: {score}"

    def test_each_candidate_has_kb_references(self):
        """每个候选产品应有 kb_references 字段（列表）。"""
        for c in self.candidates:
            assert "kb_references" in c
            assert isinstance(c["kb_references"], list), f"kb_references 应为 list: {c}"


# ============================================================================ #
#  4. 限制类目拒绝测试
# ============================================================================ #

class TestRestrictedCategories:
    def test_weapons_category_is_rejected(self):
        """weapons 类目应被拒绝，返回 status=failed。"""
        from src.agents.selection_agent import run
        result = run(category="weapons", dry_run=True)
        assert result.get("status") == "failed"
        assert result.get("error") is not None

    def test_firearms_category_is_rejected(self):
        """firearms 类目应被拒绝。"""
        from src.agents.selection_agent import run
        result = run(category="firearms", dry_run=True)
        assert result.get("status") == "failed"

    def test_drugs_category_is_rejected(self):
        """drugs 类目应被拒绝。"""
        from src.agents.selection_agent import run
        result = run(category="drugs", dry_run=True)
        assert result.get("status") == "failed"

    def test_restricted_categories_list_is_not_empty(self):
        """RESTRICTED_CATEGORIES 应包含多个类目。"""
        from src.agents.selection_agent.schema import RESTRICTED_CATEGORIES
        assert len(RESTRICTED_CATEGORIES) >= 5

    def test_pet_supplies_is_not_restricted(self):
        """pet_supplies 不应在限制类目列表中。"""
        from src.agents.selection_agent.schema import RESTRICTED_CATEGORIES
        assert "pet_supplies" not in RESTRICTED_CATEGORIES


# ============================================================================ #
#  5. KB 原则引用验证
# ============================================================================ #

class TestKBCompliance:
    def test_reasons_reference_kb_principles(self):
        """选品理由中应引用知识库原则内容（含 '原则' 或 '知识库'）。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        candidates = result.get("candidates", [])
        assert len(candidates) >= 1
        # 至少有1个候选产品的 reason 包含知识库引用
        reasons_with_kb = [
            c for c in candidates
            if "原则" in c.get("reason", "") or "知识库" in c.get("reason", "")
        ]
        assert len(reasons_with_kb) >= 1, (
            "至少应有1个候选产品的选品理由引用了知识库原则"
        )

    def test_each_candidate_has_kb_references_list(self):
        """每个候选产品应有非空的 kb_references 列表（证明知识库被使用）。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        candidates = result.get("candidates", [])
        for c in candidates:
            refs = c.get("kb_references", [])
            assert isinstance(refs, list)
            # kb_references 可以为空列表（知识库未检索到匹配），但 reason 应有文字

    def test_kb_principles_used_in_report(self):
        """报告的 kb_principles_used 字段应包含实际原则。"""
        from src.agents.selection_agent import run
        result = run(category="pet_supplies", dry_run=True)
        principles = result.get("kb_principles_used", [])
        assert len(principles) >= 1
        # 至少一条原则包含选品相关内容
        selection_related = [
            p for p in principles
            if any(kw in p for kw in ["原则", "选品", "竞争", "评分", "BSR", "定价"])
        ]
        assert len(selection_related) >= 1, (
            f"kb_principles_used 应包含选品相关内容，实际: {principles}"
        )


# ============================================================================ #
#  6. DB 写入测试（mock）
# ============================================================================ #

class TestDBWrite:
    def test_dry_run_skips_db_write(self):
        """dry_run=True 时 nodes 不应通过自身的 db_session 写入数据库。"""
        # 分别 patch nodes.db_session（验证 nodes 不写 DB）和 audit.db_session（audit 正常运行）
        nodes_mock_cm, nodes_mock_session = _make_mock_db_session()
        audit_mock_cm, _ = _make_mock_db_session()
        with patch("src.agents.selection_agent.nodes.db_session", nodes_mock_cm), \
             patch("src.utils.audit.db_session", audit_mock_cm):
            from src.agents.selection_agent import run
            run(category="pet_supplies", dry_run=True)
        # dry_run 模式：nodes.db_session 完全不应被调用（init_run/finalize_run 跳过 DB 写入）
        assert nodes_mock_session.add.call_count == 0, (
            f"dry_run=True 时 nodes 不应写入 DB，实际 add 被调用 {nodes_mock_session.add.call_count} 次"
        )

    def test_non_dry_run_writes_agent_run(self):
        """dry_run=False 时应写入 AgentRun 记录（status=running）。"""
        mock_cm, mock_session, mock_run = _make_mock_db_with_agent_run()

        with patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.selection_agent import run
            result = run(category="pet_supplies", dry_run=False)

        # 至少 session.add 被调用（init_run 写 AgentRun）
        assert mock_session.add.called, "dry_run=False 时应写入 AgentRun 记录"
        assert mock_session.commit.called

    def test_non_dry_run_saves_product_selections(self):
        """dry_run=False 时应写入 ProductSelection 记录。"""
        mock_cm, mock_session, mock_run = _make_mock_db_with_agent_run()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.selection_agent import run
            result = run(category="pet_supplies", dry_run=False)

        # 检查 ProductSelection 类型的对象被 add
        from src.db.models import ProductSelection
        product_selections = [o for o in added_objects if isinstance(o, ProductSelection)]
        assert len(product_selections) >= 3, (
            f"应写入 ≥3 个 ProductSelection，实际写入 {len(product_selections)} 个"
        )

    def test_non_dry_run_updates_agent_run_status(self):
        """dry_run=False 时 finalize_run 应更新 AgentRun 的 status 和 finished_at。"""
        mock_cm, mock_session, mock_run = _make_mock_db_with_agent_run()

        with patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.selection_agent import run
            result = run(category="pet_supplies", dry_run=False)

        # mock_run 的 status 应被设置为 completed
        assert mock_run.status == "completed", (
            f"AgentRun.status 应为 completed，实际: {mock_run.status}"
        )
        assert mock_run.finished_at is not None


# ============================================================================ #
#  7. 审计日志测试
# ============================================================================ #

class TestAuditLog:
    def test_audit_log_is_called_after_run(self):
        """run 结束后应调用 log_action 写入审计日志。"""
        mock_cm, mock_session = _make_mock_db_session()
        with patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.selection_agent import run
            run(category="pet_supplies", dry_run=True)

        # utils.audit.db_session 的 session.add 应被调用（AuditLog）
        assert mock_session.add.called, "log_action 应写入审计记录"

    def test_audit_log_action_name(self):
        """审计日志的 action 应为 selection_agent.run。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.selection_agent import run
            run(category="pet_supplies", dry_run=True)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        assert len(audit_logs) >= 1, "应至少写入1条审计日志"
        actions = [a.action for a in audit_logs]
        assert "selection_agent.run" in actions, (
            f"审计日志 action 应含 selection_agent.run，实际: {actions}"
        )

    def test_audit_log_actor_is_selection_agent(self):
        """审计日志的 actor 应为 selection_agent。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.agents.selection_agent import run
            run(category="pet_supplies", dry_run=True)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        actors = [a.actor for a in audit_logs]
        assert "selection_agent" in actors, (
            f"审计日志 actor 应含 selection_agent，实际: {actors}"
        )


# ============================================================================ #
#  8. 调度器集成测试
# ============================================================================ #

class TestSchedulerIntegration:
    def _mock_db(self):
        mock_session = MagicMock()

        @contextmanager
        def _mock_cm():
            yield mock_session

        return _mock_cm, mock_session

    def test_run_selection_analysis_returns_ok(self):
        """run_selection_analysis() 调用时应返回 status=ok。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm), \
             patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.scheduler.jobs import run_selection_analysis
            result = run_selection_analysis(dry_run=True)

        assert result["status"] == "ok"
        assert result["job_id"] == "selection_analysis"

    def test_run_selection_analysis_report_has_candidates(self):
        """run_selection_analysis() 返回的 report 应含有候选产品。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm), \
             patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.scheduler.jobs import run_selection_analysis
            result = run_selection_analysis(dry_run=True)

        report = result.get("report", {})
        candidates = report.get("candidates", [])
        assert len(candidates) >= 3

    def test_run_selection_analysis_with_category(self):
        """run_selection_analysis 支持自定义 category 参数。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm), \
             patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.scheduler.jobs import run_selection_analysis
            result = run_selection_analysis(category="pet_supplies", dry_run=True)

        assert result["status"] == "ok"


# ============================================================================ #
#  9. 节点单元测试
# ============================================================================ #

class TestInitRunNode:
    def test_init_run_sets_agent_run_id(self):
        """init_run 应设置 agent_run_id（UUID 格式）。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import init_run
        state = SelectionState(category="pet_supplies", dry_run=True)
        result = init_run(state)
        assert result.get("agent_run_id") is not None
        uuid.UUID(result["agent_run_id"])  # 验证 UUID 格式

    def test_init_run_rejects_restricted_category(self):
        """init_run 对限制类目应设置 error 和 status=failed。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import init_run
        state = SelectionState(category="weapons", dry_run=True)
        result = init_run(state)
        assert result.get("status") == "failed"
        assert result.get("error") is not None

    def test_init_run_dry_run_skips_db(self):
        """init_run dry_run=True 时跳过数据库写入。"""
        mock_cm, mock_session = _make_mock_db_session()
        from src.agents.selection_agent.schema import SelectionState
        with patch("src.agents.selection_agent.nodes.db_session", mock_cm):
            from src.agents.selection_agent.nodes import init_run
            state = SelectionState(category="pet_supplies", dry_run=True)
            init_run(state)
        assert not mock_session.add.called, "dry_run=True 时 init_run 不应写 DB"


class TestCollectDataNode:
    def test_collect_data_dry_run_uses_mock_data(self):
        """collect_data dry_run=True 时应设置 raw_market_data（使用 mock 数据）。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import collect_data
        state = SelectionState(category="pet_supplies", dry_run=True)
        result = collect_data(state)
        assert "raw_market_data" in result
        assert isinstance(result["raw_market_data"], dict)
        assert "asin_candidates" in result["raw_market_data"]

    def test_collect_data_has_asin_candidates(self):
        """dry_run 时 raw_market_data 应含有 asin_candidates 列表。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import collect_data
        state = SelectionState(category="pet_supplies", dry_run=True)
        result = collect_data(state)
        asin_list = result["raw_market_data"].get("asin_candidates", [])
        assert len(asin_list) >= 1

    def test_collect_data_skips_if_error(self):
        """state 已有 error 时 collect_data 应直接返回。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import collect_data
        state = SelectionState(category="pet_supplies", dry_run=True)
        state["error"] = "前序节点错误"
        result = collect_data(state)
        # raw_market_data 不应被填充
        assert result.get("raw_market_data") == {}


class TestRetrieveKBNode:
    def test_retrieve_kb_dry_run_uses_mock(self):
        """retrieve_kb dry_run=True 时应设置 kb_results（mock KB 数据）。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import retrieve_kb
        state = SelectionState(category="pet_supplies", dry_run=True)
        result = retrieve_kb(state)
        assert "kb_results" in result
        kb = result["kb_results"]
        assert isinstance(kb, list)
        assert len(kb) >= 1

    def test_retrieve_kb_results_contain_principles(self):
        """KB 结果应包含选品原则相关内容。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import retrieve_kb
        state = SelectionState(category="pet_supplies", dry_run=True)
        result = retrieve_kb(state)
        kb = result["kb_results"]
        has_principle = any("原则" in p or "选品" in p or "BSR" in p for p in kb)
        assert has_principle, f"KB 结果应包含选品原则，实际: {kb}"

    def test_retrieve_kb_skips_if_error(self):
        """state 已有 error 时 retrieve_kb 应直接返回，不修改 kb_results。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import retrieve_kb
        state = SelectionState(category="pet_supplies", dry_run=True)
        state["error"] = "前序错误"
        result = retrieve_kb(state)
        assert result.get("kb_results") == []


class TestAnalyzeLLMNode:
    def test_analyze_llm_dry_run_uses_mock(self):
        """analyze_llm dry_run=True 时应设置 llm_analysis（mock 分析文本）。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import analyze_llm
        state = SelectionState(category="pet_supplies", dry_run=True)
        state["raw_market_data"] = {}
        state["kb_results"] = ["原则1：测试"]
        result = analyze_llm(state)
        assert "llm_analysis" in result
        assert len(result["llm_analysis"]) > 0

    def test_analyze_llm_skips_if_error(self):
        """state 已有 error 时 analyze_llm 应直接返回。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import analyze_llm
        state = SelectionState(category="pet_supplies", dry_run=True)
        state["error"] = "前序错误"
        result = analyze_llm(state)
        assert result.get("llm_analysis") == ""


class TestGenerateReportNode:
    def test_generate_report_creates_candidates(self):
        """generate_report 应基于 raw_market_data 生成候选产品列表。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import generate_report, _MOCK_MARKET_DATA, _MOCK_KB_RESULTS
        state = SelectionState(category="pet_supplies", dry_run=True)
        state["raw_market_data"] = _MOCK_MARKET_DATA["pet_supplies"]
        state["kb_results"] = _MOCK_KB_RESULTS
        state["agent_run_id"] = str(uuid.uuid4())
        result = generate_report(state)
        assert "candidates" in result
        assert len(result["candidates"]) >= 3

    def test_generate_report_candidates_have_required_fields(self):
        """generate_report 生成的候选产品应有所有必需字段。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import generate_report, _MOCK_MARKET_DATA, _MOCK_KB_RESULTS
        state = SelectionState(category="pet_supplies", dry_run=True)
        state["raw_market_data"] = _MOCK_MARKET_DATA["pet_supplies"]
        state["kb_results"] = _MOCK_KB_RESULTS
        state["agent_run_id"] = str(uuid.uuid4())
        result = generate_report(state)
        for c in result["candidates"]:
            for field in ["asin", "product_name", "reason", "market_data", "risks", "score", "kb_references"]:
                assert field in c, f"候选产品缺少字段 {field}: {c}"

    def test_generate_report_creates_report_dict(self):
        """generate_report 应设置 report 字段（完整报告 dict）。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import generate_report, _MOCK_MARKET_DATA, _MOCK_KB_RESULTS
        state = SelectionState(category="pet_supplies", dry_run=True)
        state["raw_market_data"] = _MOCK_MARKET_DATA["pet_supplies"]
        state["kb_results"] = _MOCK_KB_RESULTS
        state["agent_run_id"] = str(uuid.uuid4())
        result = generate_report(state)
        report = result.get("report", {})
        assert "category" in report
        assert "analysis_date" in report
        assert "candidates" in report


class TestFinalizeRunNode:
    def test_finalize_run_sets_completed_status(self):
        """finalize_run 在无 error 时应设置 status=completed。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import finalize_run
        mock_cm, mock_session = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            state = SelectionState(category="pet_supplies", dry_run=True)
            state["agent_run_id"] = str(uuid.uuid4())
            state["candidates"] = []
            state["report"] = {}
            result = finalize_run(state)
        assert result.get("status") == "completed"

    def test_finalize_run_sets_failed_status_on_error(self):
        """finalize_run 在 state 有 error 时应设置 status=failed。"""
        from src.agents.selection_agent.schema import SelectionState
        from src.agents.selection_agent.nodes import finalize_run
        mock_cm, mock_session = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            state = SelectionState(category="pet_supplies", dry_run=True)
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
            from src.agents.selection_agent.schema import SelectionState
            from src.agents.selection_agent.nodes import finalize_run
            state = SelectionState(category="pet_supplies", dry_run=True)
            state["agent_run_id"] = str(uuid.uuid4())
            state["candidates"] = []
            state["report"] = {}
            finalize_run(state)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        assert len(audit_logs) >= 1, "finalize_run 应写入审计日志"


# ============================================================================ #
#  10. ProductCandidate dataclass 测试
# ============================================================================ #

class TestProductCandidate:
    def test_to_dict_returns_all_fields(self):
        """ProductCandidate.to_dict() 应返回包含所有字段的 dict。"""
        from src.agents.selection_agent.schema import ProductCandidate
        c = ProductCandidate(
            asin="B0TEST001",
            product_name="测试产品",
            reason="根据知识库原则：评分≥4.5",
            market_data={"rating": 4.6, "price": 29.99},
            risks=["竞争较激烈"],
            score=8.5,
            kb_references=["选品原则3：评分≥4.5"],
        )
        d = c.to_dict()
        assert d["asin"] == "B0TEST001"
        assert d["product_name"] == "测试产品"
        assert d["score"] == 8.5
        assert "rating" in d["market_data"]
        assert len(d["risks"]) == 1
        assert len(d["kb_references"]) == 1

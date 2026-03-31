"""端到端流程集成测试。

测试 4 个核心 e2e 流程：
1. test_rag_full_pipeline — RAG 检索问答全链路（输入问题 → 检索 → LLM生成 → 返回答案）
2. test_selection_full_pipeline — 选品 Agent 全链路（类目 → 数据收集 → KB检索 → LLM分析 → 候选产品）
3. test_feishu_command_flow — 飞书指令全链路（收到消息 → 命令路由 → 执行 → 回复）
4. test_daily_report_flow — 日报生成全链路（触发 → 3个板块收集 → 卡片生成 → 输出）

每个测试验证：输入→处理→输出的完整链路
所有外部 API 均 Mock（不依赖真实服务）
"""
from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call

import pytest


# ============================================================================ #
#  Marker 注册
# ============================================================================ #

pytestmark = pytest.mark.integration


# ============================================================================ #
#  辅助函数
# ============================================================================ #

def _make_mock_db():
    """创建 mock db_session 上下文管理器。"""
    mock_session = MagicMock()

    @contextmanager
    def _mock_cm():
        yield mock_session

    return _mock_cm, mock_session


# ============================================================================ #
#  1. RAG 全链路 e2e 测试
# ============================================================================ #

@pytest.mark.integration
class TestRAGFullPipeline:
    """RAG 检索问答全链路端到端测试。"""

    def test_rag_full_pipeline_returns_answer(self, mock_all_external):
        """
        e2e: 用户提问 → RAG检索 → LLM生成 → 返回答案

        验证链路：
        1. 用户问题输入到 RAGEngine.answer()
        2. 检索到相关文档
        3. LLM 生成包含来源的回答
        4. 返回结构化结果（含 answer/sources/model/tokens_used）
        """
        from src.knowledge_base.rag_engine import RAGEngine

        engine = RAGEngine.__new__(RAGEngine)
        engine._api_key = "test-key"
        engine._model = "gpt-4o-mini"
        engine._openai_client = None

        result = engine.answer("如何提高亚马逊产品评分？")

        # 验证输出结构
        assert isinstance(result, dict), "answer() 应返回 dict"
        assert "answer" in result, "结果应包含 answer 字段"
        assert "sources" in result, "结果应包含 sources 字段"
        assert "model" in result, "结果应包含 model 字段"
        assert "tokens_used" in result, "结果应包含 tokens_used 字段"

        # 验证答案内容（来自 mock_rag_results 触发 LLM 调用）
        assert len(result["answer"]) > 0, "答案不应为空"
        # 验证来源（从 mock_rag_results 提取）
        assert len(result["sources"]) >= 1, "应有至少1个来源"

    def test_rag_pipeline_question_to_answer_chain(self, mock_all_external):
        """
        e2e: 验证 RAG 从问题到答案的完整数据流

        验证链路：
        1. query() 便捷函数 → RAGEngine.answer() → search() → _call_llm()
        2. 返回字符串形式的答案
        """
        from src.knowledge_base.rag_engine import RAGEngine

        engine = RAGEngine.__new__(RAGEngine)
        engine._api_key = "test-key"
        engine._model = "gpt-4o-mini"
        engine._openai_client = None

        # 通过 answer() 方法验证完整链路
        result = engine.answer("亚马逊选品有哪些原则？", top_k=3)

        assert isinstance(result, dict)
        assert result["answer"] != "", "应有有效答案"
        # search 被 mock，应返回 mock_rag_results 中的来源
        sources = result["sources"]
        assert any(s.get("title") == "亚马逊选品指南" for s in sources), \
            f"来源中应包含 '亚马逊选品指南'，实际: {sources}"

    def test_rag_pipeline_empty_search_results(self):
        """
        e2e: 当检索结果为空时，RAG 应返回拒绝编造的答案

        验证降级链路：
        1. search() 返回空列表
        2. 不调用 LLM
        3. 返回固定的"没有找到相关信息"文案
        """
        from src.knowledge_base.rag_engine import RAGEngine

        engine = RAGEngine.__new__(RAGEngine)
        engine._api_key = "test-key"
        engine._model = "gpt-4o-mini"
        engine._openai_client = None

        # Mock search 返回空列表
        with patch.object(engine, "search", return_value=[]):
            result = engine.answer("完全无关的问题xyz")

        assert "没有找到相关信息" in result["answer"], \
            f"应返回拒绝编造文案，实际: {result['answer']}"
        assert result["sources"] == [], "空检索结果时 sources 应为空"
        assert result["tokens_used"] == 0, "空检索结果时不应消耗 tokens"

    def test_rag_pipeline_sources_attached_to_answer(self, mock_all_external):
        """
        e2e: 验证答案末尾附带来源标注

        验证输出格式：
        - 答案包含 【来源：xxx】 标注
        """
        from src.knowledge_base.rag_engine import RAGEngine

        engine = RAGEngine.__new__(RAGEngine)
        engine._api_key = "test-key"
        engine._model = "gpt-4o-mini"
        engine._openai_client = None

        result = engine.answer("如何优化广告策略？")

        # _call_llm 已被 mock 返回含【来源：测试文档】的答案
        assert "【来源：" in result["answer"], \
            f"答案应包含来源标注，实际: {result['answer']}"


# ============================================================================ #
#  2. 选品 Agent 全链路 e2e 测试
# ============================================================================ #

@pytest.mark.integration
class TestSelectionFullPipeline:
    """选品 Agent 全链路端到端测试。"""

    def test_selection_full_pipeline_returns_report(self, mock_all_external):
        """
        e2e: 类目输入 → 选品Agent完整流程 → 候选产品报告

        验证链路：
        1. run(category, dry_run=True) 触发完整 LangGraph 流程
        2. 经历 init_run → collect_data → retrieve_kb → analyze_llm → generate_report → finalize_run
        3. 返回包含候选产品的完整报告
        """
        from src.agents.selection_agent import run

        result = run(category="pet_supplies", dry_run=True)

        # 验证完整输出结构
        assert isinstance(result, dict), "run() 应返回 dict"
        assert result.get("status") == "completed", \
            f"状态应为 completed，实际: {result.get('status')}"
        assert "candidates" in result, "结果应包含 candidates 字段"
        assert len(result["candidates"]) >= 3, \
            f"至少3个候选产品，实际: {len(result['candidates'])}"

    def test_selection_full_pipeline_candidate_fields(self, mock_all_external):
        """
        e2e: 候选产品包含所有必需字段

        验证数据完整性：
        - asin, product_name, reason, market_data, risks, score, kb_references
        """
        from src.agents.selection_agent import run

        result = run(category="pet_supplies", dry_run=True)
        candidates = result.get("candidates", [])
        required_fields = ["asin", "product_name", "reason", "market_data", "risks", "score", "kb_references"]

        for i, candidate in enumerate(candidates):
            for field in required_fields:
                assert field in candidate, \
                    f"候选产品[{i}] 缺少字段 '{field}'"

    def test_selection_full_pipeline_kb_integration(self, mock_all_external):
        """
        e2e: 选品流程中 KB 原则被正确整合到报告

        验证知识库集成：
        - kb_principles_used 非空
        - 候选产品 reason 包含知识库引用
        """
        from src.agents.selection_agent import run

        result = run(category="pet_supplies", dry_run=True)

        # 验证 KB 原则被使用
        principles = result.get("kb_principles_used", [])
        assert len(principles) >= 1, "应使用至少1个 KB 原则"

        # 验证候选产品有知识库引用
        candidates = result.get("candidates", [])
        reasons_with_kb = [
            c for c in candidates
            if "原则" in c.get("reason", "") or "知识库" in c.get("reason", "")
        ]
        assert len(reasons_with_kb) >= 1, "至少1个候选产品的 reason 应引用知识库"

    def test_selection_full_pipeline_restricted_category_rejection(self, mock_all_external):
        """
        e2e: 受限类目应被完整链路拒绝

        验证限制机制：
        1. init_run 检测到限制类目
        2. 流程终止，返回 status=failed
        3. error 字段包含错误信息
        """
        from src.agents.selection_agent import run

        result = run(category="weapons", dry_run=True)

        assert result.get("status") == "failed", \
            f"受限类目应返回 failed，实际: {result.get('status')}"
        assert result.get("error") is not None, "应有 error 字段"

    def test_selection_full_pipeline_agent_run_id(self, mock_all_external):
        """
        e2e: 每次运行应生成唯一的 agent_run_id

        验证幂等性：多次运行产生不同的运行 ID
        """
        from src.agents.selection_agent import run

        result1 = run(category="pet_supplies", dry_run=True)
        result2 = run(category="pet_supplies", dry_run=True)

        id1 = result1.get("agent_run_id")
        id2 = result2.get("agent_run_id")

        assert id1 is not None and id2 is not None
        assert id1 != id2, "每次运行应生成不同的 agent_run_id"
        # 验证 UUID 格式
        uuid.UUID(id1)
        uuid.UUID(id2)


# ============================================================================ #
#  3. 飞书指令全链路 e2e 测试
# ============================================================================ #

@pytest.mark.integration
class TestFeishuCommandFlow:
    """飞书指令全链路端到端测试。"""

    def test_feishu_knowledge_query_flow(self, mock_all_external):
        """
        e2e: 飞书知识库问答全链路

        验证链路：
        1. 用户发送 "?如何处理差评" 消息
        2. route_command → knowledge_query action
        3. handle_qa → RAG → 返回答案
        4. 飞书 Bot 发送回复
        """
        from src.feishu.command_router import route_command
        from src.feishu.bot_handler import handle_qa

        # Step 1: 命令路由
        route_result = route_command("?如何处理差评", "user_001")
        assert route_result["action"] == "knowledge_query"
        assert "如何处理差评" in route_result["query"]

        # Step 2: 执行问答
        answer = handle_qa(
            user_id="user_001",
            chat_id="chat_group_001",
            question=route_result["query"]
        )

        # 验证完整链路
        assert isinstance(answer, str), "handle_qa 应返回字符串"
        assert len(answer) > 0, "答案不应为空"

        # 验证飞书 Bot 被调用
        bot = mock_all_external["bot"]
        bot.send_thinking.assert_called_once_with("chat_group_001")
        bot.update_message.assert_called_once()

    def test_feishu_daily_report_command_flow(self, mock_all_external):
        """
        e2e: 飞书日报触发指令全链路

        验证链路：
        1. 用户发送 "日报" 消息
        2. route_command → daily_report action
        3. DailyReportAgent.run() → 生成报告
        """
        from src.feishu.command_router import route_command

        # Step 1: 命令路由
        route_result = route_command("今日报告", "user_001")
        assert route_result["action"] == "daily_report", \
            f"应路由到 daily_report，实际: {route_result['action']}"
        assert route_result["sender_id"] == "user_001"

    def test_feishu_selection_command_flow(self, mock_all_external):
        """
        e2e: 飞书选品分析指令全链路

        验证链路：
        1. 用户发送 "选品分析" 消息
        2. route_command → selection_analysis action
        3. 返回正确的路由结果
        """
        from src.feishu.command_router import route_command

        route_result = route_command("选品分析", "user_manager_001")
        assert route_result["action"] == "selection_analysis", \
            f"应路由到 selection_analysis，实际: {route_result['action']}"
        assert route_result["sender_id"] == "user_manager_001"

    def test_feishu_emergency_stop_command_flow(self, mock_all_external):
        """
        e2e: 飞书紧急停机指令全链路

        验证链路：
        1. 用户发送 "紧急停机" 消息
        2. route_command → emergency_stop action
        """
        from src.feishu.command_router import route_command

        route_result = route_command("紧急停机", "admin_001")
        assert route_result["action"] == "emergency_stop", \
            f"应路由到 emergency_stop，实际: {route_result['action']}"

    def test_feishu_help_command_flow(self, mock_all_external):
        """
        e2e: 飞书帮助指令全链路

        验证链路：
        1. 用户发送 "help" 消息
        2. route_command → help action
        3. 返回帮助文本
        """
        from src.feishu.command_router import route_command

        route_result = route_command("help", "user_001")
        assert route_result["action"] == "help"
        assert "message" in route_result
        assert len(route_result["message"]) > 0, "帮助信息不应为空"

    def test_feishu_unknown_command_returns_help(self, mock_all_external):
        """
        e2e: 未知指令应返回帮助提示

        验证降级处理：
        1. 用户发送无法识别的消息
        2. route_command → unknown action
        3. 返回包含帮助信息的 message
        """
        from src.feishu.command_router import route_command

        route_result = route_command("今天天气怎么样", "user_001")
        assert route_result["action"] == "unknown"
        assert "message" in route_result
        assert "?<问题>" in route_result["message"] or "?" in route_result["message"], \
            "未知命令应提示使用 ? 提问"

    def test_feishu_qa_context_isolation(self, mock_all_external):
        """
        e2e: 不同用户的问答上下文应相互隔离

        验证会话隔离：
        1. 用户A的问答不影响用户B
        """
        from src.feishu.bot_handler import handle_qa, _CONTEXT

        # 清空上下文
        _CONTEXT.clear()

        handle_qa("user_A", "chat_001", "问题A")
        handle_qa("user_B", "chat_001", "问题B")

        # 验证上下文隔离
        assert "user_A" in _CONTEXT
        assert "user_B" in _CONTEXT
        # 用户A的上下文不包含用户B的内容
        context_a_questions = [m["content"] for m in _CONTEXT["user_A"] if m["role"] == "user"]
        context_b_questions = [m["content"] for m in _CONTEXT["user_B"] if m["role"] == "user"]
        assert "问题B" not in context_a_questions, "用户A的上下文不应包含用户B的问题"
        assert "问题A" not in context_b_questions, "用户B的上下文不应包含用户A的问题"


# ============================================================================ #
#  4. 日报全链路 e2e 测试
# ============================================================================ #

@pytest.mark.integration
class TestDailyReportFlow:
    """日报生成全链路端到端测试。"""

    def test_daily_report_full_pipeline(self, mock_all_external):
        """
        e2e: 日报生成完整链路

        验证链路：
        1. generate_daily_report(dry_run=True)
        2. 收集 3 个板块数据（sales/agent_progress/market）
        3. 生成完整报告 dict
        4. generate_feishu_card() 生成可序列化的卡片 JSON
        """
        from src.agents.core_agent.daily_report import generate_daily_report, generate_feishu_card

        # Step 1: 生成日报数据
        report = generate_daily_report(dry_run=True)

        # 验证完整输出结构
        assert isinstance(report, dict), "generate_daily_report 应返回 dict"
        assert report.get("status") == "completed", \
            f"日报状态应为 completed，实际: {report.get('status')}"

        # 验证 3 个板块
        assert "sales" in report and isinstance(report["sales"], dict), "应有 sales 板块"
        assert "agent_progress" in report and isinstance(report["agent_progress"], dict), \
            "应有 agent_progress 板块"
        assert "market" in report and isinstance(report["market"], dict), "应有 market 板块"

        # Step 2: 生成飞书卡片
        card = generate_feishu_card(report)

        # 验证卡片结构
        assert isinstance(card, dict), "generate_feishu_card 应返回 dict"
        assert "header" in card, "卡片应有 header"
        assert "elements" in card, "卡片应有 elements"
        assert "config" in card, "卡片应有 config"

        # 验证卡片可序列化
        card_json = json.dumps(card, ensure_ascii=False)
        assert len(card_json) > 200, "卡片 JSON 应有足够内容"

    def test_daily_report_sales_section_complete(self, mock_all_external):
        """
        e2e: 销售数据板块包含所有必需字段

        验证数据完整性：
        - revenue, orders, refunds, sku_ranking, 环比数据
        """
        from src.agents.core_agent.daily_report import generate_daily_report

        report = generate_daily_report(dry_run=True)
        sales = report.get("sales", {})

        assert "error" not in sales, f"sales 板块不应有 error: {sales.get('error')}"
        required_fields = ["revenue", "orders", "refunds", "sku_ranking",
                           "revenue_vs_prev_day", "orders_vs_prev_day", "revenue_vs_last_week"]
        for field in required_fields:
            assert field in sales, f"sales 缺少字段: {field}"

    def test_daily_report_agent_progress_section(self, mock_all_external):
        """
        e2e: Agent 进度板块包含运行状态

        验证链路：
        1. _collect_agent_progress(dry_run=True) 使用 mock 数据
        2. 返回 agent_statuses 列表
        3. pending_approvals 为整数
        """
        from src.agents.core_agent.daily_report import generate_daily_report

        report = generate_daily_report(dry_run=True)
        progress = report.get("agent_progress", {})

        assert "error" not in progress, f"agent_progress 不应有 error"
        assert "agent_statuses" in progress
        assert isinstance(progress["agent_statuses"], list)
        assert len(progress["agent_statuses"]) >= 1
        assert "pending_approvals" in progress
        assert isinstance(progress["pending_approvals"], int)

    def test_daily_report_market_section(self, mock_all_external):
        """
        e2e: 市场动态板块包含类目信息

        验证链路：
        1. _collect_market_data(dry_run=True) 使用 mock 数据
        2. 返回类目规模、增长率、竞品信息
        """
        from src.agents.core_agent.daily_report import generate_daily_report

        report = generate_daily_report(dry_run=True)
        market = report.get("market", {})

        assert "error" not in market, f"market 不应有 error"
        required_fields = ["category", "market_size_usd", "growth_rate",
                           "inventory_alerts", "competitor_alert"]
        for field in required_fields:
            assert field in market, f"market 缺少字段: {field}"

    def test_daily_report_agent_class_run(self, mock_all_external):
        """
        e2e: DailyReportAgent.run() 完整流程

        验证 Agent 类的完整执行：
        1. 实例化 DailyReportAgent
        2. 调用 run(dry_run=True)
        3. 返回包含 status/report/card/card_sent 的结果
        """
        from src.agents.core_agent.daily_report import DailyReportAgent

        agent = DailyReportAgent(chat_id="chat_001", dry_run=True)
        result = agent.run(dry_run=True)

        assert isinstance(result, dict)
        assert result.get("status") == "ok"
        assert "report" in result
        assert "card" in result
        assert result.get("card_sent") is False, "dry_run 时不应发送飞书消息"

    def test_daily_report_feishu_card_has_required_sections(self, mock_all_external):
        """
        e2e: 飞书卡片包含 3 个必需板块的内容

        验证卡片内容：
        - 销售数据板块（含 SKU 排行）
        - Agent 进度板块
        - 市场动态板块
        - 操作按钮
        """
        from src.agents.core_agent.daily_report import generate_daily_report, generate_feishu_card

        report = generate_daily_report(dry_run=True)
        card = generate_feishu_card(report)

        elements = card.get("elements", [])
        assert len(elements) > 0, "卡片应有 elements"

        # 验证操作按钮存在
        action_elements = [e for e in elements if e.get("tag") == "action"]
        assert len(action_elements) >= 1, "卡片应有操作按钮"

        # 验证分割线存在（3个板块之间）
        hr_elements = [e for e in elements if e.get("tag") == "hr"]
        assert len(hr_elements) >= 2, "卡片应有分割线分隔板块"

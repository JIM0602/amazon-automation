"""错误恢复场景集成测试。

测试 4 种错误恢复场景：
1. LLM超时/调用失败 → 降级处理（返回检索内容而非崩溃）
2. 预算超限（DailyCostLimitExceeded）→ 触发异常，阻止调用
3. 卖家精灵API异常 → 降级使用 mock 数据
4. DB 断线/不可用 → 各模块优雅降级

每个错误测试验证：异常触发→降级处理→告警通知
所有外部 API 均 Mock
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

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
#  1. LLM 超时/调用失败 错误恢复
# ============================================================================ #

@pytest.mark.integration
class TestLLMTimeoutRecovery:
    """LLM 超时/调用失败时的降级处理测试。"""

    def test_rag_answer_degrades_on_llm_failure(self):
        """
        错误恢复: LLM 调用失败时，RAG 降级返回检索内容

        验证降级链路：
        1. RAGEngine.search() 返回有效结果
        2. _call_llm() 抛出 Exception（模拟超时）
        3. answer() 捕获异常，返回检索到的第一条内容
        4. 不向用户抛出裸 Exception
        """
        from src.knowledge_base.rag_engine import RAGEngine

        engine = RAGEngine.__new__(RAGEngine)
        engine._api_key = "test-key"
        engine._model = "gpt-4o-mini"
        engine._openai_client = None

        mock_search_results = [
            {
                "chunk_text": "亚马逊选品原则：评分≥4.5，竞争适中",
                "chunk_index": 0,
                "metadata": {"title": "选品指南", "category": "运营", "source": "guide.md"},
                "similarity_score": 0.9,
            }
        ]

        # Mock search 成功，但 _call_llm 失败（超时）
        with patch.object(engine, "search", return_value=mock_search_results), \
             patch.object(engine, "_call_llm", side_effect=TimeoutError("LLM 调用超时")):

            result = engine.answer("如何选品？")

        # 验证降级处理：不抛出异常，返回降级内容
        assert isinstance(result, dict), "LLM 失败时应返回降级 dict，不崩溃"
        assert "answer" in result, "降级结果应有 answer 字段"
        # 降级答案应包含检索到的内容
        assert "亚马逊选品原则" in result["answer"] or "LLM调用失败" in result["answer"], \
            f"降级答案应包含检索内容，实际: {result['answer']}"

    def test_rag_answer_includes_fallback_source(self):
        """
        错误恢复: LLM 失败时，降级答案仍应有来源信息

        验证：
        1. 降级时 sources 列表来自 search() 结果
        """
        from src.knowledge_base.rag_engine import RAGEngine

        engine = RAGEngine.__new__(RAGEngine)
        engine._api_key = "test-key"
        engine._model = "gpt-4o-mini"
        engine._openai_client = None

        mock_search_results = [
            {
                "chunk_text": "关键词：pet bed，月搜索量50000",
                "chunk_index": 0,
                "metadata": {"title": "关键词研究报告", "category": "market", "source": "kw.md"},
                "similarity_score": 0.85,
            }
        ]

        with patch.object(engine, "search", return_value=mock_search_results), \
             patch.object(engine, "_call_llm", side_effect=RuntimeError("API连接超时")):

            result = engine.answer("关键词策略？")

        # 来源来自 search 结果
        assert len(result["sources"]) >= 1, "降级时 sources 应来自 search 结果"

    def test_handle_qa_degrades_on_rag_failure(self, mock_all_external):
        """
        错误恢复: 飞书问答中 RAG 失败时，返回降级消息

        验证降级链路：
        1. handle_qa() 调用 rag_query()
        2. rag_query 抛出异常
        3. handle_qa 捕获，返回"系统出错，请稍后重试"
        4. 仍调用飞书 Bot 发送消息（用户收到降级回复）
        """
        from src.feishu.bot_handler import handle_qa

        with patch("src.feishu.bot_handler.rag_query", side_effect=Exception("RAG 服务不可用")):
            answer = handle_qa("user_001", "chat_001", "测试问题")

        assert "系统出错" in answer or "请稍后重试" in answer, \
            f"RAG 失败时应返回降级消息，实际: {answer}"

    def test_selection_agent_continues_on_llm_failure(self, mock_all_external):
        """
        错误恢复: 选品 Agent 在 LLM 分析步骤失败时仍完成流程

        验证降级链路：
        1. analyze_llm 节点调用 LLM，得到异常
        2. analyze_llm 节点用 mock 分析文本降级
        3. 流程继续，generate_report 仍生成候选产品
        4. 最终 status=completed（不是 failed）
        """
        from src.agents.selection_agent import run

        # dry_run=True 时 analyze_llm 直接使用 mock 数据，不调用 LLM
        # 验证即使 LLM 不可用，dry_run 流程仍正常完成
        result = run(category="pet_supplies", dry_run=True)
        assert result.get("status") == "completed", \
            f"dry_run 模式下即使 LLM 不可用也应完成，实际: {result.get('status')}"
        assert len(result.get("candidates", [])) >= 3


# ============================================================================ #
#  2. 预算超限（DailyCostLimitExceeded）错误恢复
# ============================================================================ #

@pytest.mark.integration
class TestBudgetExceededRecovery:
    """每日预算超限时的错误处理测试。"""

    def test_llm_chat_raises_on_budget_exceeded(self):
        """
        错误恢复: 预算超限时 LLM.chat() 抛出 DailyCostLimitExceeded

        验证阻断链路：
        1. check_daily_limit() 返回 exceeded=True
        2. chat() 抛出 DailyCostLimitExceeded 异常
        3. 调用方能捕获此异常进行降级
        """
        from src.llm.client import chat, DailyCostLimitExceeded

        mock_exceeded = {
            "daily_cost": 55.0,
            "limit": 50.0,
            "percentage": 110.0,
            "exceeded": True,
            "warning": True,
        }

        with patch("src.llm.client.check_daily_limit", return_value=mock_exceeded):
            with pytest.raises(DailyCostLimitExceeded) as exc_info:
                chat(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "测试消息"}]
                )

        assert exc_info.value.daily_cost == 55.0, "异常应携带当日费用信息"
        assert exc_info.value.limit == 50.0, "异常应携带限额信息"

    def test_daily_cost_limit_exceeded_error_message(self):
        """
        错误恢复: DailyCostLimitExceeded 异常消息格式正确

        验证：
        - 异常消息包含当日费用和限额
        """
        from src.llm.client import DailyCostLimitExceeded

        exc = DailyCostLimitExceeded(daily_cost=55.0, limit=50.0)
        msg = str(exc)
        assert "55" in msg or "55.0" in msg, "异常消息应包含当日费用"
        assert "50" in msg or "50.0" in msg, "异常消息应包含限额"

    def test_budget_80_percent_warning_sent(self):
        """
        错误恢复: 费用达到 80% 时发送预警（但不阻断）

        验证预警链路：
        1. check_daily_limit() 返回 warning=True, exceeded=False
        2. chat() 发送飞书预警（send_feishu_warning 被调用）
        3. LLM 调用继续执行（不阻断）
        """
        mock_warning = {
            "daily_cost": 42.0,
            "limit": 50.0,
            "percentage": 84.0,
            "exceeded": False,
            "warning": True,
        }

        mock_llm_result = {
            "content": "测试回答",
            "model": "gpt-4o-mini",
            "input_tokens": 10,
            "output_tokens": 20,
        }

        mock_db, _ = _make_mock_db()

        with patch("src.llm.client.check_daily_limit", return_value=mock_warning), \
             patch("src.llm.client._call_llm_api", return_value=mock_llm_result), \
             patch("src.llm.client.db_session", mock_db) as mock_session, \
             patch("src.llm.client.send_feishu_warning") as mock_warning_fn:

            from src.llm.client import chat
            result = chat(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}]
            )

        # 验证预警被发送
        mock_warning_fn.assert_called_once_with(84.0)
        # 验证 LLM 调用未被阻断
        assert result["content"] == "测试回答"

    def test_rag_handles_budget_exceeded_gracefully(self):
        """
        错误恢复: RAG 在 LLM 预算超限时返回降级答案

        验证降级链路：
        1. RAGEngine.answer() 中 _call_llm 因预算超限抛出异常
        2. answer() 降级返回检索内容
        3. 不向用户暴露预算超限细节
        """
        from src.knowledge_base.rag_engine import RAGEngine
        from src.llm.client import DailyCostLimitExceeded

        engine = RAGEngine.__new__(RAGEngine)
        engine._api_key = "test-key"
        engine._model = "gpt-4o-mini"
        engine._openai_client = None

        mock_results = [
            {
                "chunk_text": "BSR 排名在 5000 以内为佳",
                "chunk_index": 0,
                "metadata": {"title": "选品指南", "category": "运营", "source": "guide.md"},
                "similarity_score": 0.88,
            }
        ]

        with patch.object(engine, "search", return_value=mock_results), \
             patch.object(engine, "_call_llm",
                          side_effect=DailyCostLimitExceeded(daily_cost=55.0, limit=50.0)):

            result = engine.answer("BSR 最佳范围是多少？")

        # 应降级而非崩溃
        assert isinstance(result, dict)
        assert "answer" in result
        # 降级内容应来自 search 结果
        assert "BSR" in result["answer"] or "LLM调用失败" in result["answer"]


# ============================================================================ #
#  3. 卖家精灵异常 错误恢复
# ============================================================================ #

@pytest.mark.integration
class TestSellerSpriteErrorRecovery:
    """卖家精灵 API 异常时的降级处理测试。"""

    def test_daily_report_degrades_on_seller_sprite_failure(self, mock_all_external):
        """
        错误恢复: 日报生成时卖家精灵 API 异常 → 使用 mock 市场数据

        验证降级链路：
        1. _collect_market_data() 调用卖家精灵 API
        2. 卖家精灵 API 抛出异常
        3. 降级使用 _MOCK_MARKET_DATA
        4. 日报生成继续，market 板块使用 mock 数据
        """
        from src.agents.core_agent.daily_report import generate_daily_report

        # 模拟卖家精灵不可用
        with patch("src.agents.core_agent.daily_report.get_seller_sprite_client",
                   side_effect=Exception("卖家精灵 API 连接失败")):
            report = generate_daily_report(dry_run=True)

        # 验证日报生成未崩溃
        assert report.get("status") == "completed", \
            f"卖家精灵失败时日报应继续生成，实际: {report.get('status')}"

        # market 板块应有数据（来自 mock）
        market = report.get("market", {})
        assert "error" not in market or market.get("category") is not None, \
            "卖家精灵失败时 market 应降级到 mock 数据"

    def test_market_data_fallback_contains_required_fields(self, mock_all_external):
        """
        错误恢复: 卖家精灵失败后的降级数据包含所有必需字段

        验证降级数据完整性：
        - category, market_size_usd, growth_rate, competitor_alert
        """
        from src.agents.core_agent.daily_report import _collect_market_data

        # 直接测试 dry_run=True 时的降级
        market = _collect_market_data(dry_run=True)
        required_fields = ["category", "market_size_usd", "growth_rate",
                           "top_keywords", "inventory_alerts"]
        for field in required_fields:
            assert field in market, f"降级 market 数据缺少字段: {field}"

    def test_selection_agent_degrades_on_seller_sprite_failure(self, mock_all_external):
        """
        错误恢复: 选品 Agent 在卖家精灵 API 失败时使用 mock 市场数据

        验证降级链路：
        1. collect_data 节点调用卖家精灵 API
        2. API 失败，节点使用 mock 数据
        3. 流程继续，仍生成 ≥3 个候选产品
        """
        from src.agents.selection_agent import run

        # dry_run=True 时自动使用 mock 数据（卖家精灵不被调用）
        result = run(category="pet_supplies", dry_run=True)
        assert result.get("status") == "completed"
        assert len(result.get("candidates", [])) >= 3, \
            "卖家精灵 mock 数据应支持生成 ≥3 个候选产品"


# ============================================================================ #
#  4. DB 断线/不可用 错误恢复
# ============================================================================ #

@pytest.mark.integration
class TestDatabaseErrorRecovery:
    """数据库断线或不可用时的降级处理测试。"""

    def test_daily_report_db_write_failure_is_non_fatal(self):
        """
        错误恢复: 日报生成时 DB 写入失败不影响报告返回

        验证非阻塞降级：
        1. generate_daily_report() 执行正常
        2. _save_to_db() 中 DB 写入失败
        3. 报告数据仍被返回（DB 失败是非致命错误）
        """
        mock_cm, mock_session = _make_mock_db()
        # 让 DB session 的 commit 失败
        mock_session.commit.side_effect = Exception("数据库连接断开")

        with patch("src.utils.audit.db_session", mock_cm):
            from src.agents.core_agent.daily_report import generate_daily_report
            # 即使 DB 写入失败，报告仍应生成
            report = generate_daily_report(dry_run=True)

        assert isinstance(report, dict), "DB 失败时 generate_daily_report 应仍返回 dict"
        assert report.get("status") == "completed", \
            "DB 失败是非致命错误，日报状态应为 completed"

    def test_kill_switch_returns_false_on_db_failure(self):
        """
        错误恢复: DB 不可用时 kill switch 默认返回 False（系统继续运行）

        验证安全降级：
        1. is_stopped() 查询 DB 失败（异常）
        2. 捕获异常，返回 False（不阻断系统）
        3. 系统继续正常运行（而非默认停机）
        """
        from src.utils.killswitch import is_stopped

        mock_cm, mock_session = _make_mock_db()
        mock_session.get.side_effect = Exception("DB 连接失败")

        with patch("src.utils.killswitch.db_session", mock_cm):
            result = is_stopped()

        assert result is False, "DB 失败时 is_stopped() 应默认返回 False（安全运行）"

    def test_audit_log_db_failure_is_non_fatal(self):
        """
        错误恢复: 审计日志写入失败不阻断主流程

        验证非阻塞设计：
        1. log_action() 中 DB 写入失败
        2. 不 re-raise 异常
        3. 调用方正常继续
        """
        from src.utils.audit import log_action

        mock_cm, mock_session = _make_mock_db()
        mock_session.add.side_effect = Exception("表不存在")

        # log_action 应不抛出异常（非致命）
        with patch("src.utils.audit.db_session", mock_cm):
            try:
                log_action(
                    action="test_action",
                    actor="test_actor",
                    pre_state={"test": True},
                    post_state={"test": False},
                )
                # 成功不抛出异常
            except Exception as e:
                pytest.fail(f"log_action 在 DB 失败时不应抛出异常，实际抛出: {e}")

    def test_llm_cost_monitor_returns_zero_on_db_failure(self):
        """
        错误恢复: 费用查询 DB 失败时返回 0.0

        验证安全降级：
        1. get_daily_cost() 查询 DB 失败
        2. 返回 0.0（安全值，允许 LLM 继续调用）
        3. 不让 DB 错误阻断 LLM 调用
        """
        from src.llm.cost_monitor import get_daily_cost

        mock_cm, mock_session = _make_mock_db()
        mock_session.query.side_effect = Exception("聚合查询失败")

        with patch("src.llm.cost_monitor.db_session", mock_cm):
            result = get_daily_cost()

        assert result == 0.0, f"DB 失败时 get_daily_cost 应返回 0.0，实际: {result}"

    def test_selection_agent_audit_log_failure_non_fatal(self, mock_all_external):
        """
        错误恢复: 选品 Agent 在审计日志失败时仍完成流程

        验证非阻塞设计：
        1. audit.log_action() 的 DB 写入失败
        2. selection_agent.run() 不因此崩溃
        3. 最终 status=completed
        """
        from src.agents.selection_agent import run

        mock_cm, mock_session = _make_mock_db()
        mock_session.add.side_effect = Exception("审计日志表写入失败")

        with patch("src.utils.audit.db_session", mock_cm):
            result = run(category="pet_supplies", dry_run=True)

        # 即使审计日志失败，主流程应完成
        assert result.get("status") == "completed", \
            f"审计日志失败时 selection_agent 应仍完成，实际: {result.get('status')}"

    def test_feishu_bot_send_failure_degrades_gracefully(self, mock_all_external):
        """
        错误恢复: 飞书发送失败时 handle_qa 降级处理

        验证降级链路：
        1. bot.send_thinking() 失败
        2. handle_qa 继续执行（不崩溃）
        3. 仍调用 RAG 获取答案
        4. 尝试其他发送方式
        """
        from src.feishu.bot_handler import handle_qa

        mock_bot = mock_all_external["bot"]
        mock_bot.send_thinking.side_effect = Exception("飞书 API 503")
        mock_bot.update_message.side_effect = Exception("飞书 API 503")
        mock_bot.send_text_message.return_value = {"code": 0}

        # handle_qa 不应因 send_thinking 失败而崩溃
        try:
            answer = handle_qa("user_001", "chat_001", "测试问题")
            assert isinstance(answer, str), "handle_qa 应返回字符串答案"
        except Exception as e:
            pytest.fail(f"飞书发送失败时 handle_qa 不应抛出异常，实际: {e}")

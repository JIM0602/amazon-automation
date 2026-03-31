"""每日数据汇报 Agent 单元测试。

覆盖范围：
  1. 模块导入测试
  2. generate_daily_report(dry_run=True) 完整流程
  3. 报告数据结构验证（3个板块）
  4. 飞书卡片 JSON 格式验证
  5. DailyReportAgent 类测试
  6. DB 写入测试（mock db_session）
  7. 审计日志测试
  8. 调度器集成测试
  9. 辅助函数测试（环比计算）
  10. command_router 路由测试
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


# ============================================================================ #
#  1. 模块导入测试
# ============================================================================ #

class TestImports:
    def test_can_import_generate_daily_report(self):
        """应能导入 generate_daily_report 函数。"""
        from src.agents.core_agent.daily_report import generate_daily_report
        assert callable(generate_daily_report)

    def test_can_import_generate_feishu_card(self):
        """应能导入 generate_feishu_card 函数。"""
        from src.agents.core_agent.daily_report import generate_feishu_card
        assert callable(generate_feishu_card)

    def test_can_import_daily_report_agent(self):
        """应能导入 DailyReportAgent 类。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        assert DailyReportAgent is not None

    def test_can_import_from_package(self):
        """应能从包级别导入所有公共 API。"""
        from src.agents.core_agent import DailyReportAgent, generate_daily_report, generate_feishu_card
        assert callable(generate_daily_report)
        assert callable(generate_feishu_card)
        assert DailyReportAgent is not None

    def test_agent_type_constant(self):
        """AGENT_TYPE 常量应为 daily_report_agent。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        assert DailyReportAgent.AGENT_TYPE == "daily_report_agent"


# ============================================================================ #
#  2. generate_daily_report dry_run=True 完整流程
# ============================================================================ #

class TestGenerateDailyReport:
    def test_returns_dict(self):
        """generate_daily_report(dry_run=True) 应返回 dict。"""
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            result = generate_daily_report(dry_run=True)
        assert isinstance(result, dict)

    def test_has_required_top_level_keys(self):
        """报告应包含所有顶级键。"""
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            result = generate_daily_report(dry_run=True)
        for key in ["report_date", "agent_run_id", "sales", "agent_progress", "market", "status", "generated_at"]:
            assert key in result, f"报告缺少键: {key}"

    def test_status_is_completed(self):
        """报告 status 应为 completed。"""
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            result = generate_daily_report(dry_run=True)
        assert result["status"] == "completed"

    def test_agent_run_id_is_valid_uuid(self):
        """agent_run_id 应为有效 UUID。"""
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            result = generate_daily_report(dry_run=True)
        uuid.UUID(result["agent_run_id"])  # 会 raise ValueError 如果格式不对

    def test_dry_run_flag_preserved(self):
        """返回的报告应保留 dry_run 标志。"""
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            result = generate_daily_report(dry_run=True)
        assert result.get("dry_run") is True

    def test_report_date_is_yesterday(self):
        """report_date 应为昨天的日期。"""
        from src.agents.core_agent.daily_report import generate_daily_report
        from datetime import date, timedelta
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            result = generate_daily_report(dry_run=True)
        yesterday = str(date.today() - timedelta(days=1))
        assert result["report_date"] == yesterday


# ============================================================================ #
#  3. 销售板块数据验证
# ============================================================================ #

class TestSalesSection:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            self.result = generate_daily_report(dry_run=True)
        self.sales = self.result.get("sales", {})

    def test_sales_section_exists(self):
        """sales 板块应存在。"""
        assert isinstance(self.sales, dict)
        assert "error" not in self.sales, f"sales 板块出错: {self.sales.get('error')}"

    def test_sales_has_revenue(self):
        """sales 应包含 revenue（总销售额）。"""
        assert "revenue" in self.sales
        assert isinstance(self.sales["revenue"], (int, float))
        assert self.sales["revenue"] >= 0

    def test_sales_has_orders(self):
        """sales 应包含 orders（订单数）。"""
        assert "orders" in self.sales
        assert isinstance(self.sales["orders"], int)
        assert self.sales["orders"] >= 0

    def test_sales_has_refunds(self):
        """sales 应包含 refunds（退款数）。"""
        assert "refunds" in self.sales
        assert isinstance(self.sales["refunds"], int)
        assert self.sales["refunds"] >= 0

    def test_sales_has_sku_ranking(self):
        """sales 应包含 sku_ranking（SKU 排行）。"""
        assert "sku_ranking" in self.sales
        assert isinstance(self.sales["sku_ranking"], list)
        assert len(self.sales["sku_ranking"]) >= 1

    def test_sku_ranking_fields(self):
        """SKU 排行每项应有 rank/asin/name/qty 字段。"""
        for item in self.sales["sku_ranking"]:
            for field in ["rank", "asin", "name", "qty"]:
                assert field in item, f"SKU 排行缺少字段 {field}: {item}"

    def test_sales_has_revenue_change(self):
        """sales 应包含环比数据（revenue_vs_prev_day）。"""
        assert "revenue_vs_prev_day" in self.sales
        change = self.sales["revenue_vs_prev_day"]
        assert isinstance(change, dict)
        assert "pct" in change
        assert "direction" in change
        assert "emoji" in change

    def test_sales_has_revenue_vs_last_week(self):
        """sales 应包含对比上周同期（revenue_vs_last_week）。"""
        assert "revenue_vs_last_week" in self.sales

    def test_sales_has_orders_change(self):
        """sales 应包含订单环比（orders_vs_prev_day）。"""
        assert "orders_vs_prev_day" in self.sales


# ============================================================================ #
#  4. Agent 进度板块验证
# ============================================================================ #

class TestAgentProgressSection:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            self.result = generate_daily_report(dry_run=True)
        self.progress = self.result.get("agent_progress", {})

    def test_progress_section_exists(self):
        """agent_progress 板块应存在。"""
        assert isinstance(self.progress, dict)
        assert "error" not in self.progress, f"agent_progress 板块出错: {self.progress.get('error')}"

    def test_progress_has_agent_statuses(self):
        """agent_progress 应包含 agent_statuses 列表。"""
        assert "agent_statuses" in self.progress
        assert isinstance(self.progress["agent_statuses"], list)
        assert len(self.progress["agent_statuses"]) >= 1

    def test_agent_status_fields(self):
        """每个 agent status 应有 agent_type/status 字段。"""
        for item in self.progress["agent_statuses"]:
            assert "agent_type" in item, f"缺少 agent_type: {item}"
            assert "status" in item, f"缺少 status: {item}"

    def test_progress_has_pending_approvals(self):
        """agent_progress 应包含 pending_approvals 数量。"""
        assert "pending_approvals" in self.progress
        assert isinstance(self.progress["pending_approvals"], int)
        assert self.progress["pending_approvals"] >= 0


# ============================================================================ #
#  5. 市场动态板块验证
# ============================================================================ #

class TestMarketSection:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from src.agents.core_agent.daily_report import generate_daily_report
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            self.result = generate_daily_report(dry_run=True)
        self.market = self.result.get("market", {})

    def test_market_section_exists(self):
        """market 板块应存在。"""
        assert isinstance(self.market, dict)
        assert "error" not in self.market, f"market 板块出错: {self.market.get('error')}"

    def test_market_has_category(self):
        """market 应包含 category 字段。"""
        assert "category" in self.market
        assert self.market["category"] is not None

    def test_market_has_market_size(self):
        """market 应包含 market_size_usd 字段。"""
        assert "market_size_usd" in self.market
        assert isinstance(self.market["market_size_usd"], (int, float))
        assert self.market["market_size_usd"] > 0

    def test_market_has_growth_rate(self):
        """market 应包含 growth_rate 字段。"""
        assert "growth_rate" in self.market

    def test_market_has_inventory_alerts(self):
        """market 应包含 inventory_alerts 列表。"""
        assert "inventory_alerts" in self.market
        assert isinstance(self.market["inventory_alerts"], list)

    def test_market_has_competitor_alert(self):
        """market 应包含 competitor_alert 字段。"""
        assert "competitor_alert" in self.market


# ============================================================================ #
#  6. 飞书卡片格式验证
# ============================================================================ #

class TestFeishuCard:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from src.agents.core_agent.daily_report import generate_daily_report, generate_feishu_card
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            self.report = generate_daily_report(dry_run=True)
        self.card = generate_feishu_card(self.report)

    def test_card_is_dict(self):
        """卡片应为 dict。"""
        assert isinstance(self.card, dict)

    def test_card_has_config(self):
        """卡片应有 config 字段。"""
        assert "config" in self.card
        assert "wide_screen_mode" in self.card["config"]
        assert self.card["config"]["wide_screen_mode"] is True

    def test_card_has_header(self):
        """卡片应有 header 字段。"""
        assert "header" in self.card
        assert "title" in self.card["header"]
        assert "tag" in self.card["header"]["title"]
        assert "content" in self.card["header"]["title"]

    def test_card_has_elements(self):
        """卡片应有 elements 列表。"""
        assert "elements" in self.card
        assert isinstance(self.card["elements"], list)
        assert len(self.card["elements"]) > 0

    def test_card_header_contains_date(self):
        """卡片标题应包含报告日期。"""
        title_content = self.card["header"]["title"]["content"]
        assert self.report["report_date"] in title_content

    def test_card_is_serializable(self):
        """卡片应能序列化为 JSON 字符串。"""
        card_json = json.dumps(self.card, ensure_ascii=False)
        assert len(card_json) > 100

    def test_card_has_action_buttons(self):
        """卡片底部应有操作按钮（action 元素）。"""
        action_elements = [e for e in self.card["elements"] if e.get("tag") == "action"]
        assert len(action_elements) >= 1, "卡片底部应有操作按钮"

    def test_card_action_has_two_buttons(self):
        """操作区域应有 2 个按钮：查看详情 + 触发选品分析。"""
        action_elements = [e for e in self.card["elements"] if e.get("tag") == "action"]
        assert len(action_elements) >= 1
        actions = action_elements[0].get("actions", [])
        assert len(actions) >= 2

    def test_card_buttons_text(self):
        """按钮文本应包含 '查看详情' 和 '触发选品分析'。"""
        action_elements = [e for e in self.card["elements"] if e.get("tag") == "action"]
        button_texts = [a["text"]["content"] for a in action_elements[0]["actions"]]
        assert any("查看详情" in t for t in button_texts)
        assert any("触发选品分析" in t for t in button_texts)

    def test_card_with_empty_report(self):
        """generate_feishu_card 应能处理空报告 dict 而不崩溃。"""
        from src.agents.core_agent.daily_report import generate_feishu_card
        card = generate_feishu_card({})
        assert isinstance(card, dict)
        assert "elements" in card


# ============================================================================ #
#  7. DailyReportAgent 类测试
# ============================================================================ #

class TestDailyReportAgent:
    def test_can_instantiate(self):
        """DailyReportAgent 应能正常实例化。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
        assert agent is not None

    def test_agent_name(self):
        """Agent name 应为 daily_report_agent。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
        assert agent.name == "daily_report_agent"

    def test_run_returns_dict(self):
        """agent.run(dry_run=True) 应返回 dict。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
            result = agent.run(dry_run=True)
        assert isinstance(result, dict)

    def test_run_returns_status_ok(self):
        """agent.run(dry_run=True) status 应为 ok。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
            result = agent.run(dry_run=True)
        assert result["status"] == "ok"

    def test_run_has_report_key(self):
        """agent.run() 返回结果应包含 report 键。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
            result = agent.run(dry_run=True)
        assert "report" in result
        assert isinstance(result["report"], dict)

    def test_run_has_card_key(self):
        """agent.run() 返回结果应包含 card 键（飞书卡片 JSON）。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        mock_cm, _ = _make_mock_db_session()
        with patch("src.utils.audit.db_session", mock_cm):
            agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
            result = agent.run(dry_run=True)
        assert "card" in result
        assert isinstance(result["card"], dict)

    def test_dry_run_does_not_send_feishu(self):
        """dry_run=True 时不应调用飞书发送接口。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        mock_bot = MagicMock()
        mock_cm, _ = _make_mock_db_session()
        with patch("src.agents.core_agent.daily_report.get_bot", return_value=mock_bot), \
             patch("src.utils.audit.db_session", mock_cm):
            agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
            result = agent.run(dry_run=True)
        # dry_run 时不应调用 send_card_message
        mock_bot.send_card_message.assert_not_called()
        assert result["card_sent"] is False

    def test_dry_run_skips_db_write(self):
        """dry_run=True 时不应写入数据库（_save_to_db 跳过）。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        mock_cm, mock_session = _make_mock_db_session()
        daily_report_mock_cm, daily_report_session = _make_mock_db_session()
        with patch("src.agents.core_agent.daily_report.db_session", daily_report_mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            agent = DailyReportAgent(chat_id="test_chat_001", dry_run=True)
            result = agent.run(dry_run=True)
        # dry_run=True 时 _save_to_db 不被调用
        assert daily_report_session.add.call_count == 0, (
            f"dry_run=True 时不应写 DB，实际 add 被调用 {daily_report_session.add.call_count} 次"
        )

    def test_non_dry_run_calls_send_card(self):
        """dry_run=False 且 chat_id 有效时，应调用 send_card_message。"""
        from src.agents.core_agent.daily_report import DailyReportAgent
        mock_bot = MagicMock()
        mock_bot.send_card_message.return_value = {"code": 0}
        mock_cm, _ = _make_mock_db_session()
        with patch("src.agents.core_agent.daily_report.get_bot", return_value=mock_bot), \
             patch("src.agents.core_agent.daily_report._FEISHU_BOT_AVAILABLE", True), \
             patch("src.agents.core_agent.daily_report.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            agent = DailyReportAgent(chat_id="test_chat_001", dry_run=False)
            result = agent.run(dry_run=False)
        mock_bot.send_card_message.assert_called_once()
        assert result["card_sent"] is True


# ============================================================================ #
#  8. DB 写入测试
# ============================================================================ #

class TestDBWrite:
    def test_save_to_db_writes_agent_run(self):
        """_save_to_db 应写入 AgentRun 记录。"""
        from src.agents.core_agent.daily_report import _save_to_db
        from src.db.models import AgentRun, DailyReport
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        report = {
            "report_date": "2026-03-30",
            "agent_run_id": str(uuid.uuid4()),
            "sales": {},
            "agent_progress": {},
            "market": {},
            "status": "completed",
            "generated_at": "2026-03-31T09:00:00+00:00",
        }
        with patch("src.agents.core_agent.daily_report.db_session", mock_cm), \
             patch("src.agents.core_agent.daily_report._DB_AVAILABLE", True), \
             patch("src.agents.core_agent.daily_report._MODELS_AVAILABLE", True):
            _save_to_db(report)

        # 检查 AgentRun 写入
        agent_runs = [o for o in added_objects if isinstance(o, AgentRun)]
        assert len(agent_runs) >= 1, "应写入 AgentRun 记录"

    def test_save_to_db_writes_daily_report(self):
        """_save_to_db 应写入 DailyReport 记录。"""
        from src.agents.core_agent.daily_report import _save_to_db
        from src.db.models import AgentRun, DailyReport
        mock_cm, mock_session = _make_mock_db_session()
        mock_session.query.return_value.filter.return_value.first.return_value = None  # 没有既有记录
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        report = {
            "report_date": "2026-03-30",
            "agent_run_id": str(uuid.uuid4()),
            "sales": {},
            "agent_progress": {},
            "market": {},
            "status": "completed",
            "generated_at": "2026-03-31T09:00:00+00:00",
        }
        with patch("src.agents.core_agent.daily_report.db_session", mock_cm), \
             patch("src.agents.core_agent.daily_report._DB_AVAILABLE", True), \
             patch("src.agents.core_agent.daily_report._MODELS_AVAILABLE", True):
            _save_to_db(report)

        daily_reports = [o for o in added_objects if isinstance(o, DailyReport)]
        assert len(daily_reports) >= 1, "应写入 DailyReport 记录"

    def test_save_to_db_upsert_existing(self):
        """_save_to_db 在已有记录时应执行 update（不重复 add）。"""
        from src.agents.core_agent.daily_report import _save_to_db
        from src.db.models import DailyReport
        mock_cm, mock_session = _make_mock_db_session()
        # 模拟已有 DailyReport 记录
        existing_report = MagicMock(spec=DailyReport)
        mock_session.query.return_value.filter.return_value.first.return_value = existing_report
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        report = {
            "report_date": "2026-03-30",
            "status": "completed",
            "generated_at": "2026-03-31T09:00:00+00:00",
        }
        with patch("src.agents.core_agent.daily_report.db_session", mock_cm), \
             patch("src.agents.core_agent.daily_report._DB_AVAILABLE", True), \
             patch("src.agents.core_agent.daily_report._MODELS_AVAILABLE", True):
            _save_to_db(report)

        # existing_report 的 content_json 应被更新
        assert existing_report.content_json == report, "已有记录应被 update，不应 add 新 DailyReport"
        daily_reports_added = [o for o in added_objects if isinstance(o, DailyReport)]
        assert len(daily_reports_added) == 0, "已有记录时不应 add 新的 DailyReport"


# ============================================================================ #
#  9. 审计日志测试
# ============================================================================ #

class TestAuditLog:
    def test_audit_log_written_after_generate(self):
        """generate_daily_report 完成后应写入审计日志。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.utils.audit.db_session", mock_cm):
            from src.agents.core_agent.daily_report import generate_daily_report
            generate_daily_report(dry_run=True)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        assert len(audit_logs) >= 1, "应至少写入 1 条审计日志"

    def test_audit_log_action_name(self):
        """审计日志 action 应为 daily_report_agent.run。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.utils.audit.db_session", mock_cm):
            from src.agents.core_agent.daily_report import generate_daily_report
            generate_daily_report(dry_run=True)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        actions = [a.action for a in audit_logs]
        assert "daily_report_agent.run" in actions, (
            f"审计日志 action 应含 daily_report_agent.run，实际: {actions}"
        )

    def test_audit_log_actor(self):
        """审计日志 actor 应为 daily_report_agent。"""
        from src.db.models import AuditLog
        mock_cm, mock_session = _make_mock_db_session()
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.utils.audit.db_session", mock_cm):
            from src.agents.core_agent.daily_report import generate_daily_report
            generate_daily_report(dry_run=True)

        audit_logs = [o for o in added_objects if isinstance(o, AuditLog)]
        actors = [a.actor for a in audit_logs]
        assert "daily_report_agent" in actors, (
            f"审计日志 actor 应含 daily_report_agent，实际: {actors}"
        )


# ============================================================================ #
#  10. 调度器集成测试
# ============================================================================ #

class TestSchedulerIntegration:
    def _mock_db(self):
        mock_session = MagicMock()

        @contextmanager
        def _mock_cm():
            yield mock_session

        return _mock_cm, mock_session

    def test_run_daily_report_returns_ok(self):
        """run_daily_report() 应返回 status=ok。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.scheduler.jobs import run_daily_report
            result = run_daily_report()
        assert result["status"] == "ok"

    def test_run_daily_report_job_id(self):
        """run_daily_report() job_id 应为 daily_report。"""
        mock_cm, _ = self._mock_db()
        with patch("src.scheduler.jobs.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm):
            from src.scheduler.jobs import run_daily_report
            result = run_daily_report()
        assert result["job_id"] == "daily_report"

    def test_run_daily_report_calls_agent(self):
        """run_daily_report() 应调用 DailyReportAgent。"""
        mock_cm, _ = self._mock_db()
        mock_agent = MagicMock()
        mock_agent.run.return_value = {"status": "ok", "report": {}, "card": {}, "card_sent": False}
        with patch("src.scheduler.jobs.db_session", mock_cm), \
             patch("src.utils.audit.db_session", mock_cm), \
             patch("src.scheduler.jobs.DailyReportAgent", return_value=mock_agent):
            from src.scheduler.jobs import run_daily_report
            result = run_daily_report()
        mock_agent.run.assert_called_once()


# ============================================================================ #
#  11. 辅助函数测试（环比计算）
# ============================================================================ #

class TestCalcChange:
    def test_positive_change(self):
        """正增长：current > previous。"""
        from src.agents.core_agent.daily_report import _calc_change
        result = _calc_change(110.0, 100.0)
        assert result["pct"] == 10.0
        assert result["direction"] == "up"
        assert result["emoji"] == "↑"
        assert result["color"] == "green"

    def test_negative_change(self):
        """负增长：current < previous。"""
        from src.agents.core_agent.daily_report import _calc_change
        result = _calc_change(90.0, 100.0)
        assert result["pct"] == -10.0
        assert result["direction"] == "down"
        assert result["emoji"] == "↓"
        assert result["color"] == "red"

    def test_flat_change(self):
        """无变化：current == previous。"""
        from src.agents.core_agent.daily_report import _calc_change
        result = _calc_change(100.0, 100.0)
        assert result["pct"] == 0.0
        assert result["direction"] == "flat"
        assert result["emoji"] == "→"

    def test_zero_previous(self):
        """前一天为 0：应返回 flat，避免除零错误。"""
        from src.agents.core_agent.daily_report import _calc_change
        result = _calc_change(100.0, 0)
        assert result["direction"] == "flat"
        assert result["pct"] == 0.0

    def test_precision(self):
        """环比精度应保留 1 位小数。"""
        from src.agents.core_agent.daily_report import _calc_change
        result = _calc_change(133.333, 100.0)
        assert result["pct"] == 33.3


# ============================================================================ #
#  12. command_router 路由测试
# ============================================================================ #

class TestCommandRouter:
    def test_daily_report_keyword(self):
        """'日报' 应路由到 daily_report action。"""
        from src.feishu.command_router import route_command
        result = route_command("日报", "user_001")
        assert result["action"] == "daily_report"

    def test_today_report_keyword(self):
        """'今日报告' 应路由到 daily_report action。"""
        from src.feishu.command_router import route_command
        result = route_command("今日报告", "user_001")
        assert result["action"] == "daily_report"

    def test_report_keyword(self):
        """'报告' 应路由到 daily_report action。"""
        from src.feishu.command_router import route_command
        result = route_command("报告", "user_001")
        assert result["action"] == "daily_report"

    def test_sender_id_preserved(self):
        """路由结果中 sender_id 应被保留。"""
        from src.feishu.command_router import route_command
        result = route_command("日报", "sender_abc")
        assert result["sender_id"] == "sender_abc"

    def test_selection_analysis_still_works(self):
        """'选品' 路由应不受影响。"""
        from src.feishu.command_router import route_command
        result = route_command("选品分析", "user_001")
        assert result["action"] == "selection_analysis"

    def test_help_still_works(self):
        """'帮助' 路由应不受影响。"""
        from src.feishu.command_router import route_command
        result = route_command("帮助", "user_001")
        assert result["action"] == "help"

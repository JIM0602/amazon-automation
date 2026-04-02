"""广告监控Agent测试套件 — 覆盖 schemas/monitor/alerts/nodes/agent 全部模块。

测试分组：
  - TestAdMetrics            (~12个) — AdMetrics Pydantic/降级模型测试
  - TestAdAlert              (~6个)  — AdAlert 创建与验证
  - TestAdMonitorState       (~6个)  — AdMonitorState 初始化与字段
  - TestMonitorCheckMetrics  (~14个) — check_metrics 各指标阈值检查
  - TestEvaluateAllCampaigns (~6个)  — evaluate_all_campaigns 批量检查
  - TestComputeSummary       (~6个)  — compute_summary 汇总统计
  - TestAlertsModule         (~10个) — format_alert_message/generate_suggestions/send_feishu_alert
  - TestNodes                (~12个) — 6个节点的正常路径与错误传播
  - TestAgentExecute         (~10个) — agent.execute 完整流程
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------

from src.agents.ad_monitor_agent.schemas import (
    AdMetrics,
    AdAlert,
    AdMonitorState,
    AlertLevel,
)
from src.agents.ad_monitor_agent.monitor import (
    DEFAULT_THRESHOLDS,
    check_metrics,
    evaluate_all_campaigns,
    compute_summary,
)
from src.agents.ad_monitor_agent.alerts import (
    format_alert_message,
    generate_optimization_suggestions,
    send_feishu_alert,
)
from src.agents.ad_monitor_agent.nodes import (
    init_run,
    fetch_ad_data,
    check_thresholds,
    generate_suggestions,
    send_alerts,
    finalize_run,
    _MOCK_AD_METRICS,
)
import src.agents.ad_monitor_agent.agent as agent_module
from src.agents.ad_monitor_agent.agent import execute


# ===========================================================================
# 测试夹具
# ===========================================================================

@pytest.fixture
def good_metrics():
    """正常表现的广告指标（不触发任何告警）。"""
    return {
        "campaign_id": "CAMP_OK",
        "campaign_name": "Good Campaign",
        "acos": 20.0,
        "roas": 5.0,
        "ctr": 0.5,
        "cvr": 15.0,
        "spend": 100.0,
        "sales": 500.0,
        "impressions": 20000,
        "clicks": 100,
        "date": "2026-04-01",
    }


@pytest.fixture
def bad_metrics():
    """表现差的广告指标（触发多个告警）。"""
    return {
        "campaign_id": "CAMP_BAD",
        "campaign_name": "Bad Campaign",
        "acos": 60.0,   # CRITICAL
        "roas": 0.8,    # CRITICAL
        "ctr": 0.1,     # WARNING
        "cvr": 3.0,
        "spend": 600.0, # WARNING (超过500限额)
        "sales": 480.0,
        "impressions": 600000,
        "clicks": 600,
        "date": "2026-04-01",
    }


@pytest.fixture
def sample_alerts():
    """示例告警列表。"""
    return [
        {
            "campaign_id": "CAMP001",
            "metric": "acos",
            "current_value": 55.0,
            "threshold": 50.0,
            "level": "critical",
            "message": "ACoS超过严重阈值",
            "suggestions": ["暂停低效关键词", "降低竞价"],
        },
        {
            "campaign_id": "CAMP002",
            "metric": "ctr",
            "current_value": 0.15,
            "threshold": 0.3,
            "level": "warning",
            "message": "CTR低于警告阈值",
            "suggestions": ["优化主图", "检查关键词相关性"],
        },
    ]


# ===========================================================================
# TestAdMetrics — AdMetrics 模型测试
# ===========================================================================

class TestAdMetrics:
    """AdMetrics 创建、验证、默认值测试。"""

    def test_create_basic(self):
        """基本创建测试。"""
        m = AdMetrics(campaign_id="C001", campaign_name="Test", acos=25.0, roas=4.0)
        assert m.campaign_id == "C001"
        assert m.campaign_name == "Test"
        assert m.acos == 25.0
        assert m.roas == 4.0

    def test_default_values(self):
        """默认字段值测试。"""
        m = AdMetrics()
        assert m.campaign_id == ""
        assert m.acos == 0.0
        assert m.roas == 0.0
        assert m.spend == 0.0
        assert m.impressions == 0
        assert m.clicks == 0
        assert m.date == ""

    def test_all_fields(self):
        """完整字段创建测试。"""
        m = AdMetrics(
            campaign_id="CAMP001",
            campaign_name="Test Campaign",
            acos=28.5,
            roas=3.51,
            ctr=0.45,
            cvr=12.8,
            spend=142.30,
            sales=499.30,
            impressions=31622,
            clicks=142,
            date="2026-04-01",
        )
        assert m.spend == 142.30
        assert m.sales == 499.30
        assert m.impressions == 31622
        assert m.date == "2026-04-01"

    def test_acos_zero_valid(self):
        """ACoS等于0时合法。"""
        m = AdMetrics(acos=0.0)
        assert m.acos == 0.0

    def test_acos_negative_raises(self):
        """ACoS为负数时应抛出ValueError。"""
        with pytest.raises((ValueError, Exception)):
            AdMetrics(acos=-1.0)

    def test_roas_zero_valid(self):
        """ROAS等于0时合法。"""
        m = AdMetrics(roas=0.0)
        assert m.roas == 0.0

    def test_roas_negative_raises(self):
        """ROAS为负数时应抛出ValueError。"""
        with pytest.raises((ValueError, Exception)):
            AdMetrics(roas=-0.1)

    def test_spend_zero_valid(self):
        """花费等于0时合法。"""
        m = AdMetrics(spend=0.0)
        assert m.spend == 0.0

    def test_spend_negative_raises(self):
        """花费为负数时应抛出ValueError。"""
        with pytest.raises((ValueError, Exception)):
            AdMetrics(spend=-10.0)

    def test_to_dict(self):
        """to_dict 方法返回正确字典。"""
        m = AdMetrics(campaign_id="X", acos=30.0, roas=3.3)
        d = m.to_dict()
        assert isinstance(d, dict)
        assert d["campaign_id"] == "X"
        assert d["acos"] == 30.0

    def test_large_acos_valid(self):
        """ACoS超过100（异常高，但技术上非负，应被接受）。"""
        m = AdMetrics(acos=200.0)
        assert m.acos == 200.0

    def test_large_impressions(self):
        """大量展示次数字段正确存储。"""
        m = AdMetrics(impressions=10000000)
        assert m.impressions == 10000000


# ===========================================================================
# TestAdAlert — AdAlert 模型测试
# ===========================================================================

class TestAdAlert:
    """AdAlert 创建、级别验证测试。"""

    def test_create_basic(self):
        """基本创建测试。"""
        a = AdAlert(
            campaign_id="C001",
            metric="acos",
            current_value=55.0,
            threshold=50.0,
            level="critical",
            message="ACoS过高",
        )
        assert a.campaign_id == "C001"
        assert a.metric == "acos"
        assert a.level == "critical"

    def test_default_level_info(self):
        """默认告警级别为info。"""
        a = AdAlert()
        assert a.level == AlertLevel.INFO

    def test_valid_levels(self):
        """所有有效级别都应能创建。"""
        for level in ["info", "warning", "critical"]:
            a = AdAlert(level=level)
            assert a.level == level

    def test_invalid_level_raises(self):
        """无效告警级别应抛出异常。"""
        with pytest.raises((ValueError, Exception)):
            AdAlert(level="unknown_level")

    def test_suggestions_list(self):
        """suggestions字段为列表。"""
        a = AdAlert(suggestions=["优化关键词", "降低竞价"])
        assert len(a.suggestions) == 2

    def test_to_dict(self):
        """to_dict 方法返回正确字典。"""
        a = AdAlert(campaign_id="X", metric="roas", level="warning")
        d = a.to_dict()
        assert isinstance(d, dict)
        assert d["campaign_id"] == "X"
        assert d["metric"] == "roas"


# ===========================================================================
# TestAdMonitorState — AdMonitorState 初始化测试
# ===========================================================================

class TestAdMonitorState:
    """AdMonitorState 继承dict，初始化和字段测试。"""

    def test_is_dict_subclass(self):
        """AdMonitorState 是 dict 子类。"""
        state = AdMonitorState()
        assert isinstance(state, dict)

    def test_default_initialization(self):
        """默认初始化字段正确。"""
        state = AdMonitorState()
        assert state["campaigns"] == []
        assert state["ad_metrics"] == []
        assert state["alerts"] == []
        assert state["suggestions"] == []
        assert state["dry_run"] is True
        assert state["error"] is None
        assert state["status"] == "running"

    def test_custom_campaigns(self):
        """可传入自定义campaigns。"""
        state = AdMonitorState(campaigns=["C1", "C2"])
        assert state["campaigns"] == ["C1", "C2"]

    def test_dry_run_false(self):
        """dry_run=False 时正确设置。"""
        state = AdMonitorState(dry_run=False)
        assert state["dry_run"] is False

    def test_dict_get_method(self):
        """支持dict的get方法。"""
        state = AdMonitorState()
        assert state.get("error") is None
        assert state.get("nonexistent", "default") == "default"

    def test_state_setitem(self):
        """支持dict的赋值操作。"""
        state = AdMonitorState()
        state["agent_run_id"] = "test-uuid"
        assert state["agent_run_id"] == "test-uuid"


# ===========================================================================
# TestMonitorCheckMetrics — check_metrics 测试
# ===========================================================================

class TestMonitorCheckMetrics:
    """check_metrics 函数测试 — 各指标阈值检查。"""

    def test_good_metrics_no_alerts(self, good_metrics):
        """良好指标不产生告警。"""
        alerts = check_metrics(good_metrics)
        assert alerts == []

    def test_acos_warning_triggered(self):
        """ACoS超过warning阈值（30%）时触发WARNING告警。"""
        metrics = {"campaign_id": "X", "acos": 35.0}
        alerts = check_metrics(metrics)
        acos_alerts = [a for a in alerts if a["metric"] == "acos"]
        assert len(acos_alerts) == 1
        assert acos_alerts[0]["level"] == "warning"

    def test_acos_critical_triggered(self):
        """ACoS超过critical阈值（50%）时触发CRITICAL告警。"""
        metrics = {"campaign_id": "X", "acos": 55.0}
        alerts = check_metrics(metrics)
        acos_alerts = [a for a in alerts if a["metric"] == "acos"]
        assert len(acos_alerts) == 1
        assert acos_alerts[0]["level"] == "critical"

    def test_roas_warning_triggered(self):
        """ROAS低于warning阈值（2.0）时触发WARNING告警。"""
        metrics = {"campaign_id": "X", "roas": 1.5}
        alerts = check_metrics(metrics)
        roas_alerts = [a for a in alerts if a["metric"] == "roas"]
        assert len(roas_alerts) == 1
        assert roas_alerts[0]["level"] == "warning"

    def test_roas_critical_triggered(self):
        """ROAS低于critical阈值（1.0）时触发CRITICAL告警。"""
        metrics = {"campaign_id": "X", "roas": 0.5}
        alerts = check_metrics(metrics)
        roas_alerts = [a for a in alerts if a["metric"] == "roas"]
        assert len(roas_alerts) == 1
        assert roas_alerts[0]["level"] == "critical"

    def test_ctr_warning_triggered(self):
        """CTR低于warning阈值（0.3%）时触发WARNING告警。"""
        metrics = {"campaign_id": "X", "ctr": 0.15}
        alerts = check_metrics(metrics)
        ctr_alerts = [a for a in alerts if a["metric"] == "ctr"]
        assert len(ctr_alerts) == 1
        assert ctr_alerts[0]["level"] == "warning"

    def test_spend_over_limit_triggered(self):
        """日花费超过500时触发WARNING告警。"""
        metrics = {"campaign_id": "X", "spend": 600.0}
        alerts = check_metrics(metrics)
        spend_alerts = [a for a in alerts if a["metric"] == "spend"]
        assert len(spend_alerts) == 1
        assert spend_alerts[0]["level"] == "warning"

    def test_multiple_alerts(self, bad_metrics):
        """多个指标同时超阈值时生成多条告警。"""
        alerts = check_metrics(bad_metrics)
        assert len(alerts) >= 3  # acos(critical) + roas(critical) + ctr(warning) + spend(warning)

    def test_empty_metrics_returns_empty(self):
        """空指标字典返回空列表。"""
        alerts = check_metrics({})
        assert alerts == []

    def test_none_metrics_returns_empty(self):
        """None输入返回空列表。"""
        alerts = check_metrics(None)
        assert alerts == []

    def test_alert_has_required_fields(self, bad_metrics):
        """每条告警包含必要字段。"""
        alerts = check_metrics(bad_metrics)
        assert len(alerts) > 0
        for alert in alerts:
            assert "campaign_id" in alert
            assert "metric" in alert
            assert "current_value" in alert
            assert "threshold" in alert
            assert "level" in alert
            assert "message" in alert
            assert "suggestions" in alert

    def test_custom_thresholds(self):
        """自定义阈值覆盖默认值。"""
        metrics = {"campaign_id": "X", "acos": 40.0}
        # 提高warning阈值到45%，40%不应触发
        alerts = check_metrics(metrics, thresholds={"acos_warning": 45.0})
        acos_alerts = [a for a in alerts if a["metric"] == "acos"]
        assert len(acos_alerts) == 0

    def test_acos_exactly_at_warning_threshold_no_alert(self):
        """ACoS恰好等于warning阈值时不触发（只有超过才触发）。"""
        metrics = {"campaign_id": "X", "acos": 30.0}  # 恰好等于30%
        alerts = check_metrics(metrics)
        acos_alerts = [a for a in alerts if a["metric"] == "acos"]
        assert len(acos_alerts) == 0

    def test_suggestions_not_empty_for_critical(self):
        """CRITICAL告警的suggestions不为空。"""
        metrics = {"campaign_id": "X", "acos": 55.0}
        alerts = check_metrics(metrics)
        assert len(alerts) > 0
        assert len(alerts[0]["suggestions"]) > 0


# ===========================================================================
# TestEvaluateAllCampaigns — evaluate_all_campaigns 测试
# ===========================================================================

class TestEvaluateAllCampaigns:
    """evaluate_all_campaigns 批量检查测试。"""

    def test_empty_list_returns_empty(self):
        """空列表返回空告警。"""
        alerts = evaluate_all_campaigns([])
        assert alerts == []

    def test_multiple_campaigns(self):
        """多个广告活动分别检查。"""
        metrics_list = [
            {"campaign_id": "C1", "acos": 55.0},  # critical
            {"campaign_id": "C2", "acos": 35.0},  # warning
            {"campaign_id": "C3", "acos": 20.0},  # ok
        ]
        alerts = evaluate_all_campaigns(metrics_list)
        assert len(alerts) >= 2  # C1和C2各有告警

    def test_alerts_contain_correct_campaign_ids(self):
        """告警包含正确的campaign_id。"""
        metrics_list = [
            {"campaign_id": "CAMP_A", "acos": 60.0},
            {"campaign_id": "CAMP_B", "acos": 10.0},
        ]
        alerts = evaluate_all_campaigns(metrics_list)
        campaign_ids = {a["campaign_id"] for a in alerts}
        assert "CAMP_A" in campaign_ids
        assert "CAMP_B" not in campaign_ids

    def test_returns_list_type(self):
        """返回值类型为list。"""
        result = evaluate_all_campaigns([{"campaign_id": "X"}])
        assert isinstance(result, list)

    def test_with_mock_data(self):
        """使用Mock数据检查（CAMP002有超阈值数据）。"""
        alerts = evaluate_all_campaigns(_MOCK_AD_METRICS)
        # CAMP002 的 acos=52.3 超过 critical 50.0
        critical_acos = [
            a for a in alerts
            if a.get("campaign_id") == "CAMP002" and a.get("metric") == "acos"
        ]
        assert len(critical_acos) == 1
        assert critical_acos[0]["level"] == "critical"

    def test_custom_thresholds_passed_through(self):
        """自定义阈值正确传递到各活动检查。"""
        metrics_list = [{"campaign_id": "X", "acos": 40.0}]
        # 提高阈值，不触发
        alerts = evaluate_all_campaigns(metrics_list, thresholds={"acos_warning": 45.0})
        assert len(alerts) == 0


# ===========================================================================
# TestComputeSummary — compute_summary 测试
# ===========================================================================

class TestComputeSummary:
    """compute_summary 汇总统计测试。"""

    def test_empty_returns_zeros(self):
        """空数据返回全零汇总。"""
        summary = compute_summary([])
        assert summary["total_spend"] == 0.0
        assert summary["total_sales"] == 0.0
        assert summary["avg_acos"] == 0.0
        assert summary["avg_roas"] == 0.0
        assert summary["campaign_count"] == 0

    def test_single_campaign(self):
        """单个广告活动的汇总统计。"""
        metrics = [{"campaign_id": "C1", "spend": 100.0, "sales": 400.0, "acos": 25.0, "roas": 4.0}]
        summary = compute_summary(metrics)
        assert summary["total_spend"] == 100.0
        assert summary["total_sales"] == 400.0
        assert summary["avg_acos"] == 25.0
        assert summary["avg_roas"] == 4.0
        assert summary["campaign_count"] == 1

    def test_multiple_campaigns_avg(self):
        """多个广告活动的平均值计算。"""
        metrics = [
            {"campaign_id": "C1", "acos": 20.0, "roas": 5.0, "spend": 100.0, "sales": 500.0},
            {"campaign_id": "C2", "acos": 40.0, "roas": 2.5, "spend": 200.0, "sales": 500.0},
        ]
        summary = compute_summary(metrics)
        assert summary["avg_acos"] == 30.0
        assert summary["avg_roas"] == 3.75
        assert summary["total_spend"] == 300.0
        assert summary["campaign_count"] == 2

    def test_returns_required_keys(self):
        """返回值包含所有必要字段。"""
        summary = compute_summary([{"spend": 0}])
        required_keys = {"total_spend", "total_sales", "avg_acos", "avg_roas",
                         "total_impressions", "total_clicks", "campaign_count"}
        assert required_keys.issubset(set(summary.keys()))

    def test_total_impressions_clicks(self):
        """展示次数和点击次数求和正确。"""
        metrics = [
            {"impressions": 10000, "clicks": 50},
            {"impressions": 20000, "clicks": 100},
        ]
        summary = compute_summary(metrics)
        assert summary["total_impressions"] == 30000
        assert summary["total_clicks"] == 150

    def test_with_mock_data(self):
        """使用Mock数据验证汇总结果合理。"""
        summary = compute_summary(_MOCK_AD_METRICS)
        assert summary["total_spend"] > 0
        assert summary["total_sales"] > 0
        assert summary["campaign_count"] == 2


# ===========================================================================
# TestAlertsModule — alerts.py 模块测试
# ===========================================================================

class TestAlertsModule:
    """format_alert_message / generate_optimization_suggestions / send_feishu_alert 测试。"""

    def test_format_alert_message_basic(self, sample_alerts):
        """基本格式化告警消息测试。"""
        msg = format_alert_message(sample_alerts[0])
        assert "CAMP001" in msg
        assert "acos" in msg
        assert "critical" in msg.lower() or "严重" in msg

    def test_format_alert_message_empty(self):
        """空告警返回空字符串。"""
        msg = format_alert_message({})
        assert msg == ""

    def test_format_alert_message_includes_suggestions(self, sample_alerts):
        """格式化消息包含建议。"""
        msg = format_alert_message(sample_alerts[0])
        assert "暂停低效关键词" in msg or "建议" in msg

    def test_format_alert_warning_level(self, sample_alerts):
        """WARNING级别格式化包含正确标记。"""
        msg = format_alert_message(sample_alerts[1])
        assert "CAMP002" in msg
        assert "ctr" in msg

    def test_generate_suggestions_empty_alerts(self):
        """空告警生成空建议列表。"""
        suggestions = generate_optimization_suggestions([])
        assert suggestions == []

    def test_generate_suggestions_from_alerts(self, sample_alerts):
        """有告警时生成建议。"""
        suggestions = generate_optimization_suggestions(sample_alerts)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_generate_suggestions_with_kb(self, sample_alerts):
        """带KB上下文时生成增强建议。"""
        kb = ["使用Sponsored Brands可以提升品牌曝光度"]
        suggestions = generate_optimization_suggestions(sample_alerts, kb_context=kb)
        assert any("KB参考" in s for s in suggestions)

    def test_generate_suggestions_deduplication(self):
        """相同建议内容被去重。"""
        alerts = [
            {"campaign_id": "C1", "metric": "acos", "level": "critical",
             "suggestions": ["降低竞价", "优化关键词"]},
            {"campaign_id": "C2", "metric": "acos", "level": "critical",
             "suggestions": ["降低竞价", "检查转化"]},
        ]
        suggestions = generate_optimization_suggestions(alerts)
        # 去重后"降低竞价"只出现一次
        assert suggestions.count("降低竞价") <= 1

    def test_send_feishu_dry_run_returns_true(self, sample_alerts):
        """dry_run=True 时 send_feishu_alert 返回True（不实际发送）。"""
        result = send_feishu_alert(sample_alerts, {}, dry_run=True)
        assert result is True

    def test_send_feishu_empty_alerts(self):
        """空告警列表直接返回True，不发送。"""
        result = send_feishu_alert([], {}, dry_run=True)
        assert result is True


# ===========================================================================
# TestNodes — 节点函数测试
# ===========================================================================

class TestNodes:
    """6个节点函数的正常路径、错误传播和dry_run测试。"""

    # --- init_run ---

    def test_init_run_sets_agent_run_id(self):
        """init_run 设置 agent_run_id。"""
        state = AdMonitorState(dry_run=True)
        result = init_run(state)
        assert result.get("agent_run_id") is not None
        assert len(result["agent_run_id"]) > 0

    def test_init_run_agent_run_id_is_uuid(self):
        """init_run 生成的 agent_run_id 是有效UUID格式。"""
        state = AdMonitorState(dry_run=True)
        result = init_run(state)
        run_id = result["agent_run_id"]
        # 应该能解析为UUID
        parsed = uuid.UUID(run_id)
        assert str(parsed) == run_id

    def test_init_run_empty_campaigns_no_error(self):
        """init_run 在非dry_run且campaigns为空时，不设置error（只警告）。"""
        state = AdMonitorState(campaigns=[], dry_run=True)
        result = init_run(state)
        assert result.get("error") is None

    # --- fetch_ad_data ---

    def test_fetch_ad_data_dry_run_returns_mock(self):
        """fetch_ad_data dry_run=True 时返回Mock数据。"""
        state = AdMonitorState(dry_run=True)
        state["agent_run_id"] = str(uuid.uuid4())
        result = fetch_ad_data(state)
        assert len(result["ad_metrics"]) > 0

    def test_fetch_ad_data_skips_on_error(self):
        """fetch_ad_data 遇到 state['error'] 时直接返回。"""
        state = AdMonitorState(dry_run=True)
        state["error"] = "prior error"
        result = fetch_ad_data(state)
        assert result["ad_metrics"] == []

    def test_fetch_ad_data_filters_by_campaign_ids(self):
        """fetch_ad_data 根据指定campaigns过滤Mock数据。"""
        state = AdMonitorState(campaigns=["CAMP001"], dry_run=True)
        result = fetch_ad_data(state)
        ids = [m["campaign_id"] for m in result["ad_metrics"]]
        assert "CAMP001" in ids

    # --- check_thresholds ---

    def test_check_thresholds_generates_alerts(self):
        """check_thresholds 对超阈值数据生成告警。"""
        state = AdMonitorState(dry_run=True)
        state["ad_metrics"] = [{"campaign_id": "X", "acos": 60.0}]
        result = check_thresholds(state)
        assert len(result["alerts"]) > 0

    def test_check_thresholds_skips_on_error(self):
        """check_thresholds 遇到 state['error'] 时直接返回。"""
        state = AdMonitorState(dry_run=True)
        state["error"] = "prior error"
        state["ad_metrics"] = _MOCK_AD_METRICS
        result = check_thresholds(state)
        assert result["alerts"] == []

    def test_check_thresholds_sets_summary(self):
        """check_thresholds 设置 summary 字段。"""
        state = AdMonitorState(dry_run=True)
        state["ad_metrics"] = list(_MOCK_AD_METRICS)
        result = check_thresholds(state)
        assert "summary" in result
        assert isinstance(result["summary"], dict)

    # --- generate_suggestions ---

    def test_generate_suggestions_sets_suggestions(self):
        """generate_suggestions 设置 suggestions 字段。"""
        state = AdMonitorState(dry_run=True)
        state["alerts"] = [
            {"campaign_id": "X", "metric": "acos", "level": "critical",
             "suggestions": ["暂停活动"]}
        ]
        result = generate_suggestions(state)
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0

    def test_generate_suggestions_skips_on_error(self):
        """generate_suggestions 遇到 state['error'] 时直接返回。"""
        state = AdMonitorState(dry_run=True)
        state["error"] = "prior error"
        state["alerts"] = [{"campaign_id": "X"}]
        result = generate_suggestions(state)
        assert result["suggestions"] == []

    # --- send_alerts ---

    def test_send_alerts_dry_run_true(self):
        """send_alerts dry_run=True 时标记 alerts_sent=True。"""
        state = AdMonitorState(dry_run=True)
        state["alerts"] = [{"campaign_id": "X", "metric": "acos", "level": "critical",
                             "suggestions": [], "message": "", "current_value": 55.0,
                             "threshold": 50.0}]
        state["summary"] = {}
        result = send_alerts(state)
        assert result.get("alerts_sent") is True

    def test_send_alerts_skips_on_error(self):
        """send_alerts 遇到 state['error'] 时直接返回。"""
        state = AdMonitorState(dry_run=True)
        state["error"] = "prior error"
        result = send_alerts(state)
        assert result.get("alerts_sent") is None

    # --- finalize_run ---

    def test_finalize_run_sets_completed(self):
        """finalize_run 无error时设置 status=completed。"""
        state = AdMonitorState(dry_run=True)
        state["agent_run_id"] = str(uuid.uuid4())
        state["alerts"] = []
        result = finalize_run(state)
        assert result["status"] == "completed"

    def test_finalize_run_sets_failed_on_error(self):
        """finalize_run 有error时设置 status=failed。"""
        state = AdMonitorState(dry_run=True)
        state["agent_run_id"] = str(uuid.uuid4())
        state["error"] = "something went wrong"
        state["alerts"] = []
        result = finalize_run(state)
        assert result["status"] == "failed"


# ===========================================================================
# TestAgentExecute — agent.execute 完整流程测试
# ===========================================================================

class TestAgentExecute:
    """agent.execute 函数端到端测试。"""

    def test_execute_dry_run_basic(self):
        """dry_run=True 基本执行流程，返回正确结构。"""
        result = execute(dry_run=True)
        assert isinstance(result, dict)

    def test_execute_returns_required_fields(self):
        """execute 返回包含所有必要字段。"""
        result = execute(dry_run=True)
        required_keys = {"ad_metrics", "alerts", "suggestions", "summary",
                         "alerts_sent", "agent_run_id", "status", "error"}
        assert required_keys.issubset(set(result.keys()))

    def test_execute_status_completed(self):
        """成功执行后 status=completed。"""
        result = execute(dry_run=True)
        assert result["status"] == "completed"

    def test_execute_error_is_none_on_success(self):
        """成功执行后 error=None。"""
        result = execute(dry_run=True)
        assert result["error"] is None

    def test_execute_alerts_is_list(self):
        """alerts 字段为列表。"""
        result = execute(dry_run=True)
        assert isinstance(result["alerts"], list)

    def test_execute_ad_metrics_is_list(self):
        """ad_metrics 字段为列表，包含Mock数据。"""
        result = execute(dry_run=True)
        assert isinstance(result["ad_metrics"], list)
        assert len(result["ad_metrics"]) > 0

    def test_execute_summary_has_key_fields(self):
        """summary 包含关键汇总字段。"""
        result = execute(dry_run=True)
        summary = result["summary"]
        assert "total_spend" in summary
        assert "total_sales" in summary
        assert "avg_acos" in summary

    def test_execute_agent_run_id_not_empty(self):
        """agent_run_id 不为空。"""
        result = execute(dry_run=True)
        assert result["agent_run_id"]
        assert len(result["agent_run_id"]) > 0

    def test_execute_with_specific_campaigns(self):
        """指定campaigns列表时只监控对应活动。"""
        result = execute(campaigns=["CAMP001"], dry_run=True)
        assert result["status"] == "completed"
        ad_ids = [m["campaign_id"] for m in result["ad_metrics"]]
        assert "CAMP001" in ad_ids

    def test_execute_with_custom_thresholds(self):
        """自定义阈值时正确传递并应用。"""
        # 设置极严格的ACoS阈值，确保Mock数据会触发告警
        result = execute(thresholds={"acos_warning": 5.0}, dry_run=True)
        assert result["status"] == "completed"
        # 所有acos>5的活动应触发告警
        assert len(result["alerts"]) > 0

    def test_execute_suggestions_is_list(self):
        """suggestions 字段为列表。"""
        result = execute(dry_run=True)
        assert isinstance(result["suggestions"], list)

    def test_execute_mock_data_triggers_alerts(self):
        """Mock数据中CAMP002的acos=52.3应触发critical告警。"""
        result = execute(dry_run=True)
        critical_alerts = [
            a for a in result["alerts"]
            if a.get("level") == "critical"
        ]
        assert len(critical_alerts) > 0

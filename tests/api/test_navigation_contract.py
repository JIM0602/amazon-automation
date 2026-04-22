from pathlib import Path


def test_sidebar_uses_more_features_and_returns_route() -> None:
    sidebar = Path("src/frontend/src/components/Sidebar.tsx").read_text(encoding="utf-8")
    app = Path("src/frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "更多功能" in sidebar
    assert "/returns" in sidebar
    assert "AI Agent矩阵" not in sidebar
    assert 'path="returns" element={<ReturnsPage />}' in app


def test_agent_chat_has_back_to_catalog_entry() -> None:
    content = Path("src/frontend/src/pages/AgentChat.tsx").read_text(encoding="utf-8")
    assert "返回更多功能" in content or "navigate('/agents')" in content


def test_approvals_page_uses_agent_history_tab() -> None:
    content = Path("src/frontend/src/pages/ApprovalsPage.tsx").read_text(encoding="utf-8")
    assert "Agent任务历史" in content
    assert "历史记录" not in content


def test_dashboard_uses_tacos_acoas_label() -> None:
    dashboard = Path("src/frontend/src/pages/Dashboard.tsx").read_text(encoding="utf-8")
    trend = Path("src/frontend/src/components/TrendChart.tsx").read_text(encoding="utf-8")
    assert "TACoS / ACoAS" in dashboard
    assert "综合指标" in trend
    assert "趋势图" not in trend


def test_dashboard_top_filters_only_keep_two_ranges() -> None:
    dashboard = Path("src/frontend/src/pages/Dashboard.tsx").read_text(encoding="utf-8")
    assert "(['site_today', 'last_24h'] as TimeRange[])" in dashboard
    assert "this_week" not in dashboard.split("setTimeRange(range)")[0]
    assert "custom" not in dashboard.split("setTimeRange(range)")[0]


def test_trend_chart_uses_tacos_acoas_metric_label() -> None:
    trend = Path("src/frontend/src/components/TrendChart.tsx").read_text(encoding="utf-8")
    assert "label: 'TACoS / ACoAS'" in trend
    assert "广告销售额" in trend
    assert "广告综合指标" not in trend



def test_ads_management_entry_contracts() -> None:
    ad_management = Path("src/frontend/src/pages/AdManagement.tsx").read_text(encoding="utf-8")
    ad_agent = Path("src/frontend/src/pages/AdAgentPage.tsx").read_text(encoding="utf-8")
    assert "site_today" in ad_management
    assert "按 Portfolio、对象层级、广告类型、时间范围和关键词筛选广告对象" in ad_management
    assert "Array.isArray(res.data?.items)" in ad_management
    assert "navigate('/ads/manage')" in ad_agent
    assert "返回广告管理" in ad_agent


def test_orders_page_normalizes_detail_response() -> None:
    orders_page = Path("src/frontend/src/pages/OrdersPage.tsx").read_text(encoding="utf-8")
    assert "function normalizeOrderDetail" in orders_page
    assert "setSelectedOrder(normalizeOrderDetail(response.data))" in orders_page
    assert "basic_info" in orders_page
    assert "shipping_info" in orders_page
    assert "fee_details" in orders_page
    assert "setSelectedOrder(response.data)" not in orders_page


def test_schedules_page_route_contracts() -> None:
    app = Path("src/frontend/src/App.tsx").read_text(encoding="utf-8")
    schedules_page = Path("src/frontend/src/pages/system/SchedulesPage.tsx").read_text(encoding="utf-8")
    system_management = Path("src/frontend/src/pages/SystemManagement.tsx").read_text(encoding="utf-8")

    assert "import SchedulesPage from './pages/system/SchedulesPage'" in app
    assert 'path="system/schedules" element={' in app
    assert '<SchedulesPage />' in app
    assert 'PlaceholderPage title="计划任务"' not in app

    assert '计划任务管理 (Mock)' not in system_management
    assert "navigate('/system/schedules')" in system_management
    assert '真实计划任务页' in system_management

    assert "api.get<SchedulerJob[]>('/scheduler/jobs')" in schedules_page
    assert "api.post(`/scheduler/jobs/${job.id}/${action}`)" in schedules_page
    assert "api.post(`/scheduler/trigger/${job.id}`)" in schedules_page

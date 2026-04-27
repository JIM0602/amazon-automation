import re
from pathlib import Path


def extract_section(source: str, start: str, end: str) -> str:
    match = re.search(rf"{re.escape(start)}[\s\S]*?{re.escape(end)}", source)
    assert match is not None
    return match.group(0)


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
    app = Path("src/frontend/src/App.tsx").read_text(encoding="utf-8")
    ad_management = Path("src/frontend/src/pages/AdManagement.tsx").read_text(encoding="utf-8")
    ad_agent = Path("src/frontend/src/pages/AdAgentPage.tsx").read_text(encoding="utf-8")
    ads_schemas = Path("src/frontend/src/pages/ad-management/adsSchemas.tsx").read_text(encoding="utf-8")
    campaign_builder = extract_section(ads_schemas, "function buildCampaignParams", "function buildAdGroupParams")
    targeting_builder = extract_section(ads_schemas, "function buildTargetingParams", "function buildSearchTermParams")
    assert 'path="ads/manage" element={<AdManagement />}' in app
    assert 'path="ads/manage/campaign/:id" element={<CampaignDetail />}' in app
    assert 'path="ads/manage/ad-group/:id" element={<AdGroupDetail />}' in app
    assert "按 Portfolio、对象层级、广告类型、时间范围和关键词筛选广告对象" in ad_management
    assert "Array.isArray(res.data?.items)" in ad_management
    assert "function buildCampaignParams" in ads_schemas
    assert "function buildAdGroupParams" in ads_schemas
    assert "function buildAdProductParams" in ads_schemas
    assert "function buildTargetingParams" in ads_schemas
    assert "function buildSearchTermParams" in ads_schemas
    assert "function buildNegativeTargetingParams" in ads_schemas
    assert "function buildAdLogParams" in ads_schemas
    assert "buildCommonParams" not in ads_schemas
    assert "service_status: query.serviceStatus === 'all' ? undefined : query.serviceStatus" in campaign_builder
    assert "portfolio_id: query.selectedPortfolioIds[0] || undefined" in campaign_builder
    assert "keyword: query.keyword || undefined" not in campaign_builder
    assert "keyword: query.keyword || undefined" in targeting_builder
    assert "service_status: query.serviceStatus === 'all' ? undefined : query.serviceStatus" not in targeting_builder
    assert "portfolio_id: query.selectedPortfolioIds[0] || undefined" not in targeting_builder
    assert "广告位" not in ad_management
    assert "AMC" not in ad_management
    assert "navigate('/ads/manage')" in ad_agent
    assert "返回广告管理" in ad_agent


def test_ads_management_query_state_contracts() -> None:
    query_state = Path("src/frontend/src/pages/ad-management/state/queryState.ts").read_text(encoding="utf-8")

    assert "activeTab: 'portfolio'" in query_state
    assert "dateRange: 'site_today'" in query_state
    assert "serviceStatus: 'all'" in query_state
    assert "nextParams.set('serviceStatus', query.serviceStatus)" in query_state
    assert "nextParams.set('dateRange', query.dateRange)" in query_state
    assert "nextParams.set('keyword', query.keyword)" in query_state
    assert "nextParams.set('tab', query.activeTab)" in query_state


def test_ads_management_state_skeleton_files_exist() -> None:
    query_state = Path("src/frontend/src/pages/ad-management/state/queryState.ts")
    view_state = Path("src/frontend/src/pages/ad-management/state/viewState.ts")
    action_state = Path("src/frontend/src/pages/ad-management/state/actionState.ts")
    routes_config = Path("src/frontend/src/pages/ad-management/config/routes.ts")
    detail_data = Path("src/frontend/src/pages/ad-management/detail/detailData.ts")
    ad_management = Path("src/frontend/src/pages/AdManagement.tsx").read_text(encoding="utf-8")
    campaign_detail = Path("src/frontend/src/pages/ad-management/CampaignDetail.tsx").read_text(encoding="utf-8")
    ad_group_detail = Path("src/frontend/src/pages/ad-management/AdGroupDetail.tsx").read_text(encoding="utf-8")

    assert query_state.exists()
    assert view_state.exists()
    assert action_state.exists()
    assert routes_config.exists()
    assert detail_data.exists()
    assert "createDefaultQuery" in query_state.read_text(encoding="utf-8")
    assert "AdsViewState" in view_state.read_text(encoding="utf-8")
    assert "AdsActionState" in action_state.read_text(encoding="utf-8")
    assert "getObjectPayload" in detail_data.read_text(encoding="utf-8")
    assert "getListPayload" in detail_data.read_text(encoding="utf-8")
    assert "/ads/manage/campaign/:id" in routes_config.read_text(encoding="utf-8")
    assert "/ads/manage/ad-group/:id" in routes_config.read_text(encoding="utf-8")
    assert "/ads/manage/targeting/:id" in routes_config.read_text(encoding="utf-8")
    assert "/ads/manage/search-term/:id" in routes_config.read_text(encoding="utf-8")
    assert "/ads/manage/negative-targeting/:id" in routes_config.read_text(encoding="utf-8")
    assert "/ads/manage/log/:id" in routes_config.read_text(encoding="utf-8")
    assert "from './ad-management/state/queryState'" in ad_management
    assert "buildQuerySearchParams(query)" in ad_management
    assert "function createDefaultQuery()" not in ad_management
    assert "function parseInitialQuery(searchParams: URLSearchParams)" not in ad_management
    assert "from './detail/detailData'" in campaign_detail
    assert "from './detail/detailData'" in ad_group_detail
    assert "function getObjectPayload" not in campaign_detail
    assert "function getListPayload" not in campaign_detail
    assert "function getObjectPayload" not in ad_group_detail
    assert "function getListPayload" not in ad_group_detail


def test_ads_management_action_skeleton_files_exist() -> None:
    actions_config = Path("src/frontend/src/pages/ad-management/config/actions.ts")
    edit_budget_modal = Path("src/frontend/src/pages/ad-management/actions/EditBudgetModal.tsx")
    change_status_modal = Path("src/frontend/src/pages/ad-management/actions/ChangeStatusModal.tsx")
    edit_bid_drawer = Path("src/frontend/src/pages/ad-management/actions/EditBidDrawer.tsx")
    negative_keyword_modal = Path("src/frontend/src/pages/ad-management/actions/NegativeKeywordModal.tsx")
    batch_action_panel = Path("src/frontend/src/pages/ad-management/actions/BatchActionPanel.tsx")
    confirm_operation_dialog = Path("src/frontend/src/pages/ad-management/actions/ConfirmOperationDialog.tsx")
    action_surface = Path("src/frontend/src/pages/ad-management/actions/ActionSurface.tsx")

    assert actions_config.exists()
    assert edit_budget_modal.exists()
    assert change_status_modal.exists()
    assert edit_bid_drawer.exists()
    assert negative_keyword_modal.exists()
    assert batch_action_panel.exists()
    assert confirm_operation_dialog.exists()
    assert action_surface.exists()

    actions_source = actions_config.read_text(encoding="utf-8")
    assert "ADS_ACTION_REGISTRY" in actions_source
    assert "edit_budget" in actions_source
    assert "change_status" in actions_source
    assert "edit_bid" in actions_source
    assert "add_negative_keyword" in actions_source
    assert "targetType" in actions_source
    assert "level: 'L1'" in actions_source or 'level: "L1"' in actions_source
    assert "ConfirmOperationDialog" in confirm_operation_dialog.read_text(encoding="utf-8")
    edit_budget_source = edit_budget_modal.read_text(encoding="utf-8")
    change_status_source = change_status_modal.read_text(encoding="utf-8")
    edit_bid_source = edit_bid_drawer.read_text(encoding="utf-8")
    negative_keyword_source = negative_keyword_modal.read_text(encoding="utf-8")
    assert "EditBudgetModal" in edit_budget_source
    assert "ChangeStatusModal" in change_status_source
    assert "EditBidDrawer" in edit_bid_source
    assert "NegativeKeywordModal" in negative_keyword_source
    assert "title" in edit_budget_source
    assert "targetLabel" in edit_budget_source
    assert "level" in edit_budget_source
    assert "title" in change_status_source
    assert "targetLabel" in change_status_source
    assert "level" in change_status_source
    assert "title" in edit_bid_source
    assert "targetLabel" in edit_bid_source
    assert "level" in edit_bid_source
    assert "title" in negative_keyword_source
    assert "targetLabel" in negative_keyword_source
    assert "level" in negative_keyword_source
    batch_action_source = batch_action_panel.read_text(encoding="utf-8")
    confirm_dialog_source = confirm_operation_dialog.read_text(encoding="utf-8")
    action_surface_source = action_surface.read_text(encoding="utf-8")
    assert "BatchActionPanel" in batch_action_source
    assert "ActionSurface" in batch_action_source
    assert "title" in batch_action_source
    assert "targetLabel" in batch_action_source
    assert "level" in batch_action_source
    assert "targetCount" in batch_action_source
    assert "ConfirmOperationDialog" in confirm_dialog_source
    assert "ActionSurface" in confirm_dialog_source
    assert "title" in confirm_dialog_source
    assert "targetLabel" in confirm_dialog_source
    assert "level" in confirm_dialog_source
    assert "targetCount" in confirm_dialog_source
    assert "ActionSurface" in action_surface_source
    assert "title" in action_surface_source
    assert "targetLabel" in action_surface_source
    assert "level" in action_surface_source


def test_ads_management_action_registry_is_wired_into_schemas() -> None:
    ads_schemas = Path("src/frontend/src/pages/ad-management/adsSchemas.tsx").read_text(encoding="utf-8")

    assert "from './config/actions'" in ads_schemas
    assert "ADS_ACTION_REGISTRY" in ads_schemas
    assert "ADS_ACTION_REGISTRY.edit_budget" in ads_schemas
    assert "ADS_ACTION_REGISTRY.change_status" in ads_schemas
    assert "ADS_ACTION_REGISTRY.edit_bid" in ads_schemas
    assert "ADS_ACTION_REGISTRY.add_negative_keyword" in ads_schemas
    assert ">编辑<" not in ads_schemas
    assert ">查看<" not in ads_schemas



def test_ads_management_workspace_uses_canonical_detail_routes() -> None:
    ads_schemas = Path("src/frontend/src/pages/ad-management/adsSchemas.tsx").read_text(encoding="utf-8")

    assert "navigateToDetail(context, '/ads/manage/campaign', row)" in ads_schemas
    assert "/ads/management/campaign/${String(row.id ?? '')}" not in ads_schemas
    assert "navigateToDetail(context, '/ads/manage/ad-group', row)" in ads_schemas
    assert "navigateToDetail(context, '/ads/manage/targeting', row)" in ads_schemas
    assert "navigateToDetail(context, '/ads/manage/search-term', row)" in ads_schemas
    assert "navigateToDetail(context, '/ads/manage/negative-targeting', row)" in ads_schemas
    assert "navigateToDetail(context, '/ads/manage/log', row)" in ads_schemas
    assert "context.navigate(`${basePath}/${String(row.id ?? '')}${suffix}`)" in ads_schemas
    assert "title: '广告活动', render: (_, row) => <button" in ads_schemas
    assert "title: '广告组', render: (_, row) => <button" in ads_schemas
    assert "title: '关键词', render: (_, row) => <button" in ads_schemas
    assert "title: '搜索词', render: (_, row) => <button" in ads_schemas
    assert "title: '否定关键词', render: (_, row) => <button" in ads_schemas
    assert "title: '操作时间', render: (_, row) => <button" in ads_schemas



def test_ads_management_detail_navigation_preserves_workspace_query_context() -> None:
    ads_schemas = Path("src/frontend/src/pages/ad-management/adsSchemas.tsx").read_text(encoding="utf-8")
    query_state = Path("src/frontend/src/pages/ad-management/state/queryState.ts").read_text(encoding="utf-8")
    campaign_detail = Path("src/frontend/src/pages/ad-management/CampaignDetail.tsx").read_text(encoding="utf-8")
    ad_group_detail = Path("src/frontend/src/pages/ad-management/AdGroupDetail.tsx").read_text(encoding="utf-8")
    targeting_detail = Path("src/frontend/src/pages/ad-management/detail/TargetingDetailPage.tsx").read_text(encoding="utf-8")
    search_term_detail = Path("src/frontend/src/pages/ad-management/detail/SearchTermDetailPage.tsx").read_text(encoding="utf-8")
    negative_targeting_detail = Path("src/frontend/src/pages/ad-management/detail/NegativeTargetingDetailPage.tsx").read_text(encoding="utf-8")
    log_detail = Path("src/frontend/src/pages/ad-management/detail/LogDetailPage.tsx").read_text(encoding="utf-8")

    assert "buildQuerySearchParams(query).toString()" in ads_schemas
    assert "pageSize" in query_state
    assert "sortBy" in query_state
    assert "sortOrder" in query_state
    assert "nextParams.set('pageSize', String(query.pageSize))" in query_state
    assert "nextParams.set('sortBy', query.sortBy)" in query_state
    assert "nextParams.set('sortOrder', query.sortOrder)" in query_state
    assert "searchParams.get('pageSize')" in query_state
    assert "searchParams.get('sortBy')" in query_state
    assert "searchParams.get('sortOrder')" in query_state
    assert "useLocation" in campaign_detail
    assert "useLocation" in ad_group_detail
    assert "location.search" in campaign_detail
    assert "location.search" in ad_group_detail
    assert "navigate(`/ads/manage${location.search}`)" in campaign_detail
    assert "navigate(`/ads/manage${location.search}`)" in ad_group_detail
    assert "useLocation" in targeting_detail
    assert "useLocation" in search_term_detail
    assert "useLocation" in negative_targeting_detail
    assert "useLocation" in log_detail
    assert "navigate(`/ads/manage${location.search}`)" in targeting_detail
    assert "navigate(`/ads/manage${location.search}`)" in search_term_detail
    assert "navigate(`/ads/manage${location.search}`)" in negative_targeting_detail
    assert "navigate(`/ads/manage${location.search}`)" in log_detail


def test_ads_management_action_state_is_wired_into_page() -> None:
    ad_management = Path("src/frontend/src/pages/AdManagement.tsx").read_text(encoding="utf-8")
    ads_panel = Path("src/frontend/src/pages/ad-management/AdsDataTablePanel.tsx").read_text(encoding="utf-8")
    action_state = Path("src/frontend/src/pages/ad-management/state/actionState.ts").read_text(encoding="utf-8")

    assert "createDefaultActionState" in ad_management
    assert "ConfirmOperationDialog" in ad_management
    assert "BatchActionPanel" in ad_management
    assert "actionState" in ad_management
    assert "setActionState" in ad_management
    assert "onActionTrigger" in ads_panel
    assert "onActionTrigger={handleActionTrigger}" in ad_management
    assert "当前操作" in ad_management
    assert "能力等级" in ad_management
    assert "actionState.level" in ad_management
    assert "actionState.targetIds.length" in ad_management
    assert "currentActionLabel" in ad_management
    assert "currentActionTargetLabel" in ad_management
    assert "actionKey" in ad_management
    assert "targetLabel" in ad_management
    assert "actionKey" in action_state
    assert "targetLabel" in action_state
    assert "message" in action_state
    assert "committed" in action_state
    assert "shouldReload" in action_state
    assert "isRealWrite" in action_state
    assert "actionState.message" in ad_management
    assert "actionState.committed" in ad_management
    assert "actionState.isRealWrite" in ad_management
    assert "actionState.actionName" in ad_management
    assert "actionName: `${action.key}:${currentActionTargetLabel}`" not in ad_management
    assert "row.campaign_name" in ad_management or "row.ad_group_name" in ad_management or "row.keyword" in ad_management
    assert "handleActionClose" in ad_management


def test_edit_budget_modal_renders_interactive_form_contract() -> None:
    source = Path("src/frontend/src/pages/ad-management/actions/EditBudgetModal.tsx").read_text(encoding="utf-8")

    assert 'type="number"' in source
    assert '预算值（USD）' in source
    assert 'placeholder="例如 120"' in source
    assert '预算模式' in source
    assert '<select' in source
    assert '保存预算' in source
    assert '取消' in source
    assert 'ActionSurface' in source


def test_change_status_modal_renders_interactive_form_contract() -> None:
    source = Path("src/frontend/src/pages/ad-management/actions/ChangeStatusModal.tsx").read_text(encoding="utf-8")

    assert '<select' in source
    assert '目标状态' in source
    assert '启用' in source
    assert '暂停' in source
    assert '归档' in source
    assert '确认修改' in source
    assert '取消' in source
    assert 'ActionSurface' in source


def test_ads_management_action_form_submit_flow_contracts() -> None:
    ad_management = Path("src/frontend/src/pages/AdManagement.tsx").read_text(encoding="utf-8")
    edit_budget = Path("src/frontend/src/pages/ad-management/actions/EditBudgetModal.tsx").read_text(encoding="utf-8")
    change_status = Path("src/frontend/src/pages/ad-management/actions/ChangeStatusModal.tsx").read_text(encoding="utf-8")
    edit_bid = Path("src/frontend/src/pages/ad-management/actions/EditBidDrawer.tsx").read_text(encoding="utf-8")
    negative_keyword = Path("src/frontend/src/pages/ad-management/actions/NegativeKeywordModal.tsx").read_text(encoding="utf-8")

    assert "handleActionSubmit" in ad_management
    assert "handleActionCancel" in ad_management
    assert "api.post('/ads/actions'" in ad_management or 'api.post("/ads/actions"' in ad_management
    assert "action_key" in ad_management
    assert "target_type" in ad_management
    assert "target_ids" in ad_management
    assert "payload" in ad_management
    assert "level" in ad_management
    assert "committed" in ad_management
    assert "should_reload" in ad_management
    assert "is_real_write" in ad_management
    assert "onSubmit={handleActionSubmit}" in ad_management
    assert "onCancel={handleActionCancel}" in ad_management
    assert "submitting={actionState.submitting}" in ad_management
    assert "actionState.result" in ad_management
    assert "actionState.submitting" in ad_management
    assert "setReloadKey((value) => value + 1)" in ad_management
    assert "result: 'success'" in ad_management
    assert "result: 'idle'" in ad_management
    assert "submitting: true" in ad_management
    assert "submitting: false" in ad_management
    assert "onSubmit" in edit_budget
    assert "onCancel" in edit_budget
    assert "submitting" in edit_budget
    assert "onSubmit" in change_status
    assert "onCancel" in change_status
    assert "submitting" in change_status
    assert "onSubmit" in edit_bid
    assert "onCancel" in edit_bid
    assert "submitting" in edit_bid
    assert "onSubmit" in negative_keyword
    assert "onCancel" in negative_keyword
    assert "submitting" in negative_keyword
    assert "onSubmit={handleActionSubmit}" in ad_management.split("<EditBidDrawer", 1)[1]
    assert "onCancel={handleActionCancel}" in ad_management.split("<EditBidDrawer", 1)[1]
    assert "onSubmit={handleActionSubmit}" in ad_management.split("<NegativeKeywordModal", 1)[1]
    assert "onCancel={handleActionCancel}" in ad_management.split("<NegativeKeywordModal", 1)[1]
    assert "submitting={actionState.submitting}" in ad_management.split("<EditBidDrawer", 1)[1]
    assert "submitting={actionState.submitting}" in ad_management.split("<NegativeKeywordModal", 1)[1]
    assert "response.data?.level" in ad_management or "response.data.level" in ad_management
    assert "response.data?.committed" in ad_management or "response.data.committed" in ad_management
    assert "response.data?.should_reload" in ad_management or "response.data.should_reload" in ad_management



def test_ads_action_gateway_contracts_exist_in_backend_sources() -> None:
    api_source = Path("src/api/ads.py").read_text(encoding="utf-8")
    mock_source = Path("data/mock/ads.py").read_text(encoding="utf-8")

    assert 'router.post("/actions")' in api_source or "@router.post('/actions')" in api_source
    assert "AdsActionRequest" in api_source
    assert "AdsActionResponse" in api_source
    assert "execute_ads_action" in api_source
    assert "committed" in api_source
    assert "should_reload" in api_source
    assert "is_real_write" in api_source
    assert "level" in api_source
    assert "execute_ads_action" in mock_source
    assert "edit_budget" in mock_source
    assert "change_status" in mock_source
    assert "edit_bid" in mock_source
    assert "add_negative_keyword" in mock_source









def test_edit_bid_drawer_renders_interactive_form_contract() -> None:
    source = Path("src/frontend/src/pages/ad-management/actions/EditBidDrawer.tsx").read_text(encoding="utf-8")

    assert 'type="number"' in source
    assert '竞价值（USD）' in source
    assert 'placeholder="例如 1.2"' in source
    assert '应用范围' in source
    assert '<select' in source
    assert '保存竞价' in source
    assert '取消' in source
    assert 'ActionSurface' in source



def test_negative_keyword_modal_renders_interactive_form_contract() -> None:
    source = Path("src/frontend/src/pages/ad-management/actions/NegativeKeywordModal.tsx").read_text(encoding="utf-8")

    assert '否定关键词' in source
    assert '匹配方式' in source
    assert '<textarea' in source
    assert '<select' in source
    assert '保存否定词' in source
    assert '取消' in source
    assert 'ActionSurface' in source




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

import type { NavigateFunction } from 'react-router-dom'
import type { Column } from '../../types/table'
import { ADS_ACTION_REGISTRY, type AdsActionConfig } from './config/actions'
import { buildQuerySearchParams } from './state/queryState'
import type { AdsQueryState, AdsTableRow, TabKey } from './types'

export interface AdsDataResponse<T extends AdsTableRow> {
  items: T[]
  total_count: number
  summary_row?: Partial<T> | null
}

export interface AdsDataPanelContext {
  navigate: NavigateFunction
  query: AdsQueryState
  onDrillToCampaign: (portfolioId: string) => void
  onActionTrigger: (action: AdsActionConfig, row: AdsTableRow) => void
}

export interface AdsTabSchema<T extends AdsTableRow = AdsTableRow> {
  endpoint: string
  emptyText: string
  getRowKey: (row: T) => string
  buildParams: (query: AdsQueryState) => Record<string, unknown>
  columns: Column<T>[]
}

function formatNumber(value: unknown) {
  return typeof value === 'number' ? value.toLocaleString('en-US') : '0'
}

function formatCurrency(value: unknown) {
  return `$${(typeof value === 'number' ? value : 0).toFixed(2)}`
}

function formatPercent(value: unknown) {
  return `${(((typeof value === 'number' ? value : 0) * 100)).toFixed(2)}%`
}

function renderServiceStatus(value: unknown) {
  const text = String(value ?? '-')
  const colorMap: Record<string, string> = {
    Delivering: 'bg-green-500/20 text-green-400',
    Paused: 'bg-yellow-500/20 text-yellow-400',
    'Out of budget': 'bg-orange-500/20 text-orange-400',
    Ended: 'bg-gray-500/20 text-gray-400',
  }
  return <span className={`rounded px-2 py-0.5 text-xs ${colorMap[text] ?? 'bg-gray-500/20 text-gray-400'}`}>{text}</span>
}

const editBudgetAction = ADS_ACTION_REGISTRY.edit_budget
const changeStatusAction = ADS_ACTION_REGISTRY.change_status
const editBidAction = ADS_ACTION_REGISTRY.edit_bid
const addNegativeKeywordAction = ADS_ACTION_REGISTRY.add_negative_keyword
const changeAdGroupStatusAction: AdsActionConfig = {
  ...changeStatusAction,
  targetType: 'ad_group',
}

function renderActionLabel(action: AdsActionConfig, row: AdsTableRow, onActionTrigger: AdsDataPanelContext['onActionTrigger']) {
  return (
    <button type="button" className="text-blue-500 hover:underline" onClick={() => onActionTrigger(action, row)}>
      {action.label}
      <span className="ml-1 text-xs text-gray-400">{action.level}</span>
    </button>
  )
}

function buildCommonParams(query: AdsQueryState) {
  return {
    page: query.page,
    page_size: query.pageSize,
    ad_type: query.adType,
    service_status: query.serviceStatus === 'all' ? undefined : query.serviceStatus,
    campaign_id: query.campaignId || undefined,
    ad_group_id: query.adGroupId || undefined,
    portfolio_id: query.selectedPortfolioIds[0] || undefined,
    keyword: query.keyword || undefined,
    search_field: query.searchField,
    metric_preset: query.metricPreset || undefined,
    impressions_min: query.advanced.impressionsMin || undefined,
    impressions_max: query.advanced.impressionsMax || undefined,
    clicks_min: query.advanced.clicksMin || undefined,
    clicks_max: query.advanced.clicksMax || undefined,
    spend_min: query.advanced.spendMin || undefined,
    spend_max: query.advanced.spendMax || undefined,
    orders_min: query.advanced.ordersMin || undefined,
    orders_max: query.advanced.ordersMax || undefined,
    acos_min: query.advanced.acosMin ? Number(query.advanced.acosMin) / 100 : undefined,
    acos_max: query.advanced.acosMax ? Number(query.advanced.acosMax) / 100 : undefined,
    sort_by: query.sortBy || undefined,
    sort_order: query.sortOrder || undefined,
  }
}

function buildCampaignParams(query: AdsQueryState) {
  return {
    ...buildCommonParams(query),
  }
}

function buildAdGroupParams(query: AdsQueryState) {
  return {
    ...buildCommonParams(query),
  }
}

function buildAdProductParams(query: AdsQueryState) {
  return {
    ...buildCommonParams(query),
  }
}

function buildTargetingParams(query: AdsQueryState) {
  return {
    ...buildCommonParams(query),
  }
}

function buildSearchTermParams(query: AdsQueryState) {
  return {
    ...buildCommonParams(query),
  }
}

function buildNegativeTargetingParams(query: AdsQueryState) {
  return {
    ...buildCommonParams(query),
  }
}

function buildAdLogParams(query: AdsQueryState) {
  return {
    ...buildCommonParams(query),
  }
}

function navigateToDetail(context: AdsDataPanelContext, basePath: string, row: AdsTableRow) {
  const query = context.query
  const search = buildQuerySearchParams(query).toString()
  const suffix = search ? `?${search}` : ''
  context.navigate(`${basePath}/${String(row.id ?? '')}${suffix}`)
}

export function createAdsSchemas(context: AdsDataPanelContext): Record<TabKey, AdsTabSchema> {
  return {
    portfolio: {
      endpoint: '/ads/portfolios',
      emptyText: '当前筛选下暂无广告组合',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => ({
        page: query.page,
        page_size: query.pageSize,
        portfolio_ids: query.selectedPortfolioIds.length > 0 ? query.selectedPortfolioIds.join(',') : undefined,
        keyword: query.keyword || undefined,
      }),
      columns: [
        { key: 'name', title: '广告组合', render: (_, row) => <button type="button" className="font-medium text-blue-500 hover:underline" onClick={() => context.onDrillToCampaign(String(row.id ?? ''))}>{String(row.name ?? '-')}</button> },
        { key: 'campaign_count', title: '广告活动数量', render: (_, row) => <button type="button" className="text-blue-500 hover:underline" onClick={() => context.onDrillToCampaign(String(row.id ?? ''))}>{formatNumber(row.campaign_count)}</button> },
        { key: 'budget', title: '预算', render: (_, row) => formatCurrency(row.budget) },
        { key: 'campaign_count_total', title: '广告活动数', render: (_, row) => formatNumber(row.campaign_count) },
        { key: 'total_ad_spend', title: '广告花费', render: (_, row) => formatCurrency(row.total_ad_spend ?? row.ad_spend) },
        { key: 'total_ad_sales', title: '广告销售额', render: (_, row) => formatCurrency(row.total_ad_sales ?? row.ad_sales) },
        { key: 'acos', title: 'ACoS', render: (_, row) => formatPercent(row.acos) },
        { key: 'actions', title: '操作', render: (_, row) => renderActionLabel(editBudgetAction, row, context.onActionTrigger) },
      ],
    },
    campaign: {
      endpoint: '/ads/campaigns',
      emptyText: '当前筛选下暂无广告活动',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildCampaignParams(query),
      columns: [
        { key: 'campaign_name', title: '广告活动', render: (_, row) => <button type="button" className="font-medium text-blue-500 hover:underline" onClick={() => navigateToDetail(context, '/ads/manage/campaign', row)}>{String(row.campaign_name ?? row.name ?? '-')}</button> },
        { key: 'service_status', title: '服务状态', render: (_, row) => renderServiceStatus(row.service_status) },
        { key: 'portfolio_name', title: '广告组合', render: (_, row) => String(row.portfolio_name ?? '-') },
        { key: 'ad_type', title: '广告类型', render: (_, row) => String(row.ad_type ?? '-') },
        { key: 'daily_budget', title: '每日预算', render: (_, row) => formatCurrency(row.daily_budget) },
        { key: 'impressions', title: '广告曝光量', render: (_, row) => formatNumber(row.impressions) },
        { key: 'clicks', title: '广告点击量', render: (_, row) => formatNumber(row.clicks) },
        { key: 'ad_spend', title: '广告花费', render: (_, row) => formatCurrency(row.ad_spend) },
        { key: 'acos', title: 'ACoS', render: (_, row) => formatPercent(row.acos) },
        { key: 'actions', title: '操作', render: (_, row) => renderActionLabel(changeStatusAction, row, context.onActionTrigger) },
      ],
    },
    ad_group: {
      endpoint: '/ads/ad_groups',
      emptyText: '当前筛选下暂无广告组',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildAdGroupParams(query),
      columns: [
        { key: 'group_name', title: '广告组', render: (_, row) => <button type="button" className="font-medium text-blue-500 hover:underline" onClick={() => navigateToDetail(context, '/ads/manage/ad-group', row)}>{String(row.group_name ?? row.ad_group_name ?? '-')}</button> },
        { key: 'service_status', title: '服务状态', render: (_, row) => renderServiceStatus(row.service_status) },
        { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
        { key: 'portfolio_name', title: '广告组合', render: (_, row) => String(row.portfolio_name ?? '-') },
        { key: 'default_bid', title: '默认竞价', render: (_, row) => formatCurrency(row.default_bid) },
        { key: 'actions', title: '操作', render: (_, row) => renderActionLabel(changeAdGroupStatusAction, row, context.onActionTrigger) },
      ],
    },
    ad_product: {
      endpoint: '/ads/ad_products',
      emptyText: '当前筛选下暂无广告产品',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildAdProductParams(query),
      columns: [
        { key: 'product_title', title: '广告产品', render: (_, row) => String(row.product_title ?? '-') },
        { key: 'asin', title: 'ASIN', render: (_, row) => String(row.asin ?? '-') },
        { key: 'service_status', title: '服务状态', render: (_, row) => renderServiceStatus(row.service_status) },
        { key: 'price', title: '价格', render: (_, row) => formatCurrency(row.price) },
        { key: 'reviews_count', title: '评论数', render: (_, row) => formatNumber(row.reviews_count) },
        { key: 'rating', title: '评分', render: (_, row) => String(row.rating ?? '-') },
        { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
      ],
    },
    targeting: {
      endpoint: '/ads/targeting',
      emptyText: '当前筛选下暂无投放',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildTargetingParams(query),
      columns: [
        { key: 'keyword', title: '关键词', render: (_, row) => <button type="button" className="font-medium text-blue-500 hover:underline" onClick={() => navigateToDetail(context, '/ads/manage/targeting', row)}>{String(row.keyword ?? '-')}</button> },
        { key: 'service_status', title: '服务状态', render: (_, row) => renderServiceStatus(row.service_status) },
        { key: 'match_type', title: '匹配类型', render: (_, row) => String(row.match_type ?? '-') },
        { key: 'group_name', title: '广告组', render: (_, row) => String(row.group_name ?? row.ad_group_name ?? '-') },
        { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
        { key: 'bid', title: '竞价', render: (_, row) => formatCurrency(row.bid) },
        { key: 'suggested_bid', title: '建议竞价', render: (_, row) => formatCurrency(row.suggested_bid) },
        { key: 'actions', title: '操作', render: (_, row) => renderActionLabel(editBidAction, row, context.onActionTrigger) },
      ],
    },
    search_term: {
      endpoint: '/ads/search_terms',
      emptyText: '当前筛选下暂无搜索词',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildSearchTermParams(query),
      columns: [
        { key: 'search_term', title: '搜索词', render: (_, row) => <button type="button" className="font-medium text-blue-500 hover:underline" onClick={() => navigateToDetail(context, '/ads/manage/search-term', row)}>{String(row.search_term ?? '-')}</button> },
        { key: 'targeting', title: '投放', render: (_, row) => String(row.targeting ?? '-') },
        { key: 'match_type', title: '匹配类型', render: (_, row) => String(row.match_type ?? '-') },
        { key: 'suggested_bid', title: '建议竞价', render: (_, row) => formatCurrency(row.suggested_bid) },
        { key: 'source_bid', title: '源竞价', render: (_, row) => formatCurrency(row.source_bid) },
        { key: 'aba_rank', title: 'ABA排名', render: (_, row) => formatNumber(row.aba_rank) },
        { key: 'actions', title: '操作', render: (_, row) => renderActionLabel(addNegativeKeywordAction, row, context.onActionTrigger) },
      ],
    },
    negative_targeting: {
      endpoint: '/ads/negative_targeting',
      emptyText: '当前筛选下暂无否定投放',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildNegativeTargetingParams(query),
      columns: [
        { key: 'keyword', title: '否定关键词', render: (_, row) => <button type="button" className="font-medium text-blue-500 hover:underline" onClick={() => navigateToDetail(context, '/ads/manage/negative-targeting', row)}>{String(row.keyword ?? row.negative_keyword ?? '-')}</button> },
        { key: 'neg_status', title: '否定状态', render: (_, row) => String(row.neg_status ?? row.status ?? '-') },
        { key: 'match_type', title: '匹配类型', render: (_, row) => String(row.match_type ?? '-') },
        { key: 'group_name', title: '广告组', render: (_, row) => String(row.group_name ?? row.ad_group_name ?? '-') },
        { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
        { key: 'actions', title: '操作', render: (_, row) => renderActionLabel(addNegativeKeywordAction, row, context.onActionTrigger) },
      ],
    },
    ad_placement: {
      endpoint: '/ads/placements',
      emptyText: '广告位数据将在后续接入 Amazon Ads placement 报告后显示',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildCommonParams(query),
      columns: [
        { key: 'placement', title: '广告位', render: (_, row) => String(row.placement ?? '-') },
        { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
        { key: 'impressions', title: '广告曝光量', render: (_, row) => formatNumber(row.impressions) },
        { key: 'clicks', title: '广告点击量', render: (_, row) => formatNumber(row.clicks) },
        { key: 'ad_spend', title: '广告花费', render: (_, row) => formatCurrency(row.ad_spend) },
        { key: 'ad_orders', title: '广告订单量', render: (_, row) => formatNumber(row.ad_orders) },
        { key: 'acos', title: 'ACoS', render: (_, row) => formatPercent(row.acos) },
      ],
    },
    ad_log: {
      endpoint: '/ads/logs',
      emptyText: '当前筛选下暂无广告日志',
      getRowKey: (row) => String(row.id ?? ''),
      buildParams: (query) => buildAdLogParams(query),
      columns: [
        { key: 'operation_time', title: '操作时间', render: (_, row) => <button type="button" className="font-medium text-blue-500 hover:underline" onClick={() => navigateToDetail(context, '/ads/manage/log', row)}>{String(row.operation_time ?? '-')}</button> },
        { key: 'portfolio_name', title: '广告组合', render: (_, row) => String(row.portfolio_name ?? '-') },
        { key: 'ad_type', title: '广告类型', render: (_, row) => String(row.ad_type ?? '-') },
        { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
        { key: 'group_name', title: '广告组', render: (_, row) => String(row.group_name ?? row.ad_group_name ?? '-') },
        { key: 'operation_type', title: '操作类型', render: (_, row) => String(row.operation_type ?? '-') },
        { key: 'operation_content', title: '操作内容', render: (_, row) => String(row.operation_content ?? '-') },
      ],
    },
  }
}

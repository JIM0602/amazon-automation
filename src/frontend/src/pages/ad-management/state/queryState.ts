import type { AdType, AdsMetricPreset, AdsQueryState, AdsSearchField, AdsStrategyFilter, ServiceStatus, TabKey, TimeRange } from '../types'

const TAB_KEYS = new Set<TabKey>(['portfolio', 'campaign', 'ad_group', 'ad_product', 'targeting', 'search_term', 'negative_targeting', 'ad_placement', 'ad_log'])
const AD_TYPES = new Set<AdType>(['SP', 'SB', 'SD', 'ST'])
const TIME_RANGES = new Set<TimeRange>(['site_today', 'last_24h', 'this_week', 'this_month', 'this_year'])
const SERVICE_STATUSES = new Set<ServiceStatus>(['all', 'Delivering', 'Paused', 'Out of budget', 'Ended'])
const SEARCH_FIELDS = new Set<AdsSearchField>(['name', 'asin', 'msku', 'campaign', 'ad_group', 'keyword'])
const STRATEGIES = new Set<AdsStrategyFilter>(['all', 'auto_budget', 'auto_pause', 'dayparting', 'none'])
const METRIC_PRESETS = new Set<AdsMetricPreset>(['has_orders', 'clicks_no_orders', 'impressions_no_clicks', 'no_impressions'])

export const DEFAULT_ADVANCED_FILTERS = {
  impressionsMin: '',
  impressionsMax: '',
  clicksMin: '',
  clicksMax: '',
  spendMin: '',
  spendMax: '',
  ordersMin: '',
  ordersMax: '',
  acosMin: '',
  acosMax: '',
}

export function createDefaultQuery(): AdsQueryState {
  return {
    activeTab: 'portfolio',
    shopId: 'siqiangshangwu',
    adType: 'SP',
    serviceStatus: 'all',
    campaignId: '',
    adGroupId: '',
    strategy: 'all',
    owner: '',
    dateRange: 'site_today',
    compareEnabled: false,
    searchField: 'name',
    selectedPortfolioIds: [],
    portfolioSearch: '',
    keyword: '',
    metricPreset: '',
    filterTemplateId: '',
    advancedOpen: false,
    advanced: { ...DEFAULT_ADVANCED_FILTERS },
    page: 1,
    pageSize: 20,
    sortBy: '',
    sortOrder: null,
  }
}

export function parsePositiveNumber(value: string | null, fallback: number) {
  if (!value) return fallback
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export function parseInitialQuery(searchParams: URLSearchParams): AdsQueryState {
  const defaults = createDefaultQuery()
  const tab = searchParams.get('tab')
  const adType = searchParams.get('adType')
  const serviceStatus = searchParams.get('serviceStatus')
  const dateRange = searchParams.get('dateRange')
  const searchField = searchParams.get('searchField')
  const strategy = searchParams.get('strategy')
  const metricPreset = searchParams.get('metricPreset')
  const portfolios = searchParams.get('portfolio')
  const sortOrder = searchParams.get('sortOrder')

  return {
    ...defaults,
    activeTab: tab && TAB_KEYS.has(tab as TabKey) ? (tab as TabKey) : defaults.activeTab,
    shopId: searchParams.get('shop') || defaults.shopId,
    adType: adType && AD_TYPES.has(adType as AdType) ? (adType as AdType) : defaults.adType,
    serviceStatus: serviceStatus && SERVICE_STATUSES.has(serviceStatus as ServiceStatus)
      ? (serviceStatus as ServiceStatus)
      : defaults.serviceStatus,
    campaignId: searchParams.get('campaignId') || defaults.campaignId,
    adGroupId: searchParams.get('adGroupId') || defaults.adGroupId,
    strategy: strategy && STRATEGIES.has(strategy as AdsStrategyFilter) ? (strategy as AdsStrategyFilter) : defaults.strategy,
    owner: searchParams.get('owner') || defaults.owner,
    dateRange: dateRange && TIME_RANGES.has(dateRange as TimeRange) ? (dateRange as TimeRange) : defaults.dateRange,
    compareEnabled: searchParams.get('compare') === '1',
    searchField: searchField && SEARCH_FIELDS.has(searchField as AdsSearchField) ? (searchField as AdsSearchField) : defaults.searchField,
    selectedPortfolioIds: portfolios ? portfolios.split(',').map((item) => item.trim()).filter(Boolean) : defaults.selectedPortfolioIds,
    portfolioSearch: searchParams.get('portfolioSearch') || defaults.portfolioSearch,
    keyword: searchParams.get('keyword') || defaults.keyword,
    metricPreset: metricPreset && METRIC_PRESETS.has(metricPreset as AdsMetricPreset) ? (metricPreset as AdsMetricPreset) : defaults.metricPreset,
    filterTemplateId: searchParams.get('template') || defaults.filterTemplateId,
    advancedOpen: searchParams.get('advanced') === '1',
    advanced: {
      impressionsMin: searchParams.get('impressionsMin') || '',
      impressionsMax: searchParams.get('impressionsMax') || '',
      clicksMin: searchParams.get('clicksMin') || '',
      clicksMax: searchParams.get('clicksMax') || '',
      spendMin: searchParams.get('spendMin') || '',
      spendMax: searchParams.get('spendMax') || '',
      ordersMin: searchParams.get('ordersMin') || '',
      ordersMax: searchParams.get('ordersMax') || '',
      acosMin: searchParams.get('acosMin') || '',
      acosMax: searchParams.get('acosMax') || '',
    },
    page: parsePositiveNumber(searchParams.get('page'), defaults.page),
    pageSize: parsePositiveNumber(searchParams.get('pageSize'), defaults.pageSize),
    sortBy: searchParams.get('sortBy') || defaults.sortBy,
    sortOrder: sortOrder === 'asc' || sortOrder === 'desc' ? sortOrder : defaults.sortOrder,
  }
}

export function buildQuerySearchParams(query: AdsQueryState) {
  const nextParams = new URLSearchParams()
  nextParams.set('tab', query.activeTab)
  nextParams.set('adType', query.adType)
  nextParams.set('shop', query.shopId)
  nextParams.set('serviceStatus', query.serviceStatus)
  if (query.campaignId) nextParams.set('campaignId', query.campaignId)
  if (query.adGroupId) nextParams.set('adGroupId', query.adGroupId)
  if (query.strategy !== createDefaultQuery().strategy) nextParams.set('strategy', query.strategy)
  if (query.owner) nextParams.set('owner', query.owner)
  nextParams.set('dateRange', query.dateRange)
  if (query.compareEnabled) nextParams.set('compare', '1')
  if (query.searchField !== createDefaultQuery().searchField) nextParams.set('searchField', query.searchField)
  if (query.selectedPortfolioIds.length > 0) {
    nextParams.set('portfolio', query.selectedPortfolioIds.join(','))
  }
  if (query.portfolioSearch) {
    nextParams.set('portfolioSearch', query.portfolioSearch)
  }
  if (query.page > 1) {
    nextParams.set('page', String(query.page))
  }
  if (query.pageSize !== createDefaultQuery().pageSize) {
    nextParams.set('pageSize', String(query.pageSize))
  }
  if (query.keyword) {
    nextParams.set('keyword', query.keyword)
  }
  if (query.metricPreset) nextParams.set('metricPreset', query.metricPreset)
  if (query.filterTemplateId) nextParams.set('template', query.filterTemplateId)
  if (query.advancedOpen) nextParams.set('advanced', '1')
  Object.entries(query.advanced).forEach(([key, value]) => {
    if (value) nextParams.set(key, value)
  })
  if (query.sortBy) {
    nextParams.set('sortBy', query.sortBy)
  }
  if (query.sortOrder) {
    nextParams.set('sortOrder', query.sortOrder)
  }
  return nextParams
}

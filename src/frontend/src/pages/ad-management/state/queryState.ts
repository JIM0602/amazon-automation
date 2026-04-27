import type { AdType, AdsQueryState, ServiceStatus, TabKey, TimeRange } from '../types'

const TAB_KEYS = new Set<TabKey>(['portfolio', 'campaign', 'ad_group', 'ad_product', 'targeting', 'search_term', 'negative_targeting', 'ad_log'])
const AD_TYPES = new Set<AdType>(['SP', 'SB', 'SD', 'ST'])
const TIME_RANGES = new Set<TimeRange>(['site_today', 'last_24h', 'this_week', 'this_month', 'this_year'])
const SERVICE_STATUSES = new Set<ServiceStatus>(['all', 'Delivering', 'Paused', 'Out of budget', 'Ended'])

export function createDefaultQuery(): AdsQueryState {
  return {
    activeTab: 'portfolio',
    shopId: 'siqiangshangwu',
    adType: 'SP',
    serviceStatus: 'all',
    dateRange: 'site_today',
    selectedPortfolioIds: [],
    portfolioSearch: '',
    keyword: '',
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
    dateRange: dateRange && TIME_RANGES.has(dateRange as TimeRange) ? (dateRange as TimeRange) : defaults.dateRange,
    selectedPortfolioIds: portfolios ? portfolios.split(',').map((item) => item.trim()).filter(Boolean) : defaults.selectedPortfolioIds,
    portfolioSearch: searchParams.get('portfolioSearch') || defaults.portfolioSearch,
    keyword: searchParams.get('keyword') || defaults.keyword,
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
  nextParams.set('dateRange', query.dateRange)
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
  if (query.sortBy) {
    nextParams.set('sortBy', query.sortBy)
  }
  if (query.sortOrder) {
    nextParams.set('sortOrder', query.sortOrder)
  }
  return nextParams
}

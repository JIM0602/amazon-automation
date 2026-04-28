import type { SortOrder } from '../../types/table'

export type AdType = 'SP' | 'SB' | 'SD' | 'ST'

export type TabKey =
  | 'portfolio'
  | 'campaign'
  | 'ad_group'
  | 'ad_product'
  | 'targeting'
  | 'search_term'
  | 'negative_targeting'
  | 'ad_placement'
  | 'ad_log'

export type TimeRange = 'site_today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year'

export type ServiceStatus = 'all' | 'Delivering' | 'Paused' | 'Out of budget' | 'Ended'

export type AdsSearchField = 'name' | 'asin' | 'msku' | 'campaign' | 'ad_group' | 'keyword'
export type AdsStrategyFilter = 'all' | 'auto_budget' | 'auto_pause' | 'dayparting' | 'none'
export type AdsMetricPreset = 'has_orders' | 'clicks_no_orders' | 'impressions_no_clicks' | 'no_impressions'

export interface AdsAdvancedFilters {
  impressionsMin: string
  impressionsMax: string
  clicksMin: string
  clicksMax: string
  spendMin: string
  spendMax: string
  ordersMin: string
  ordersMax: string
  acosMin: string
  acosMax: string
}

export interface PortfolioCampaign {
  id: string
  name: string
}

export interface PortfolioNode {
  id: string
  name: string
  campaign_count: number
  campaigns: PortfolioCampaign[]
}

export interface AdsQueryState {
  activeTab: TabKey
  shopId: string
  adType: AdType
  serviceStatus: ServiceStatus
  campaignId: string
  adGroupId: string
  strategy: AdsStrategyFilter
  owner: string
  dateRange: TimeRange
  compareEnabled: boolean
  searchField: AdsSearchField
  selectedPortfolioIds: string[]
  portfolioSearch: string
  keyword: string
  metricPreset: AdsMetricPreset | ''
  filterTemplateId: string
  advancedOpen: boolean
  advanced: AdsAdvancedFilters
  page: number
  pageSize: number
  sortBy: string
  sortOrder: SortOrder
}

export interface AdsTableRow extends Record<string, unknown> {
  id?: string
}

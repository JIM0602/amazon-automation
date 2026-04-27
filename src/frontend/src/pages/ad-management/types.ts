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
  | 'ad_log'

export type TimeRange = 'site_today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year'

export type ServiceStatus = 'all' | 'Delivering' | 'Paused' | 'Out of budget' | 'Ended'

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
  dateRange: TimeRange
  selectedPortfolioIds: string[]
  portfolioSearch: string
  keyword: string
  page: number
  pageSize: number
  sortBy: string
  sortOrder: SortOrder
}

export interface AdsTableRow extends Record<string, unknown> {
  id?: string
}

import PortfolioTab from './PortfolioTab'
import CampaignTab from './CampaignTab'
import AdGroupTab from './AdGroupTab'
import AdProductTab from './AdProductTab'
import TargetingTab from './TargetingTab'
import SearchTermTab from './SearchTermTab'
import NegativeTargetingTab from './NegativeTargetingTab'
import AdLogTab from './AdLogTab'

export type AdType = 'SP' | 'SB' | 'SD' | 'ST'

export type TabKey = 'portfolio' | 'campaign' | 'ad_group' | 'ad_product' | 'targeting' | 'search_term' | 'negative_targeting' | 'ad_log'

export interface TabProps {
  portfolioIds: string[]
  adType: AdType
  timeRange: string
  searchQuery: string
  page: number
  pageSize: number
  onPageChange: (page: number) => void
}

interface TabContentProps extends TabProps {
  activeTab: TabKey
}

export default function TabContent(props: TabContentProps) {
  const commonProps = {
    portfolioIds: props.portfolioIds,
    adType: props.adType,
    timeRange: props.timeRange,
    searchQuery: props.searchQuery,
    page: props.page,
    pageSize: props.pageSize,
    onPageChange: props.onPageChange,
  }

  switch (props.activeTab) {
    case 'portfolio':
      return <PortfolioTab {...commonProps} />
    case 'campaign':
      return <CampaignTab {...commonProps} />
    case 'ad_group':
      return <AdGroupTab {...commonProps} />
    case 'ad_product':
      return <AdProductTab {...commonProps} />
    case 'targeting':
      return <TargetingTab {...commonProps} />
    case 'search_term':
      return <SearchTermTab {...commonProps} />
    case 'negative_targeting':
      return <NegativeTargetingTab {...commonProps} />
    case 'ad_log':
      return <AdLogTab {...commonProps} />
    default:
      return <div className="p-8 text-center text-gray-500 dark:text-gray-400">加载中...</div>
  }
}

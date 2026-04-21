import { useEffect, useMemo, useState } from 'react'
import { Search, RotateCcw } from 'lucide-react'
import api from '../api/client'
import TabContent, { type AdType, type TabKey } from './ad-management/TabContent'

interface PortfolioCampaign {
  id: string
  name: string
}

interface PortfolioNode {
  id: string
  name: string
  campaign_count: number
  campaigns: PortfolioCampaign[]
}

type TimeRange = 'site_today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year'

const TAB_ITEMS: Array<{ key: TabKey; label: string }> = [
  { key: 'portfolio', label: '广告组合' },
  { key: 'campaign', label: '广告活动' },
  { key: 'ad_group', label: '广告组' },
  { key: 'ad_product', label: '广告产品' },
  { key: 'targeting', label: '投放' },
  { key: 'search_term', label: '搜索词' },
  { key: 'negative_targeting', label: '否定投放' },
  { key: 'ad_log', label: '广告日志' },
]

const AD_TYPES: AdType[] = ['SP', 'SB', 'SD', 'ST']

const TIME_RANGE_OPTIONS: Array<{ value: TimeRange; label: string }> = [
  { value: 'site_today', label: '站点今天' },
  { value: 'last_24h', label: '最近24小时' },
  { value: 'this_week', label: '本周' },
  { value: 'this_month', label: '本月' },
  { value: 'this_year', label: '本年' },
]

export default function AdManagement() {
  const [activeTab, setActiveTab] = useState<TabKey>('campaign')
  const [adType, setAdType] = useState<AdType>('SP')
  const [selectedPortfolios, setSelectedPortfolios] = useState<string[]>([])
  const [timeRange, setTimeRange] = useState<TimeRange>('site_today')
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [portfolioSearch, setPortfolioSearch] = useState('')
  const [portfolioTree, setPortfolioTree] = useState<PortfolioNode[]>([])
  const [portfolioLoading, setPortfolioLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    async function fetchPortfolioTree() {
      if (mounted) setPortfolioLoading(true)
      try {
        const res = await api.get('/ads/portfolio_tree')
        if (mounted) {
          const items = Array.isArray(res.data)
            ? res.data
            : Array.isArray(res.data?.items)
              ? res.data.items
              : []
          setPortfolioTree(items)
        }
      } catch (error) {
        if (mounted) setPortfolioTree([])
      } finally {
        if (mounted) setPortfolioLoading(false)
      }
    }

    fetchPortfolioTree()
    return () => {
      mounted = false
    }
  }, [])

  const filteredPortfolios = useMemo(() => {
    const keyword = portfolioSearch.trim().toLowerCase()
    if (!keyword) return portfolioTree
    return portfolioTree.filter((portfolio) => portfolio.name.toLowerCase().includes(keyword))
  }, [portfolioSearch, portfolioTree])

  const allVisibleSelected = filteredPortfolios.length > 0
    && filteredPortfolios.every((portfolio) => selectedPortfolios.includes(portfolio.id))

  const togglePortfolio = (portfolioId: string) => {
    setSelectedPortfolios((current) => (
      current.includes(portfolioId)
        ? current.filter((id) => id !== portfolioId)
        : [...current, portfolioId]
    ))
  }

  const toggleAllVisible = () => {
    setSelectedPortfolios((current) => {
      if (allVisibleSelected) {
        const visibleIds = new Set(filteredPortfolios.map((portfolio) => portfolio.id))
        return current.filter((id) => !visibleIds.has(id))
      }

      const next = new Set(current)
      filteredPortfolios.forEach((portfolio) => next.add(portfolio.id))
      return Array.from(next)
    })
  }

  const handleConfirmPortfolio = () => {
    setPage(1)
  }

  return (
    <div className="mx-auto max-w-[1600px] p-6 text-gray-900 dark:text-gray-100">
      <div className="mb-6 flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">广告管理</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">按 Portfolio、对象层级、广告类型、时间范围和关键词筛选广告对象</p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="grid min-h-[760px] grid-cols-1 lg:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="border-b border-gray-200 bg-gray-50/80 p-4 dark:border-gray-800 dark:bg-gray-950 lg:border-b-0 lg:border-r">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">Portfolio 树</h2>
              <button
                type="button"
                onClick={() => setSelectedPortfolios([])}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-gray-500 transition-colors hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-800"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                清空
              </button>
            </div>

            <div className="mb-3 relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                value={portfolioSearch}
                onChange={(event) => setPortfolioSearch(event.target.value)}
                placeholder="搜索 Portfolio"
                className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-[var(--color-accent)] dark:border-gray-700 dark:bg-gray-900"
              />
            </div>

            <div className="mb-3 flex items-center justify-between rounded-lg border border-dashed border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900">
              <label className="flex items-center gap-2 font-medium">
                <input
                  type="checkbox"
                  checked={allVisibleSelected && filteredPortfolios.length > 0}
                  onChange={toggleAllVisible}
                  className="h-4 w-4 rounded border-gray-300 text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                />
                全部
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">{selectedPortfolios.length} 已选</span>
            </div>

            <div className="max-h-[560px] space-y-1 overflow-y-auto pr-1">
              {portfolioLoading ? (
                <div className="rounded-lg border border-gray-200 bg-white px-3 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
                  加载中...
                </div>
              ) : filteredPortfolios.length === 0 ? (
                <div className="rounded-lg border border-gray-200 bg-white px-3 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
                  暂无 Portfolio
                </div>
              ) : (
                filteredPortfolios.map((portfolio) => {
                  const selected = selectedPortfolios.includes(portfolio.id)
                  return (
                    <label
                      key={portfolio.id}
                      className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2 text-sm transition-colors ${
                        selected
                          ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/5'
                          : 'border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:hover:bg-gray-800'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => togglePortfolio(portfolio.id)}
                        className="mt-1 h-4 w-4 rounded border-gray-300 text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium">{portfolio.name}</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">{portfolio.campaign_count} 个广告活动</span>
                      </span>
                    </label>
                  )
                })
              )}
            </div>

            <button
              type="button"
              onClick={handleConfirmPortfolio}
              className="mt-4 inline-flex w-full items-center justify-center rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              确认选择
            </button>
          </aside>

          <main className="min-w-0 p-4 sm:p-6">
            <div className="mb-4 flex flex-col gap-4 border-b border-gray-200 pb-4 dark:border-gray-800">
              <div className="flex flex-wrap gap-2">
                {TAB_ITEMS.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => {
                      setActiveTab(item.key)
                      setPage(1)
                    }}
                    className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === item.key
                        ? 'bg-[var(--color-accent)] text-white shadow-sm'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex flex-wrap gap-2">
                  {AD_TYPES.map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        setAdType(type)
                        setPage(1)
                      }}
                      className={`inline-flex min-w-14 items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                        adType === type
                          ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>

                <div className="flex flex-wrap items-center gap-3 sm:ml-auto">
                  <div className="flex flex-wrap gap-2">
                    {TIME_RANGE_OPTIONS.map((item) => (
                      <button
                        key={item.value}
                        type="button"
                        onClick={() => {
                          setTimeRange(item.value)
                          setPage(1)
                        }}
                        className={`rounded-lg px-3 py-2 text-sm transition-colors ${
                          timeRange === item.value
                            ? 'bg-[var(--color-accent)]/10 text-[var(--color-accent)] dark:bg-[var(--color-accent)]/20'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                        }`}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>

                  <div className="relative min-w-[220px]">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input
                      value={searchQuery}
                      onChange={(event) => {
                        setSearchQuery(event.target.value)
                        setPage(1)
                      }}
                      placeholder="搜索关键词"
                      className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-[var(--color-accent)] dark:border-gray-700 dark:bg-gray-900"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="min-h-[620px] rounded-2xl border border-gray-200 bg-gray-50/60 p-4 dark:border-gray-800 dark:bg-gray-950">
              <TabContent
                activeTab={activeTab}
                portfolioIds={selectedPortfolios}
                adType={adType}
                timeRange={timeRange}
                searchQuery={searchQuery}
                page={page}
                pageSize={pageSize}
                onPageChange={setPage}
              />
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

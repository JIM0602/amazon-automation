import { RotateCcw, Search } from 'lucide-react'
import type { PortfolioNode } from './types'

interface AdsLeftFilterPanelProps {
  portfolioTree: PortfolioNode[]
  portfolioLoading: boolean
  selectedPortfolioIds: string[]
  portfolioSearch: string
  onPortfolioSearchChange: (value: string) => void
  onPortfolioToggle: (portfolioId: string) => void
  onPortfolioReplaceSelection: (portfolioId: string) => void
  onPortfolioClear: () => void
}

export default function AdsLeftFilterPanel({
  portfolioTree,
  portfolioLoading,
  selectedPortfolioIds,
  portfolioSearch,
  onPortfolioSearchChange,
  onPortfolioToggle,
  onPortfolioReplaceSelection,
  onPortfolioClear,
}: AdsLeftFilterPanelProps) {
  return (
    <aside className="border-b border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-950 lg:border-b-0 lg:border-r">
      <div className="mb-3 grid grid-cols-4 overflow-hidden rounded border border-gray-300 text-xs dark:border-gray-700">
        {['SP', 'SB', 'SD', 'ST'].map((type, index) => (
          <button
            key={type}
            type="button"
            className={`h-8 border-gray-300 dark:border-gray-700 ${index > 0 ? 'border-l' : ''} ${
              type === 'SP' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 dark:bg-gray-900 dark:text-gray-300'
            }`}
          >
            {type}
          </button>
        ))}
      </div>

      <div className="mb-3 flex items-center justify-between border-b border-gray-200 dark:border-gray-800">
        <h2 className="border-b-2 border-blue-600 px-4 pb-2 text-sm font-medium text-blue-600">广告组合</h2>
        <button type="button" className="px-4 pb-2 text-sm text-gray-600 dark:text-gray-400">标签</button>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={onPortfolioClear}
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          全部广告组合
        </button>
        <button type="button" className="text-xs text-blue-600">确认</button>
      </div>

      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          value={portfolioSearch}
          onChange={(event) => onPortfolioSearchChange(event.target.value)}
          placeholder="搜索广告组合"
          className="h-8 w-full rounded border border-gray-300 bg-white py-1 pl-9 pr-3 text-xs outline-none transition-colors placeholder:text-gray-400 focus:border-blue-500 dark:border-gray-700 dark:bg-gray-900"
        />
      </div>

      <div className="mb-2 flex items-center justify-between rounded border border-dashed border-gray-200 bg-gray-50 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <span>可见</span>
          <span>隐藏</span>
          <span>对比</span>
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400">{selectedPortfolioIds.length} 已选</span>
      </div>

      <div className="max-h-[620px] space-y-1 overflow-y-auto pr-1">
        {portfolioLoading ? (
          <div className="rounded border border-gray-200 bg-white px-3 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
            加载中...
          </div>
        ) : portfolioTree.length === 0 ? (
          <div className="rounded border border-gray-200 bg-white px-3 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
            暂无广告组合
          </div>
        ) : (
          portfolioTree.map((portfolio) => {
            const selected = selectedPortfolioIds.includes(portfolio.id)
            return (
              <div
                key={portfolio.id}
                className={`rounded border px-2 py-2 text-sm transition-colors ${
                  selected
                    ? 'border-blue-200 bg-blue-50'
                    : 'border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:hover:bg-gray-800'
                }`}
              >
                <div className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onPortfolioToggle(portfolio.id)}
                    className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{portfolio.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">🇺🇸 Pudiwind-US-美国</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{portfolio.campaign_count} 个广告活动</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onPortfolioReplaceSelection(portfolio.id)}
                  className="mt-2 text-xs text-blue-600 transition-opacity hover:opacity-80"
                >
                  仅筛选此项
                </button>
              </div>
            )
          })
        )}
      </div>
    </aside>
  )
}

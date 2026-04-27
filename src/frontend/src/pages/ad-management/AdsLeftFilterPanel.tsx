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
    <aside className="border-b border-gray-200 bg-gray-50/80 p-4 dark:border-gray-800 dark:bg-gray-950 lg:border-b-0 lg:border-r">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">广告组合</h2>
        <button
          type="button"
          onClick={onPortfolioClear}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-gray-500 transition-colors hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          全部广告组合
        </button>
      </div>

      <div className="mb-3 relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          value={portfolioSearch}
          onChange={(event) => onPortfolioSearchChange(event.target.value)}
          placeholder="搜索广告组合"
          className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-[var(--color-accent)] dark:border-gray-700 dark:bg-gray-900"
        />
      </div>

      <div className="mb-3 flex items-center justify-between rounded-lg border border-dashed border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <span>可见</span>
          <span>隐藏</span>
          <span>对比</span>
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400">{selectedPortfolioIds.length} 已选</span>
      </div>

      <div className="max-h-[560px] space-y-2 overflow-y-auto pr-1">
        {portfolioLoading ? (
          <div className="rounded-lg border border-gray-200 bg-white px-3 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
            加载中...
          </div>
        ) : portfolioTree.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white px-3 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
            暂无广告组合
          </div>
        ) : (
          portfolioTree.map((portfolio) => {
            const selected = selectedPortfolioIds.includes(portfolio.id)
            return (
              <div
                key={portfolio.id}
                className={`rounded-xl border px-3 py-2 text-sm transition-colors ${
                  selected
                    ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/5'
                    : 'border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:hover:bg-gray-800'
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onPortfolioToggle(portfolio.id)}
                    className="mt-1 h-4 w-4 rounded border-gray-300 text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{portfolio.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{portfolio.campaign_count} 个广告活动</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onPortfolioReplaceSelection(portfolio.id)}
                  className="mt-2 text-xs text-[var(--color-accent)] transition-opacity hover:opacity-80"
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

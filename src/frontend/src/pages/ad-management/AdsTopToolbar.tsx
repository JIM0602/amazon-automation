import { RefreshCcw, RotateCcw, Search } from 'lucide-react'
import type { AdType, ServiceStatus, TimeRange } from './types'

interface AdsTopToolbarProps {
  shopId: string
  adType: AdType
  serviceStatus: ServiceStatus
  dateRange: TimeRange
  keyword: string
  onShopChange: (value: string) => void
  onAdTypeChange: (value: AdType) => void
  onServiceStatusChange: (value: ServiceStatus) => void
  onDateRangeChange: (value: TimeRange) => void
  onKeywordChange: (value: string) => void
  onSync: () => void
  onReset: () => void
}

const AD_TYPE_OPTIONS: AdType[] = ['SP', 'SB', 'SD', 'ST']
const SERVICE_STATUS_OPTIONS: Array<{ value: ServiceStatus; label: string }> = [
  { value: 'all', label: '全部状态' },
  { value: 'Delivering', label: '投放中' },
  { value: 'Paused', label: '已暂停' },
  { value: 'Out of budget', label: '预算不足' },
  { value: 'Ended', label: '已结束' },
]
const DATE_RANGE_OPTIONS: Array<{ value: TimeRange; label: string }> = [
  { value: 'site_today', label: '站点今天' },
  { value: 'last_24h', label: '最近24小时' },
  { value: 'this_week', label: '本周' },
  { value: 'this_month', label: '本月' },
  { value: 'this_year', label: '本年' },
]

export default function AdsTopToolbar({
  shopId,
  adType,
  serviceStatus,
  dateRange,
  keyword,
  onShopChange,
  onAdTypeChange,
  onServiceStatusChange,
  onDateRangeChange,
  onKeywordChange,
  onSync,
  onReset,
}: AdsTopToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={shopId}
        onChange={(event) => onShopChange(event.target.value)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)] dark:border-gray-700 dark:bg-gray-900"
      >
        <option value="siqiangshangwu">siqiangshangwu</option>
      </select>

      <div className="flex flex-wrap gap-2">
        {AD_TYPE_OPTIONS.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => onAdTypeChange(type)}
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

      <select
        value={serviceStatus}
        onChange={(event) => onServiceStatusChange(event.target.value as ServiceStatus)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)] dark:border-gray-700 dark:bg-gray-900"
      >
        {SERVICE_STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select
        value={dateRange}
        onChange={(event) => onDateRangeChange(event.target.value as TimeRange)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)] dark:border-gray-700 dark:bg-gray-900"
      >
        {DATE_RANGE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <div className="relative min-w-[220px] sm:ml-auto">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          value={keyword}
          onChange={(event) => onKeywordChange(event.target.value)}
          placeholder="搜索关键词"
          className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-[var(--color-accent)] dark:border-gray-700 dark:bg-gray-900"
        />
      </div>

      <button
        type="button"
        onClick={onSync}
        className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:hover:bg-gray-800"
      >
        <RefreshCcw className="h-4 w-4" />
        同步
      </button>

      <button
        type="button"
        onClick={onReset}
        className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:hover:bg-gray-800"
      >
        <RotateCcw className="h-4 w-4" />
        重置
      </button>
    </div>
  )
}

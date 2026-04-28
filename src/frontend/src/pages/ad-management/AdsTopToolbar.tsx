import { CalendarDays, Grid3X3, RefreshCcw, RotateCcw, Search, SlidersHorizontal } from 'lucide-react'
import type { AdType, AdsAdvancedFilters, AdsMetricPreset, AdsSearchField, AdsStrategyFilter, ServiceStatus, TimeRange } from './types'

interface AdsTopToolbarProps {
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
  keyword: string
  metricPreset: AdsMetricPreset | ''
  filterTemplateId: string
  advancedOpen: boolean
  advanced: AdsAdvancedFilters
  onShopChange: (value: string) => void
  onAdTypeChange: (value: AdType) => void
  onServiceStatusChange: (value: ServiceStatus) => void
  onCampaignChange: (value: string) => void
  onAdGroupChange: (value: string) => void
  onStrategyChange: (value: AdsStrategyFilter) => void
  onOwnerChange: (value: string) => void
  onDateRangeChange: (value: TimeRange) => void
  onCompareChange: (value: boolean) => void
  onSearchFieldChange: (value: AdsSearchField) => void
  onKeywordChange: (value: string) => void
  onMetricPresetChange: (value: AdsMetricPreset | '') => void
  onFilterTemplateChange: (value: string) => void
  onAdvancedOpenChange: (value: boolean) => void
  onAdvancedChange: <K extends keyof AdsAdvancedFilters>(key: K, value: AdsAdvancedFilters[K]) => void
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
const SEARCH_FIELD_OPTIONS: Array<{ value: AdsSearchField; label: string }> = [
  { value: 'name', label: '名称' },
  { value: 'asin', label: 'ASIN' },
  { value: 'msku', label: 'MSKU' },
  { value: 'campaign', label: '广告活动' },
  { value: 'ad_group', label: '广告组' },
  { value: 'keyword', label: '关键词' },
]
const STRATEGY_OPTIONS: Array<{ value: AdsStrategyFilter; label: string }> = [
  { value: 'all', label: '广告策略' },
  { value: 'auto_budget', label: '自动预算' },
  { value: 'auto_pause', label: '自动启停' },
  { value: 'dayparting', label: '分时启停' },
  { value: 'none', label: '未使用' },
]
const METRIC_PRESETS: Array<{ value: AdsMetricPreset; label: string }> = [
  { value: 'has_orders', label: '有成交' },
  { value: 'clicks_no_orders', label: '有点击无成交' },
  { value: 'impressions_no_clicks', label: '有曝光无点击' },
  { value: 'no_impressions', label: '无曝光' },
]
const TEMPLATE_OPTIONS = [
  { value: '', label: '筛选模板' },
  { value: 'high_spend', label: '高花费' },
  { value: 'low_acos', label: '低ACoS' },
  { value: 'needs_attention', label: '待关注' },
]

export default function AdsTopToolbar({
  shopId,
  adType,
  serviceStatus,
  campaignId,
  adGroupId,
  strategy,
  owner,
  dateRange,
  compareEnabled,
  searchField,
  keyword,
  metricPreset,
  filterTemplateId,
  advancedOpen,
  advanced,
  onShopChange,
  onAdTypeChange,
  onServiceStatusChange,
  onCampaignChange,
  onAdGroupChange,
  onStrategyChange,
  onOwnerChange,
  onDateRangeChange,
  onCompareChange,
  onSearchFieldChange,
  onKeywordChange,
  onMetricPresetChange,
  onFilterTemplateChange,
  onAdvancedOpenChange,
  onAdvancedChange,
  onSync,
  onReset,
}: AdsTopToolbarProps) {
  const inputClass = 'h-8 rounded border border-gray-300 bg-white px-2 text-xs outline-none focus:border-blue-500 dark:border-gray-700 dark:bg-gray-900'
  const selectClass = `${inputClass} min-w-[118px]`

  return (
    <div className="bg-white px-4 py-3 dark:bg-gray-900">
      <div className="mb-2 flex items-center justify-between text-xs text-gray-700 dark:text-gray-300">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white">美国太平洋：</span>
          <span>按站点时间统计</span>
        </div>
        <button type="button" className="text-blue-600 hover:underline dark:text-blue-400">SP预算上限</button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select value={shopId} onChange={(event) => onShopChange(event.target.value)} className={selectClass}>
          <option value="siqiangshangwu">全部店铺</option>
        </select>

        <input value={campaignId} onChange={(event) => onCampaignChange(event.target.value)} className={`${inputClass} w-[150px]`} placeholder="广告活动ID/名称" />
        <input value={adGroupId} onChange={(event) => onAdGroupChange(event.target.value)} className={`${inputClass} w-[140px]`} placeholder="广告组ID/名称" />

        <select value={serviceStatus} onChange={(event) => onServiceStatusChange(event.target.value as ServiceStatus)} className={selectClass}>
          {SERVICE_STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>

        <select value={strategy} onChange={(event) => onStrategyChange(event.target.value as AdsStrategyFilter)} className={selectClass}>
          {STRATEGY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>

        <input value={owner} onChange={(event) => onOwnerChange(event.target.value)} className={`${inputClass} w-[100px]`} placeholder="业务员" />

        <select value={dateRange} onChange={(event) => onDateRangeChange(event.target.value as TimeRange)} className={selectClass}>
          {DATE_RANGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>

        <label className="inline-flex h-8 items-center gap-1 text-xs text-gray-700 dark:text-gray-300">
          <input type="checkbox" checked={compareEnabled} onChange={(event) => onCompareChange(event.target.checked)} className="h-3.5 w-3.5 rounded border-gray-300" />
          对比
        </label>

        <div className="inline-flex h-8 overflow-hidden rounded border border-gray-300 bg-white text-xs dark:border-gray-700 dark:bg-gray-900">
          <select value={searchField} onChange={(event) => onSearchFieldChange(event.target.value as AdsSearchField)} className="border-r border-gray-300 bg-transparent px-2 outline-none dark:border-gray-700">
            {SEARCH_FIELD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <span className="inline-flex items-center border-r border-gray-200 px-2 text-gray-500 dark:border-gray-700">
            <Grid3X3 className="h-3.5 w-3.5" />
          </span>
          <input
            value={keyword}
            onChange={(event) => onKeywordChange(event.target.value)}
            placeholder="双击可批量搜索内容"
            className="w-[210px] bg-transparent px-2 text-xs outline-none"
          />
          <button type="button" className="border-l border-gray-200 px-2 font-semibold dark:border-gray-700">精</button>
          <button type="button" className="px-2 text-gray-500">
            <Search className="h-3.5 w-3.5" />
          </button>
        </div>

        <select value={filterTemplateId} onChange={(event) => onFilterTemplateChange(event.target.value)} className={selectClass}>
          {TEMPLATE_OPTIONS.map((option) => (
            <option key={option.value || 'all'} value={option.value}>{option.label}</option>
          ))}
        </select>

        <button type="button" onClick={() => onAdvancedOpenChange(!advancedOpen)} className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-2 text-xs transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:hover:bg-gray-800">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          高级筛选
        </button>

        <button type="button" onClick={onReset} className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-2 text-xs transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:hover:bg-gray-800">
          <RotateCcw className="h-3.5 w-3.5" />
          重置
        </button>

        <button type="button" onClick={onSync} className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-2 text-xs transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:hover:bg-gray-800">
          <RefreshCcw className="h-3.5 w-3.5" />
          同步
        </button>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        {METRIC_PRESETS.map((item) => (
          <button
            key={item.value}
            type="button"
            onClick={() => onMetricPresetChange(metricPreset === item.value ? '' : item.value)}
            className={`rounded border px-2 py-0.5 ${metricPreset === item.value ? 'border-orange-400 bg-orange-100 text-orange-800' : 'border-orange-200 bg-orange-50 text-orange-700'}`}
          >
            {item.label}
          </button>
        ))}
        <div className="flex flex-wrap gap-2">
          {AD_TYPE_OPTIONS.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => onAdTypeChange(type)}
              className={`rounded border px-2 py-0.5 ${adType === type ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300'}`}
            >
              {type}
            </button>
          ))}
        </div>
        <span className="ml-auto inline-flex items-center gap-1 text-gray-500">
          <CalendarDays className="h-3.5 w-3.5" />
          时间按站点口径
        </span>
      </div>

      {advancedOpen ? (
        <div className="mt-3 grid grid-cols-2 gap-2 rounded border border-blue-100 bg-blue-50/50 p-3 text-xs md:grid-cols-5 dark:border-blue-900/60 dark:bg-blue-950/20">
          <RangeInput label="曝光量" min={advanced.impressionsMin} max={advanced.impressionsMax} onMin={(value) => onAdvancedChange('impressionsMin', value)} onMax={(value) => onAdvancedChange('impressionsMax', value)} />
          <RangeInput label="点击量" min={advanced.clicksMin} max={advanced.clicksMax} onMin={(value) => onAdvancedChange('clicksMin', value)} onMax={(value) => onAdvancedChange('clicksMax', value)} />
          <RangeInput label="花费" min={advanced.spendMin} max={advanced.spendMax} onMin={(value) => onAdvancedChange('spendMin', value)} onMax={(value) => onAdvancedChange('spendMax', value)} />
          <RangeInput label="订单量" min={advanced.ordersMin} max={advanced.ordersMax} onMin={(value) => onAdvancedChange('ordersMin', value)} onMax={(value) => onAdvancedChange('ordersMax', value)} />
          <RangeInput label="ACoS %" min={advanced.acosMin} max={advanced.acosMax} onMin={(value) => onAdvancedChange('acosMin', value)} onMax={(value) => onAdvancedChange('acosMax', value)} />
        </div>
      ) : null}
    </div>
  )
}

function RangeInput({
  label,
  min,
  max,
  onMin,
  onMax,
}: {
  label: string
  min: string
  max: string
  onMin: (value: string) => void
  onMax: (value: string) => void
}) {
  return (
    <label className="flex items-center gap-1">
      <span className="w-14 shrink-0 text-gray-600 dark:text-gray-300">{label}</span>
      <input value={min} onChange={(event) => onMin(event.target.value)} className="h-7 min-w-0 flex-1 rounded border border-gray-300 bg-white px-2 outline-none focus:border-blue-500 dark:border-gray-700 dark:bg-gray-900" placeholder="最小" />
      <span className="text-gray-400">~</span>
      <input value={max} onChange={(event) => onMax(event.target.value)} className="h-7 min-w-0 flex-1 rounded border border-gray-300 bg-white px-2 outline-none focus:border-blue-500 dark:border-gray-700 dark:bg-gray-900" placeholder="最大" />
    </label>
  )
}

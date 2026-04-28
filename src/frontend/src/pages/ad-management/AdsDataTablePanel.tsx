import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Columns3, Download, HelpCircle, Plus, RefreshCcw, Settings, TimerReset } from 'lucide-react'
import api from '../../api/client'
import { DataTable } from '../../components/DataTable'
import type { DataTableSelection } from '../../components/DataTable'
import { createAdsSchemas, type AdsDataResponse } from './adsSchemas'
import type { AdsQueryState, AdsTableRow } from './types'

interface AdsDataTablePanelProps {
  query: AdsQueryState
  reloadKey: number
  onPageChange: (page: number, pageSize: number) => void
  onSortChange: (key: string, order: 'asc' | 'desc' | null) => void
  onDrillToCampaign: (portfolioId: string) => void
  onActionTrigger: Parameters<typeof createAdsSchemas>[0]['onActionTrigger']
  selection?: DataTableSelection
}

const TAB_ACTION_LABEL: Record<string, string> = {
  portfolio: '创建广告组合',
  campaign: '创建广告',
  ad_group: '添加广告组',
  ad_product: '添加广告产品',
  targeting: '添加投放',
  search_term: '添加到投放/否定',
  negative_targeting: '添加否定投放',
  ad_log: '导出日志',
}

export default function AdsDataTablePanel({
  query,
  reloadKey,
  onPageChange,
  onSortChange,
  onDrillToCampaign,
  onActionTrigger,
  selection,
}: AdsDataTablePanelProps) {
  const navigate = useNavigate()
  const schemas = useMemo(
    () => createAdsSchemas({ navigate, query, onDrillToCampaign, onActionTrigger }),
    [navigate, onActionTrigger, onDrillToCampaign, query],
  )
  const schema = schemas[query.activeTab]
  const [data, setData] = useState<AdsTableRow[]>([])
  const [total, setTotal] = useState(0)
  const [summaryRow, setSummaryRow] = useState<Partial<AdsTableRow> | undefined>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [columnPanelOpen, setColumnPanelOpen] = useState(false)
  const storageKey = `ads-visible-columns-${query.activeTab}`
  const [visibleColumns, setVisibleColumns] = useState<string[]>(() => {
    try {
      const saved = window.localStorage.getItem(storageKey)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(storageKey)
      setVisibleColumns(saved ? JSON.parse(saved) : [])
    } catch {
      setVisibleColumns([])
    }
  }, [storageKey])

  const effectiveColumns = useMemo(() => {
    if (visibleColumns.length === 0) return schema.columns
    const allowed = new Set(visibleColumns)
    return schema.columns.filter((column) => allowed.has(column.key) || column.key === 'actions')
  }, [schema.columns, visibleColumns])

  const toggleColumn = (key: string) => {
    const allKeys = schema.columns.map((column) => column.key)
    const current = visibleColumns.length > 0 ? visibleColumns : allKeys
    const next = current.includes(key) ? current.filter((item) => item !== key) : [...current, key]
    setVisibleColumns(next)
    window.localStorage.setItem(storageKey, JSON.stringify(next))
  }

  const resetColumns = () => {
    setVisibleColumns([])
    window.localStorage.removeItem(storageKey)
  }

  useEffect(() => {
    let alive = true

    async function fetchData() {
      setLoading(true)
      setError('')
      try {
        const response = await api.get<AdsDataResponse<AdsTableRow>>(schema.endpoint, {
          params: schema.buildParams(query),
        })
        if (!alive) return
        setData(response.data.items || [])
        setTotal(response.data.total_count || 0)
        setSummaryRow(response.data.summary_row || undefined)
      } catch {
        if (!alive) return
        setError('数据加载失败，请重试')
        setData([])
        setTotal(0)
        setSummaryRow(undefined)
      } finally {
        if (alive) setLoading(false)
      }
    }

    fetchData()
    return () => {
      alive = false
    }
  }, [schema, query, reloadKey])

  if (error) {
    return (
      <div className="rounded border border-dashed border-gray-300 bg-gray-50 px-4 py-8 text-center text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
        {error}
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="flex min-h-12 flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-3 py-2 dark:border-gray-800">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="inline-flex h-8 items-center gap-1 rounded bg-blue-600 px-3 text-xs font-medium text-white hover:bg-blue-700">
            <Plus className="h-3.5 w-3.5" />
            {TAB_ACTION_LABEL[query.activeTab]}
          </button>
          {['调整', '添加标签', '添加预警', '复制'].map((label) => (
            <button
              key={label}
              type="button"
              className="h-8 rounded border border-gray-300 px-3 text-xs text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300"
              disabled
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-700 dark:text-gray-300">
          <label className="inline-flex items-center gap-1">
            <input type="checkbox" className="h-3.5 w-3.5 rounded border-gray-300" />
            显示图表
          </label>
          <button type="button" onClick={() => setColumnPanelOpen((value) => !value)} className="inline-flex items-center gap-1 hover:text-blue-600">
            <Settings className="h-4 w-4" />
            自定义列
          </button>
          <TimerReset className="h-4 w-4" />
          <RefreshCcw className="h-4 w-4" />
          <Download className="h-4 w-4" />
          <Columns3 className="h-4 w-4" />
          <HelpCircle className="h-4 w-4" />
        </div>
      </div>

      {columnPanelOpen ? (
        <div className="border-b border-gray-200 bg-gray-50 px-3 py-2 text-xs dark:border-gray-800 dark:bg-gray-950">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-medium text-gray-700 dark:text-gray-200">自定义列（本地保存）</span>
            <button type="button" onClick={resetColumns} className="text-blue-600 hover:underline">恢复默认</button>
          </div>
          <div className="flex flex-wrap gap-2">
            {schema.columns.filter((column) => column.key !== 'actions').map((column) => {
              const checked = visibleColumns.length === 0 || visibleColumns.includes(column.key)
              return (
                <label key={column.key} className="inline-flex h-7 items-center gap-1 rounded border border-gray-200 bg-white px-2 dark:border-gray-700 dark:bg-gray-900">
                  <input type="checkbox" checked={checked} onChange={() => toggleColumn(column.key)} className="h-3.5 w-3.5 rounded border-gray-300" />
                  {column.title}
                </label>
              )
            })}
          </div>
        </div>
      ) : null}

      <DataTable
        className="min-h-0 flex-1"
        columns={effectiveColumns}
        data={data}
        rowKey={schema.getRowKey}
        loading={loading}
        summaryRow={summaryRow}
        emptyText={query.keyword || query.selectedPortfolioIds.length > 0 ? schema.emptyText : '暂无广告数据'}
        onSort={onSortChange}
        selection={selection}
        pagination={{
          current: query.page,
          pageSize: query.pageSize,
          total,
          onChange: onPageChange,
        }}
      />
    </div>
  )
}

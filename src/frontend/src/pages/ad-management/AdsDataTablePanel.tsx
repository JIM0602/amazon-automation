import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'
import { DataTable } from '../../components/DataTable'
import { createAdsSchemas, type AdsDataResponse } from './adsSchemas'
import type { AdsQueryState, AdsTableRow } from './types'

interface AdsDataTablePanelProps {
  query: AdsQueryState
  reloadKey: number
  onPageChange: (page: number, pageSize: number) => void
  onSortChange: (key: string, order: 'asc' | 'desc' | null) => void
  onDrillToCampaign: (portfolioId: string) => void
  onActionTrigger: Parameters<typeof createAdsSchemas>[0]['onActionTrigger']
}

export default function AdsDataTablePanel({
  query,
  reloadKey,
  onPageChange,
  onSortChange,
  onDrillToCampaign,
  onActionTrigger,
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
      <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-8 text-center text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
        {error}
      </div>
    )
  }

  return (
    <DataTable
      columns={schema.columns}
      data={data}
      rowKey={schema.getRowKey}
      loading={loading}
      summaryRow={summaryRow}
      emptyText={query.keyword || query.selectedPortfolioIds.length > 0 ? schema.emptyText : '暂无广告数据'}
      onSort={onSortChange}
      pagination={{
        current: query.page,
        pageSize: query.pageSize,
        total,
        onChange: onPageChange,
      }}
    />
  )
}

import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../api/client'
import { BatchActionPanel } from './ad-management/actions/BatchActionPanel'
import { ChangeStatusModal, type ChangeStatusFormValue } from './ad-management/actions/ChangeStatusModal'
import { ConfirmOperationDialog } from './ad-management/actions/ConfirmOperationDialog'
import { EditBidDrawer, type EditBidFormValue } from './ad-management/actions/EditBidDrawer'
import { EditBudgetModal, type EditBudgetFormValue } from './ad-management/actions/EditBudgetModal'
import { NegativeKeywordModal, type NegativeKeywordFormValue } from './ad-management/actions/NegativeKeywordModal'
import AdsDataTablePanel from './ad-management/AdsDataTablePanel'
import AdsLeftFilterPanel from './ad-management/AdsLeftFilterPanel'
import AdsObjectTabs from './ad-management/AdsObjectTabs'
import AdsTopToolbar from './ad-management/AdsTopToolbar'
import { ADS_ACTION_REGISTRY, type AdsActionConfig } from './ad-management/config/actions'
import { createDefaultActionState } from './ad-management/state/actionState'
import { buildQuerySearchParams, createDefaultQuery, parseInitialQuery } from './ad-management/state/queryState'
import type { AdsQueryState, AdsTableRow, PortfolioNode, TabKey } from './ad-management/types'

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


export default function AdManagement() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState<AdsQueryState>(() => parseInitialQuery(searchParams))
  const [actionState, setActionState] = useState(() => createDefaultActionState())
  const [reloadKey, setReloadKey] = useState(0)
  const [portfolioTree, setPortfolioTree] = useState<PortfolioNode[]>([])
  const [portfolioLoading, setPortfolioLoading] = useState(true)

  const handleActionTrigger = (action: AdsActionConfig, row: AdsTableRow) => {
    const currentActionTargetLabel = String(
      row.campaign_name ?? row.ad_group_name ?? row.group_name ?? row.keyword ?? row.search_term ?? row.name ?? row.id ?? '-',
    )

    setActionState({
      actionName: action.label,
      actionKey: action.key,
      targetLabel: currentActionTargetLabel,
      targetType: action.targetType,
      targetIds: [String(row.id ?? '')],
      level: action.level,
      dirty: false,
      submitting: false,
      confirmOpen: false,
      committed: null,
      shouldReload: false,
      isRealWrite: null,
      message: null,
      result: 'idle',
    })
  }

  const handleActionClose = () => {
    setActionState((current) => ({
      ...createDefaultActionState(),
      result: current.result,
      committed: current.committed,
      shouldReload: current.shouldReload,
      isRealWrite: current.isRealWrite,
      message: current.message,
    }))
  }

  const handleActionCancel = () => {
    setActionState((current) => ({
      ...current,
      submitting: false,
      confirmOpen: false,
      committed: null,
      shouldReload: false,
      isRealWrite: null,
      message: null,
      result: 'idle',
    }))
    handleActionClose()
  }

  const handleActionSubmit = async (
    value: EditBudgetFormValue | ChangeStatusFormValue | EditBidFormValue | NegativeKeywordFormValue,
  ) => {
    setActionState((current) => ({
      ...current,
      submitting: true,
      result: 'idle',
    }))

    try {
      const response = await api.post('/ads/actions', {
        action_key: actionState.actionKey,
        target_type: actionState.targetType,
        target_ids: actionState.targetIds,
        payload: value,
      })
      if (response.data?.committed) {
        setActionState((current) => ({
          ...current,
          submitting: false,
          committed: response.data?.committed ?? null,
          shouldReload: response.data?.should_reload ?? false,
          isRealWrite: response.data?.is_real_write ?? null,
          message: response.data?.message ?? null,
          result: 'success',
          level: response.data?.level ?? current.level,
        }))
        if (response.data?.should_reload) {
          setReloadKey((value) => value + 1)
        }
        if (response.data?.is_real_write === false || response.data?.is_real_write === true) {
          handleActionClose()
        }
      } else {
        setActionState((current) => ({
          ...current,
          submitting: false,
          committed: response.data?.committed ?? null,
          shouldReload: response.data?.should_reload ?? false,
          isRealWrite: response.data?.is_real_write ?? null,
          message: response.data?.message ?? '提交失败',
          result: 'error',
          level: response.data?.level ?? current.level,
        }))
      }
    } catch {
      setActionState((current) => ({
        ...current,
        submitting: false,
        committed: false,
        shouldReload: false,
        isRealWrite: null,
        message: '广告操作提交失败，请稍后重试。',
        result: 'error',
      }))
    }
  }

  const actionFeedbackLabel = actionState.isRealWrite === null ? '' : actionState.isRealWrite ? '真实写入' : 'Mock 提交'
  const actionReloadLabel = actionState.committed === null ? '' : actionState.shouldReload ? '需要刷新' : '无需刷新'

  const activeActionName = actionState.actionKey ?? ''
  const currentActionTargetLabel = actionState.targetLabel
  const currentActionLabel = activeActionName
    ? ADS_ACTION_REGISTRY[activeActionName]?.label ?? actionState.actionName ?? activeActionName
    : ''

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
      } catch {
        if (mounted) setPortfolioTree([])
      } finally {
        if (mounted) setPortfolioLoading(false)
      }
    }

    fetchPortfolioTree()
    return () => {
      mounted = false
    }
  }, [reloadKey])

  useEffect(() => {
    setSearchParams(buildQuerySearchParams(query), { replace: true })
  }, [query, setSearchParams])

  const filteredPortfolios = useMemo(() => {
    const keyword = query.portfolioSearch.trim().toLowerCase()
    if (!keyword) return portfolioTree
    return portfolioTree.filter((portfolio) => portfolio.name.toLowerCase().includes(keyword))
  }, [portfolioTree, query.portfolioSearch])

  const updateQuery = (updater: (current: AdsQueryState) => AdsQueryState) => {
    setQuery((current) => updater(current))
  }

  const handleFilterChange = <K extends keyof AdsQueryState>(key: K, value: AdsQueryState[K]) => {
    updateQuery((current) => ({ ...current, [key]: value, page: 1 }))
  }

  const handleTabChange = (tab: TabKey) => {
    updateQuery((current) => ({
      ...current,
      activeTab: tab,
      keyword: '',
      sortBy: '',
      sortOrder: null,
      page: 1,
    }))
  }

  const handlePortfolioToggle = (portfolioId: string) => {
    updateQuery((current) => ({
      ...current,
      selectedPortfolioIds: current.selectedPortfolioIds.includes(portfolioId)
        ? current.selectedPortfolioIds.filter((id) => id !== portfolioId)
        : [...current.selectedPortfolioIds, portfolioId],
      page: 1,
    }))
  }

  const handlePortfolioReplaceSelection = (portfolioId: string) => {
    updateQuery((current) => ({
      ...current,
      selectedPortfolioIds: [portfolioId],
      page: 1,
    }))
  }

  const handlePortfolioClear = () => {
    updateQuery((current) => ({
      ...current,
      selectedPortfolioIds: [],
      page: 1,
    }))
  }

  const handleReset = () => {
    updateQuery((current) => ({
      ...createDefaultQuery(),
      activeTab: current.activeTab,
    }))
    setReloadKey((value) => value + 1)
  }

  const handleSync = () => {
    setReloadKey((value) => value + 1)
  }

  const handleDrillToCampaign = (portfolioId: string) => {
    updateQuery((current) => ({
      ...current,
      activeTab: 'campaign',
      selectedPortfolioIds: portfolioId ? [portfolioId] : current.selectedPortfolioIds,
      keyword: '',
      sortBy: '',
      sortOrder: null,
      page: 1,
    }))
  }

  return (
    <div className="mx-auto max-w-[1600px] p-6 text-gray-900 dark:text-gray-100">
      <div className="mb-6 flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">广告管理</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">按 Portfolio、对象层级、广告类型、时间范围和关键词筛选广告对象</p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="grid min-h-[760px] grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)]">
          <AdsLeftFilterPanel
            portfolioTree={filteredPortfolios}
            portfolioLoading={portfolioLoading}
            selectedPortfolioIds={query.selectedPortfolioIds}
            portfolioSearch={query.portfolioSearch}
            onPortfolioSearchChange={(value) => updateQuery((current) => ({ ...current, portfolioSearch: value }))}
            onPortfolioToggle={handlePortfolioToggle}
            onPortfolioReplaceSelection={handlePortfolioReplaceSelection}
            onPortfolioClear={handlePortfolioClear}
          />

          <main className="min-w-0 p-4 sm:p-6">
            <div className="mb-4 flex flex-col gap-4 border-b border-gray-200 pb-4 dark:border-gray-800">
              <AdsObjectTabs items={TAB_ITEMS} activeTab={query.activeTab} onChange={handleTabChange} />
              <AdsTopToolbar
                shopId={query.shopId}
                adType={query.adType}
                serviceStatus={query.serviceStatus}
                dateRange={query.dateRange}
                keyword={query.keyword}
                onShopChange={(value) => handleFilterChange('shopId', value)}
                onAdTypeChange={(value) => handleFilterChange('adType', value)}
                onServiceStatusChange={(value) => handleFilterChange('serviceStatus', value)}
                onDateRangeChange={(value) => handleFilterChange('dateRange', value)}
                onKeywordChange={(value) => handleFilterChange('keyword', value)}
                onSync={handleSync}
                onReset={handleReset}
              />
            </div>

            <div className="min-h-[620px] rounded-2xl border border-gray-200 bg-gray-50/60 p-4 dark:border-gray-800 dark:bg-gray-950">
              <AdsDataTablePanel
                query={query}
                reloadKey={reloadKey}
                onPageChange={(page, pageSize) => updateQuery((current) => ({ ...current, page, pageSize }))}
                onSortChange={(key, order) => updateQuery((current) => ({ ...current, sortBy: key, sortOrder: order }))}
                onDrillToCampaign={handleDrillToCampaign}
                onActionTrigger={handleActionTrigger}
              />

              <div className="mt-4">
                {activeActionName ? (
                  <section className="mb-4 rounded-2xl border border-blue-200 bg-blue-50/80 px-4 py-3 text-sm text-blue-900 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-100">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="space-y-1">
                        <div className="font-medium">当前操作：{currentActionLabel}</div>
                        <div className="text-xs text-blue-700 dark:text-blue-300">
                          目标对象：{currentActionTargetLabel} · 能力等级：{actionState.level ?? '-'} · 目标数量：{actionState.targetIds.length}
                          {actionState.submitting ? ' · 提交中' : ''}
                          {actionState.result === 'success' ? ' · 已提交' : ''}
                          {actionState.result === 'error' ? ' · 提交失败' : ''}
                          {actionFeedbackLabel ? ` · ${actionFeedbackLabel}` : ''}
                          {actionReloadLabel ? ` · ${actionReloadLabel}` : ''}
                          {actionState.committed !== null ? ` · committed=${String(actionState.committed)}` : ''}
                        </div>
                        {actionState.message ? <div className="text-xs text-blue-800 dark:text-blue-200">反馈：{actionState.message}</div> : null}
                      </div>
                      <button
                        type="button"
                        className="rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200 dark:hover:bg-blue-900/60"
                        onClick={handleActionClose}
                      >
                        关闭当前操作
                      </button>
                    </div>
                  </section>
                ) : null}
                <BatchActionPanel
                  visible={actionState.targetIds.length > 1}
                  title="批量操作"
                  targetLabel={currentActionTargetLabel}
                  level={actionState.level}
                  targetCount={actionState.targetIds.length}
                />
                <EditBudgetModal
                  open={activeActionName === 'edit_budget'}
                  title={currentActionLabel}
                  targetLabel={currentActionTargetLabel}
                  level={actionState.level}
                  submitting={actionState.submitting}
                  onCancel={handleActionCancel}
                  onSubmit={handleActionSubmit}
                />
                <ChangeStatusModal
                  open={activeActionName === 'change_status'}
                  title={currentActionLabel}
                  targetLabel={currentActionTargetLabel}
                  level={actionState.level}
                  submitting={actionState.submitting}
                  onCancel={handleActionCancel}
                  onSubmit={handleActionSubmit}
                />
                <EditBidDrawer
                  open={activeActionName === 'edit_bid'}
                  title={currentActionLabel}
                  targetLabel={currentActionTargetLabel}
                  level={actionState.level}
                  submitting={actionState.submitting}
                  onCancel={handleActionCancel}
                  onSubmit={handleActionSubmit}
                />
                <NegativeKeywordModal
                  open={activeActionName === 'add_negative_keyword'}
                  title={currentActionLabel}
                  targetLabel={currentActionTargetLabel}
                  level={actionState.level}
                  submitting={actionState.submitting}
                  onCancel={handleActionCancel}
                  onSubmit={handleActionSubmit}
                />
                <ConfirmOperationDialog
                  open={actionState.confirmOpen}
                  title={currentActionLabel || '操作确认'}
                  targetLabel={currentActionTargetLabel}
                  level={actionState.level}
                  targetCount={actionState.targetIds.length}
                />
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

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
  { key: 'ad_placement', label: '广告位' },
  { key: 'ad_log', label: '广告日志' },
]

const TAB_LABELS: Record<TabKey, string> = {
  portfolio: '广告组合',
  campaign: '广告活动',
  ad_group: '广告组',
  ad_product: '广告产品',
  targeting: '投放',
  search_term: '搜索词',
  negative_targeting: '否定投放',
  ad_placement: '广告位',
  ad_log: '广告日志',
}

const DISPLAY_TAB_ITEMS: Array<{ key: TabKey; label: string }> = TAB_ITEMS.map((item) => ({
  ...item,
  label: TAB_LABELS[item.key],
}))


export default function AdManagement() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState<AdsQueryState>(() => parseInitialQuery(searchParams))
  const [actionState, setActionState] = useState(() => createDefaultActionState())
  const [reloadKey, setReloadKey] = useState(0)
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set())
  const [pendingActionPayload, setPendingActionPayload] = useState<ChangeStatusFormValue | null>(null)
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
      targetContext: row,
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
    setPendingActionPayload(null)
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
    setPendingActionPayload(null)
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
        payload: buildActionPayload(value),
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
          setSelectedKeys(new Set())
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

  const actionFeedbackLabel = actionState.isRealWrite === null ? '' : actionState.isRealWrite ? '真实写入' : 'Dry-run / 本地记录'
  const actionReloadLabel = actionState.committed === null ? '' : actionState.shouldReload ? '需要刷新' : '无需刷新'

  const activeActionName = actionState.actionKey ?? ''
  const currentActionTargetLabel = actionState.targetLabel
  const currentActionLabel = activeActionName
    ? ADS_ACTION_REGISTRY[activeActionName]?.label ?? actionState.actionName ?? activeActionName
    : ''

  const buildActionPayload = (
    value: EditBudgetFormValue | ChangeStatusFormValue | EditBidFormValue | NegativeKeywordFormValue,
  ) => {
    const context = actionState.targetContext || {}
    const payload: Record<string, unknown> = { ...value }

    if ('budgetValue' in value) {
      payload.daily_budget = Number(value.budgetValue)
    }

    if ('bidValue' in value) {
      payload.bid = Number(value.bidValue)
    }

    if ('keywordText' in value) {
      payload.keyword = value.keywordText
      payload.keyword_text = value.keywordText
      payload.match_type = value.matchType
      payload.campaign_id = context.campaign_id ?? context.campaignId
      payload.ad_group_id = context.ad_group_id ?? context.adGroupId
    }

    if (actionState.targetType === 'campaign') {
      payload.campaign_id = context.campaign_id ?? actionState.targetIds[0]
    }
    if (actionState.targetType === 'ad_group') {
      payload.ad_group_id = context.ad_group_id ?? actionState.targetIds[0]
      payload.campaign_id = context.campaign_id ?? payload.campaign_id
    }

    return payload
  }

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

  const handleBatchAction = (actionKey: string) => {
    if (actionKey === 'clear') {
      setSelectedKeys(new Set())
      return
    }

    const ids = Array.from(selectedKeys)
    if (ids.length === 0) return

    const batchStatusMap: Record<string, ChangeStatusFormValue['nextStatus']> = {
      change_status_enabled: 'enabled',
      change_status_paused: 'paused',
    }

    const nextStatus = batchStatusMap[actionKey]
    setPendingActionPayload(nextStatus ? { nextStatus } : null)

    setActionState({
      actionName: actionKey === 'change_status_enabled' ? '批量启用' : actionKey === 'change_status_paused' ? '批量暂停' : '批量修改预算',
      actionKey: actionKey === 'change_status_enabled' || actionKey === 'change_status_paused' ? 'change_status' : 'edit_budget',
      targetLabel: `已选 ${ids.length} 项`,
      targetType: query.activeTab,
      targetIds: ids,
      targetContext: {},
      level: null,
      dirty: false,
      submitting: false,
      confirmOpen: Boolean(nextStatus),
      committed: null,
      shouldReload: false,
      isRealWrite: null,
      message: null,
      result: 'idle',
    })
  }

  return (
    <div className="min-h-[calc(100vh-64px)] bg-[#eef0f5] p-3 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <div className="overflow-hidden rounded-md border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="border-b border-gray-200 bg-white px-3 pt-2 dark:border-gray-800 dark:bg-gray-900">
          <AdsObjectTabs items={DISPLAY_TAB_ITEMS} activeTab={query.activeTab} onChange={handleTabChange} />
          <AdsTopToolbar
            shopId={query.shopId}
            adType={query.adType}
            serviceStatus={query.serviceStatus}
            campaignId={query.campaignId}
            adGroupId={query.adGroupId}
            strategy={query.strategy}
            owner={query.owner}
            dateRange={query.dateRange}
            compareEnabled={query.compareEnabled}
            searchField={query.searchField}
            keyword={query.keyword}
            metricPreset={query.metricPreset}
            filterTemplateId={query.filterTemplateId}
            advancedOpen={query.advancedOpen}
            advanced={query.advanced}
            onShopChange={(value) => handleFilterChange('shopId', value)}
            onAdTypeChange={(value) => handleFilterChange('adType', value)}
            onServiceStatusChange={(value) => handleFilterChange('serviceStatus', value)}
            onCampaignChange={(value) => handleFilterChange('campaignId', value)}
            onAdGroupChange={(value) => handleFilterChange('adGroupId', value)}
            onStrategyChange={(value) => handleFilterChange('strategy', value)}
            onOwnerChange={(value) => handleFilterChange('owner', value)}
            onDateRangeChange={(value) => handleFilterChange('dateRange', value)}
            onCompareChange={(value) => handleFilterChange('compareEnabled', value)}
            onSearchFieldChange={(value) => handleFilterChange('searchField', value)}
            onKeywordChange={(value) => handleFilterChange('keyword', value)}
            onMetricPresetChange={(value) => handleFilterChange('metricPreset', value)}
            onFilterTemplateChange={(value) => handleFilterChange('filterTemplateId', value)}
            onAdvancedOpenChange={(value) => handleFilterChange('advancedOpen', value)}
            onAdvancedChange={(key, value) => handleFilterChange('advanced', { ...query.advanced, [key]: value })}
            onSync={handleSync}
            onReset={handleReset}
          />
        </div>
        <div className="grid min-h-[720px] grid-cols-1 lg:grid-cols-[212px_minmax(0,1fr)]">
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

          <main className="min-w-0 bg-[#eef0f5] p-3 dark:bg-gray-950">
            <div className="min-h-[690px]">
              <AdsDataTablePanel
                query={query}
                reloadKey={reloadKey}
                onPageChange={(page, pageSize) => updateQuery((current) => ({ ...current, page, pageSize }))}
                onSortChange={(key, order) => updateQuery((current) => ({ ...current, sortBy: key, sortOrder: order }))}
                onDrillToCampaign={handleDrillToCampaign}
                onActionTrigger={handleActionTrigger}
                selection={{ selectedKeys, onSelectionChange: setSelectedKeys }}
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
                  visible={selectedKeys.size > 0}
                  targetCount={selectedKeys.size}
                  activeTab={query.activeTab}
                  onBatchAction={handleBatchAction}
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
                  submitting={actionState.submitting}
                  onCancel={handleActionCancel}
                  onConfirm={() => {
                    if (!pendingActionPayload) return
                    return handleActionSubmit(pendingActionPayload)
                  }}
                />
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

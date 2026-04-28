interface BatchActionPanelProps {
  visible?: boolean
  targetCount?: number
  activeTab?: string
  onBatchAction?: (actionKey: string) => void
}

export function BatchActionPanel({
  visible = false,
  targetCount = 0,
  activeTab = '',
  onBatchAction,
}: BatchActionPanelProps) {
  if (!visible || targetCount === 0) {
    return null
  }

  const showBudget = activeTab === 'campaign'

  return (
    <section className="mb-4 rounded-2xl border border-purple-200 bg-purple-50/80 px-4 py-3 text-sm text-purple-900 dark:border-purple-900/60 dark:bg-purple-950/40 dark:text-purple-100">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="font-medium">
          批量操作 · 已选 <span className="font-bold text-purple-700 dark:text-purple-300">{targetCount}</span> 项
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onBatchAction?.('change_status_enabled')}
            className="rounded-lg border border-green-300 bg-white px-3 py-1.5 text-xs font-medium text-green-700 transition hover:bg-green-50 dark:border-green-700 dark:bg-green-950/40 dark:text-green-300 dark:hover:bg-green-900/40"
          >
            批量启用
          </button>
          <button
            type="button"
            onClick={() => onBatchAction?.('change_status_paused')}
            className="rounded-lg border border-yellow-300 bg-white px-3 py-1.5 text-xs font-medium text-yellow-700 transition hover:bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-300 dark:hover:bg-yellow-900/40"
          >
            批量暂停
          </button>
          {showBudget && (
            <button
              type="button"
              onClick={() => onBatchAction?.('edit_budget')}
              className="rounded-lg border border-blue-300 bg-white px-3 py-1.5 text-xs font-medium text-blue-700 transition hover:bg-blue-50 dark:border-blue-700 dark:bg-blue-950/40 dark:text-blue-300 dark:hover:bg-blue-900/40"
            >
              批量修改预算
            </button>
          )}
          <button
            type="button"
            onClick={() => onBatchAction?.('clear')}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-500 transition hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            清除选择
          </button>
        </div>
      </div>
    </section>
  )
}

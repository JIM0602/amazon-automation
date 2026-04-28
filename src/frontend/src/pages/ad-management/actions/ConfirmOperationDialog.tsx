import { ActionSurface } from './ActionSurface'

interface ConfirmOperationDialogProps {
  open?: boolean
  title?: string
  targetLabel?: string
  level?: string | null
  targetCount?: number
  submitting?: boolean
  onCancel?: () => void
  onConfirm?: () => void | Promise<void>
}

export function ConfirmOperationDialog({
  open = false,
  title = '操作确认',
  targetLabel = '-',
  level = 'L1',
  targetCount = 0,
  submitting = false,
  onCancel,
  onConfirm,
}: ConfirmOperationDialogProps) {
  if (!open) {
    return null
  }

  const handleConfirm = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onConfirm?.()
  }

  return (
    <ActionSurface title={title} targetLabel={targetLabel} level={level} targetCount={targetCount}>
      <form onSubmit={handleConfirm} className="space-y-4 text-gray-700 dark:text-gray-200">
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/50 dark:text-amber-200">
          <p className="font-medium">确认执行此操作？</p>
          <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
            目标对象：{targetLabel}
            {targetCount > 1 ? `（共 ${targetCount} 项）` : ''}
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-1">
          <button
            type="button"
            disabled={submitting}
            onClick={onCancel}
            className="rounded-xl border border-gray-300 px-4 py-2 text-sm text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-400"
          >
            {submitting ? '提交中...' : '确认操作'}
          </button>
        </div>
      </form>
    </ActionSurface>
  )
}

import { useEffect, useState } from 'react'
import { ActionSurface } from './ActionSurface'

export interface ChangeStatusFormValue {
  nextStatus: 'enabled' | 'paused'
}

interface ChangeStatusModalProps {
  open?: boolean
  title?: string
  targetLabel?: string
  level?: string | null
  submitting?: boolean
  onCancel?: () => void
  onSubmit?: (value: ChangeStatusFormValue) => void | Promise<void>
}

export function ChangeStatusModal({
  open = false,
  title = '修改状态',
  targetLabel = '-',
  level = 'L1',
  submitting = false,
  onCancel,
  onSubmit,
}: ChangeStatusModalProps) {
  const [nextStatus, setNextStatus] = useState<'enabled' | 'paused'>('paused')

  useEffect(() => {
    if (open) {
      setNextStatus('paused')
    }
  }, [open])

  if (!open) {
    return null
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit?.({ nextStatus })
  }

  return (
    <ActionSurface title={title} targetLabel={targetLabel} level={level}>
      <form onSubmit={handleSubmit} className="space-y-4 text-gray-700 dark:text-gray-200">
        <label className="block space-y-2 text-sm">
          <span className="font-medium">目标状态</span>
          <select
            value={nextStatus}
            disabled={submitting}
            onChange={(event) => setNextStatus(event.target.value as 'enabled' | 'paused')}
            className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value="enabled">启用</option>
            <option value="paused">暂停</option>
          </select>
        </label>

        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/50 dark:text-amber-200">
          目标对象：{targetLabel}，请确认状态切换后再提交。
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
            {submitting ? '提交中...' : '确认修改'}
          </button>
        </div>
      </form>
    </ActionSurface>
  )
}

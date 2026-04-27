import { useEffect, useState } from 'react'
import { ActionSurface } from './ActionSurface'

export interface EditBidFormValue {
  bidValue: string
  scope: 'current' | 'same_group'
}

interface EditBidDrawerProps {
  open?: boolean
  title?: string
  targetLabel?: string
  level?: string | null
  submitting?: boolean
  onCancel?: () => void
  onSubmit?: (value: EditBidFormValue) => void | Promise<void>
}

export function EditBidDrawer({
  open = false,
  title = '编辑竞价',
  targetLabel = '-',
  level = 'L1',
  submitting = false,
  onCancel,
  onSubmit,
}: EditBidDrawerProps) {
  const [bidValue, setBidValue] = useState('')
  const [scope, setScope] = useState<'current' | 'same_group'>('current')

  useEffect(() => {
    if (open) {
      setBidValue('')
      setScope('current')
    }
  }, [open])

  if (!open) {
    return null
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit?.({ bidValue, scope })
  }

  return (
    <ActionSurface as="aside" title={title} targetLabel={targetLabel} level={level}>
      <form onSubmit={handleSubmit} className="space-y-4 text-gray-700 dark:text-gray-200">
        <label className="block space-y-2 text-sm">
          <span className="font-medium">竞价值（USD）</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={bidValue}
            disabled={submitting}
            onChange={(event) => setBidValue(event.target.value)}
            placeholder="例如 1.2"
            className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          />
        </label>

        <label className="block space-y-2 text-sm">
          <span className="font-medium">应用范围</span>
          <select
            value={scope}
            disabled={submitting}
            onChange={(event) => setScope(event.target.value as 'current' | 'same_group')}
            className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value="current">当前关键词</option>
            <option value="same_group">同步到同广告组</option>
          </select>
        </label>

        <div className="rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-700 dark:border-violet-900/60 dark:bg-violet-950/50 dark:text-violet-200">
          当前为 {level ?? '-'} 能力等级，现阶段先完成前台竞价录入与提交反馈。
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
            {submitting ? '保存中...' : '保存竞价'}
          </button>
        </div>
      </form>
    </ActionSurface>
  )
}

import { useEffect, useState } from 'react'
import { ActionSurface } from './ActionSurface'

export interface EditBudgetFormValue {
  budgetMode: 'daily' | 'lifetime'
  budgetValue: string
}

interface EditBudgetModalProps {
  open?: boolean
  title?: string
  targetLabel?: string
  level?: string | null
  submitting?: boolean
  onCancel?: () => void
  onSubmit?: (value: EditBudgetFormValue) => void | Promise<void>
}

export function EditBudgetModal({
  open = false,
  title = '编辑预算',
  targetLabel = '-',
  level = 'L1',
  submitting = false,
  onCancel,
  onSubmit,
}: EditBudgetModalProps) {
  const [budgetMode, setBudgetMode] = useState<'daily' | 'lifetime'>('daily')
  const [budgetValue, setBudgetValue] = useState('')

  useEffect(() => {
    if (open) {
      setBudgetMode('daily')
      setBudgetValue('')
    }
  }, [open])

  if (!open) {
    return null
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit?.({ budgetMode, budgetValue })
  }

  return (
    <ActionSurface title={title} targetLabel={targetLabel} level={level}>
      <form onSubmit={handleSubmit} className="space-y-4 text-gray-700 dark:text-gray-200">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 text-sm">
            <span className="font-medium">预算模式</span>
            <select
              value={budgetMode}
              disabled={submitting}
              onChange={(event) => setBudgetMode(event.target.value as 'daily' | 'lifetime')}
              className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            >
              <option value="daily">日预算</option>
              <option value="lifetime">生命周期预算</option>
            </select>
          </label>
          <label className="space-y-2 text-sm">
            <span className="font-medium">预算值（USD）</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={budgetValue}
              disabled={submitting}
              onChange={(event) => setBudgetValue(event.target.value)}
              placeholder="例如 120"
              className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            />
          </label>
        </div>

        <div className="rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/50 dark:text-blue-200">
          当前为 {level ?? '-'} 能力等级，现阶段先完成前台表单录入与校验提示。
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
            {submitting ? '保存中...' : '保存预算'}
          </button>
        </div>
      </form>
    </ActionSurface>
  )
}

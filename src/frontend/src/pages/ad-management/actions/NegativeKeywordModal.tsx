import { useEffect, useState } from 'react'
import { ActionSurface } from './ActionSurface'

export interface NegativeKeywordFormValue {
  keywordText: string
  matchType: 'negative_exact' | 'negative_phrase'
}

interface NegativeKeywordModalProps {
  open?: boolean
  title?: string
  targetLabel?: string
  level?: string | null
  submitting?: boolean
  onCancel?: () => void
  onSubmit?: (value: NegativeKeywordFormValue) => void | Promise<void>
}

export function NegativeKeywordModal({
  open = false,
  title = '添加否定词',
  targetLabel = '-',
  level = 'L1',
  submitting = false,
  onCancel,
  onSubmit,
}: NegativeKeywordModalProps) {
  const [keywordText, setKeywordText] = useState('')
  const [matchType, setMatchType] = useState<'negative_exact' | 'negative_phrase'>('negative_phrase')

  useEffect(() => {
    if (open) {
      setKeywordText('')
      setMatchType('negative_phrase')
    }
  }, [open])

  if (!open) {
    return null
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit?.({ keywordText, matchType })
  }

  return (
    <ActionSurface title={title} targetLabel={targetLabel} level={level}>
      <form onSubmit={handleSubmit} className="space-y-4 text-gray-700 dark:text-gray-200">
        <label className="block space-y-2 text-sm">
          <span className="font-medium">否定关键词</span>
          <textarea
            value={keywordText}
            disabled={submitting}
            onChange={(event) => setKeywordText(event.target.value)}
            placeholder="请输入需要屏蔽的搜索词"
            rows={4}
            className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          />
        </label>

        <label className="block space-y-2 text-sm">
          <span className="font-medium">匹配方式</span>
          <select
            value={matchType}
            disabled={submitting}
            onChange={(event) => setMatchType(event.target.value as 'negative_exact' | 'negative_phrase')}
            className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value="negative_phrase">词组否定</option>
            <option value="negative_exact">精确否定</option>
          </select>
        </label>

        <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/50 dark:text-rose-200">
          目标对象：{targetLabel}，现阶段先完成前台否定词录入与提交反馈。
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
            {submitting ? '保存中...' : '保存否定词'}
          </button>
        </div>
      </form>
    </ActionSurface>
  )
}

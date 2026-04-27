import type { ReactNode } from 'react'

interface ActionSurfaceProps {
  as?: 'div' | 'aside' | 'section'
  title?: string
  targetLabel?: string
  level?: string | null
  targetCount?: number
  children: ReactNode
}

export function ActionSurface({
  as = 'div',
  title = '-',
  targetLabel = '-',
  level = 'L1',
  targetCount,
  children,
}: ActionSurfaceProps) {
  const Component = as

  return (
    <Component className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{title}</div>
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        目标对象：{targetLabel} · 能力等级：{level ?? '-'}
        {typeof targetCount === 'number' ? ` · 目标数量：${targetCount}` : ''}
      </div>
      <div className="mt-3 rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
        {children}
      </div>
    </Component>
  )
}

import { ActionSurface } from './ActionSurface'

interface BatchActionPanelProps {
  visible?: boolean
  title?: string
  targetLabel?: string
  level?: string | null
  targetCount?: number
}

export function BatchActionPanel({
  visible = false,
  title = '批量操作',
  targetLabel = '当前筛选结果',
  level = 'L1',
  targetCount = 0,
}: BatchActionPanelProps) {
  if (!visible) {
    return null
  }

  return (
    <ActionSurface as="section" title={title} targetLabel={targetLabel} level={level} targetCount={targetCount}>
      批量操作面板能力建设中。
    </ActionSurface>
  )
}

import { ActionSurface } from './ActionSurface'

interface ConfirmOperationDialogProps {
  open?: boolean
  title?: string
  targetLabel?: string
  level?: string | null
  targetCount?: number
}

export function ConfirmOperationDialog({
  open = false,
  title = '操作确认',
  targetLabel = '-',
  level = 'L1',
  targetCount = 0,
}: ConfirmOperationDialogProps) {
  if (!open) {
    return null
  }

  return <ActionSurface title={title} targetLabel={targetLabel} level={level} targetCount={targetCount}>操作确认对话框能力建设中。</ActionSurface>
}

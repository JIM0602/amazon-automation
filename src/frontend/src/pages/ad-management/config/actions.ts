import type { AdsActionLevel, AdsActionTargetType } from '../state/actionState'

export interface AdsActionConfig {
  key: string
  label: string
  targetType: AdsActionTargetType
  level: AdsActionLevel
  container: 'modal' | 'drawer' | 'panel' | 'dialog'
}

export const ADS_ACTION_REGISTRY: Record<string, AdsActionConfig> = {
  edit_budget: {
    key: 'edit_budget',
    label: '编辑预算',
    targetType: 'campaign',
    level: 'L1',
    container: 'modal',
  },
  change_status: {
    key: 'change_status',
    label: '修改状态',
    targetType: 'campaign',
    level: 'L1',
    container: 'modal',
  },
  edit_bid: {
    key: 'edit_bid',
    label: '编辑竞价',
    targetType: 'targeting',
    level: 'L1',
    container: 'drawer',
  },
  add_negative_keyword: {
    key: 'add_negative_keyword',
    label: '添加否定词',
    targetType: 'negative_targeting',
    level: 'L1',
    container: 'modal',
  },
}

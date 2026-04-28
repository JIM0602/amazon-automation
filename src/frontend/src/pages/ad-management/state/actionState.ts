import type { TabKey } from '../types'

export type AdsActionLevel = 'L1' | 'L2' | 'L3'
export type AdsActionTargetType = TabKey | 'campaign' | 'ad_group' | 'targeting' | 'search_term' | 'negative_targeting' | 'ad_log'

export interface AdsActionState {
  actionName: string | null
  actionKey: string | null
  targetLabel: string
  targetType: AdsActionTargetType | null
  targetIds: string[]
  targetContext: Record<string, unknown>
  level: AdsActionLevel | null
  dirty: boolean
  submitting: boolean
  confirmOpen: boolean
  committed: boolean | null
  shouldReload: boolean
  isRealWrite: boolean | null
  message: string | null
  result: 'idle' | 'success' | 'error'
}

export function createDefaultActionState(): AdsActionState {
  return {
    actionName: null,
    actionKey: null,
    targetLabel: '-',
    targetType: null,
    targetIds: [],
    targetContext: {},
    level: null,
    dirty: false,
    submitting: false,
    confirmOpen: false,
    committed: null,
    shouldReload: false,
    isRealWrite: null,
    message: null,
    result: 'idle',
  }
}

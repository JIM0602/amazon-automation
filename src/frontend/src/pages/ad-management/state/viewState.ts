import type { AdsQueryState, TabKey } from '../types'

export type AdsViewLayer = 'workspace' | 'detail' | 'drawer' | 'modal'
export type AdsEntityType = TabKey | 'campaign_detail' | 'ad_group_detail' | 'log_detail'

export interface AdsViewState {
  layer: AdsViewLayer
  entityType: AdsEntityType
  entityId: string | null
  sourceTab: TabKey
  sourceQuery: AdsQueryState | null
}

export function createDefaultViewState(sourceTab: TabKey = 'portfolio'): AdsViewState {
  return {
    layer: 'workspace',
    entityType: sourceTab,
    entityId: null,
    sourceTab,
    sourceQuery: null,
  }
}

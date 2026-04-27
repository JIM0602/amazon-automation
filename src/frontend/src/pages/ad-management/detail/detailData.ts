export function getObjectPayload<T extends Record<string, unknown>>(
  payload: unknown,
  keys: string[] = ['data', 'item'],
): T | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return null
  }

  const candidate = payload as Record<string, unknown>
  for (const key of keys) {
    const value = candidate[key]
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as T
    }
  }

  return candidate as T
}

export function getListPayload<T extends Record<string, unknown>>(
  payload: unknown,
): { items: T[]; totalCount: number; summaryRow?: Partial<T> } {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return { items: [], totalCount: 0 }
  }

  const candidate = payload as Record<string, unknown>
  const rawItems = Array.isArray(candidate.items)
    ? candidate.items
    : Array.isArray(candidate.data)
      ? candidate.data
      : []

  return {
    items: rawItems.filter((item): item is T => !!item && typeof item === 'object' && !Array.isArray(item)) as T[],
    totalCount: typeof candidate.total_count === 'number' ? candidate.total_count : rawItems.length,
    summaryRow:
      candidate.summary_row && typeof candidate.summary_row === 'object' && !Array.isArray(candidate.summary_row)
        ? (candidate.summary_row as Partial<T>)
        : undefined,
  }
}

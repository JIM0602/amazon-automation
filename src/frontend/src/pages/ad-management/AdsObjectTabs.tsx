import type { TabKey } from './types'

interface TabItem {
  key: TabKey
  label: string
}

interface AdsObjectTabsProps {
  items: TabItem[]
  activeTab: TabKey
  onChange: (tab: TabKey) => void
}

export default function AdsObjectTabs({ items, activeTab, onChange }: AdsObjectTabsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          onClick={() => onChange(item.key)}
          className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === item.key
              ? 'bg-[var(--color-accent)] text-white shadow-sm'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

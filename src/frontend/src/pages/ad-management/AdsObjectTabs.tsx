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
    <div className="flex flex-wrap items-center gap-7 border-b border-gray-200 bg-white px-4 dark:border-gray-800 dark:bg-gray-900">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          onClick={() => onChange(item.key)}
          className={`relative inline-flex h-11 items-center text-sm font-medium transition-colors ${
            activeTab === item.key
              ? 'text-orange-500'
              : 'text-gray-900 hover:text-orange-500 dark:text-gray-200 dark:hover:text-orange-400'
          }`}
        >
          {item.label}
          {activeTab === item.key ? (
            <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-orange-500" />
          ) : null}
        </button>
      ))}
    </div>
  )
}

import { useLocation, useNavigate, useParams } from 'react-router-dom'

export default function NegativeTargetingDetailPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { id = '' } = useParams()

  return (
    <div className="mx-auto max-w-6xl p-6 text-gray-900 dark:text-gray-100">
      <button type="button" onClick={() => navigate(`/ads/manage${location.search}`)} className="mb-4 text-sm text-[var(--color-accent)] hover:underline">
        返回广告管理
      </button>
      <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
        <div className="mb-2 text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">L3 展示级</div>
        <h1 className="text-2xl font-semibold">否定投放详情</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">对象 ID：{id || '-'}</p>
      </div>
    </div>
  )
}

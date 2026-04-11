import { useState, useEffect, useCallback } from 'react'
import { AnimatePresence } from 'motion/react'
import { RefreshCw, CheckCircle, Clock, XCircle, FileWarning } from 'lucide-react'
import api from '../api/client'
import ApprovalCard from '../components/ApprovalCard'

type StatusFilter = 'pending' | 'approved' | 'rejected' | 'all'

const AGENT_TYPES = [
  { value: '', label: '所有 Agent' },
  { value: 'core_management', label: '主理人' },
  { value: 'brand_planning', label: '品牌策划' },
  { value: 'selection', label: '选品专家' },
  { value: 'competitor', label: '竞品分析' },
  { value: 'whitepaper', label: '白皮书' },
  { value: 'listing', label: 'Listing 优化' },
  { value: 'image_generation', label: '图片生成' },
  { value: 'product_listing', label: '上架专员' },
  { value: 'inventory', label: '库存管理' },
  { value: 'ad_monitor', label: '广告监控' },
  { value: 'persona', label: '用户画像' },
  { value: 'keyword_library', label: '词库管理' },
  { value: 'auditor', label: '风控合规' }
]

export default function Approvals() {
  const [approvals, setApprovals] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  const [agentTypeFilter, setAgentTypeFilter] = useState<string>('')
  const [refreshing, setRefreshing] = useState(false)

  const fetchApprovals = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true)
      else setRefreshing(true)
      
      const statusQuery = statusFilter === 'all' ? '' : statusFilter
      const res = await api.get(`/approvals?status=${statusQuery}&agent_type=${agentTypeFilter}`)
      
      setApprovals(res.data.approvals || [])
      setTotal(res.data.total || 0)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取审批列表失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [statusFilter, agentTypeFilter])

  // Initial fetch and dependency fetch
  useEffect(() => {
    fetchApprovals()
  }, [fetchApprovals])

  // Polling every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchApprovals(true)
    }, 30000)
    return () => clearInterval(interval)
  }, [fetchApprovals])

  const handleApprove = async (id: string, comment?: string) => {
    await api.post(`/approvals/${id}/approve`, { comment: comment || null })
    // Optimistic update or refetch
    fetchApprovals(true)
  }

  const handleReject = async (id: string, comment: string) => {
    await api.post(`/approvals/${id}/reject`, { comment })
    fetchApprovals(true)
  }

  return (
    <div className="flex-1 p-8 text-white min-h-full bg-[#0a0a1a]">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold tracking-tight">审批中心</h1>
              {statusFilter === 'pending' && total > 0 && (
                <span className="bg-amber-500/20 text-amber-400 text-xs font-bold px-2.5 py-1 rounded-full border border-amber-500/20">
                  {total} 待处理
                </span>
              )}
            </div>
            <p className="text-gray-400 text-lg">审核并管理所有 Agent 提交的操作请求</p>
          </div>
          
          <button
            onClick={() => fetchApprovals(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] rounded-xl text-sm font-medium hover:bg-[rgba(255,255,255,0.1)] transition-colors text-gray-300"
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-[var(--color-accent)]' : ''}`} />
            {refreshing ? '刷新中...' : '刷新'}
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8 p-4 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-2xl backdrop-blur-xl">
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'pending', label: '待审批', icon: Clock, color: 'text-amber-400' },
              { id: 'approved', label: '已通过', icon: CheckCircle, color: 'text-green-400' },
              { id: 'rejected', label: '已拒绝', icon: XCircle, color: 'text-red-400' },
              { id: 'all', label: '全部', icon: null, color: 'text-gray-300' }
            ].map(status => {
              const Icon = status.icon
              const isActive = statusFilter === status.id
              return (
                <button
                  key={status.id}
                  onClick={() => setStatusFilter(status.id as StatusFilter)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-[var(--color-accent)] text-white shadow-lg shadow-[var(--color-accent)]/20'
                      : 'bg-[rgba(255,255,255,0.03)] text-gray-400 hover:text-white hover:bg-[rgba(255,255,255,0.08)] border border-[rgba(255,255,255,0.05)]'
                  }`}
                >
                  {Icon && <Icon className={`w-4 h-4 ${isActive ? 'text-white' : status.color}`} />}
                  {status.label}
                </button>
              )
            })}
          </div>

          <div className="sm:ml-auto">
            <select
              value={agentTypeFilter}
              onChange={(e) => setAgentTypeFilter(e.target.value)}
              className="w-full sm:w-48 bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded-xl px-4 py-2 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)] focus:border-[var(--color-accent)] appearance-none cursor-pointer"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239CA3AF'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 0.75rem center',
                backgroundSize: '1rem'
              }}
            >
              {AGENT_TYPES.map(type => (
                <option key={type.value} value={type.value} className="bg-gray-900 text-white">
                  {type.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* List */}
        <div className="space-y-4 relative min-h-[400px]">
          {loading && !refreshing ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <RefreshCw className="w-8 h-8 text-[var(--color-accent)] animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-20 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-2xl backdrop-blur-sm">
              <FileWarning className="w-12 h-12 text-red-500/50 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-red-400 mb-2">加载失败</h3>
              <p className="text-red-500/70 text-sm mb-4">{error}</p>
              <button 
                onClick={() => fetchApprovals()}
                className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg text-sm border border-red-500/20 transition-colors"
              >
                重试
              </button>
            </div>
          ) : approvals.length === 0 ? (
            <div className="text-center py-24 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-2xl backdrop-blur-sm">
              <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-gray-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-300 mb-1">
                {statusFilter === 'pending' ? '太棒了，所有任务已审批完毕' : '没有找到相关审批记录'}
              </h3>
              <p className="text-gray-500 text-sm">
                {statusFilter === 'pending' ? '去喝杯咖啡休息一下吧' : '请尝试更换过滤条件'}
              </p>
            </div>
          ) : (
            <AnimatePresence mode="popLayout">
              {approvals.map(approval => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  onApprove={handleApprove}
                  onReject={handleReject}
                />
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>
    </div>
  )
}

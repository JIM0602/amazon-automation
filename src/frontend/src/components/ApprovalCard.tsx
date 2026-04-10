import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { CheckCircle, XCircle, Clock, ChevronDown, ChevronUp, AlertCircle, Loader2 } from 'lucide-react'

export interface ApprovalCardProps {
  approval: {
    id: string
    agent_run_id: string
    action_type: string
    payload: Record<string, unknown> | null
    status: string
    approved_by: string | null
    comment: string | null
    created_at: string
  }
  onApprove: (id: string, comment?: string) => Promise<void>
  onReject: (id: string, comment: string) => Promise<void>
}

export default function ApprovalCard({ approval, onApprove, onReject }: ApprovalCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [isRejecting, setIsRejecting] = useState(false)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isPending = approval.status === 'pending'
  const isApproved = approval.status === 'approved'
  const isRejected = approval.status === 'rejected'

  const handleApprove = async () => {
    try {
      setLoading(true)
      setError(null)
      await onApprove(approval.id, comment)
    } catch (err: any) {
      setError(err.response?.data?.detail || '审批通过失败')
    } finally {
      setLoading(false)
    }
  }

  const handleReject = async () => {
    if (!comment.trim()) {
      setError('拒绝必须填写理由')
      return
    }
    try {
      setLoading(true)
      setError(null)
      await onReject(approval.id, comment)
      setIsRejecting(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || '拒绝审批失败')
    } finally {
      setLoading(false)
    }
  }

  const formatPayload = (payload: Record<string, unknown> | null) => {
    if (!payload) return '无详细信息'
    return JSON.stringify(payload, null, 2)
  }

  const getSummary = (payload: Record<string, unknown> | null) => {
    if (!payload) return '暂无详细内容'
    // Try to get a meaningful summary
    if (payload.summary && typeof payload.summary === 'string') return payload.summary
    if (payload.content && typeof payload.content === 'string') return payload.content.substring(0, 100) + '...'
    if (payload.title && typeof payload.title === 'string') return payload.title
    const keys = Object.keys(payload)
    if (keys.length > 0) return `包含字段: ${keys.join(', ')}`
    return '详情请展开查看'
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={`bg-[rgba(255,255,255,0.03)] backdrop-blur-xl border border-[rgba(255,255,255,0.08)] rounded-2xl overflow-hidden hover:bg-[rgba(255,255,255,0.06)] transition-all duration-300 ${
        expanded ? 'shadow-2xl shadow-black/40' : 'shadow-xl shadow-black/20'
      }`}
    >
      <div 
        className="p-5 cursor-pointer flex items-start gap-4"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={`mt-1 flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center border ${
          isPending ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
          isApproved ? 'bg-green-500/10 border-green-500/20 text-green-400' :
          'bg-red-500/10 border-red-500/20 text-red-400'
        }`}>
          {isPending && <Clock className="w-5 h-5" />}
          {isApproved && <CheckCircle className="w-5 h-5" />}
          {isRejected && <XCircle className="w-5 h-5" />}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-lg font-semibold text-white truncate">
              {approval.action_type === 'generate_report' ? '报告生成' : approval.action_type}
            </h3>
            <span className="text-xs text-gray-500 ml-4 whitespace-nowrap">
              {formatDate(approval.created_at)}
            </span>
          </div>
          
          <p className="text-sm text-gray-400 line-clamp-1">
            {getSummary(approval.payload)}
          </p>

          {!isPending && approval.comment && (
            <div className={`mt-2 text-xs px-3 py-2 rounded-lg inline-block border ${
              isApproved ? 'bg-green-500/5 border-green-500/10 text-green-300' : 'bg-red-500/5 border-red-500/10 text-red-300'
            }`}>
              <span className="font-semibold">{isApproved ? '通过留言' : '拒绝原因'}: </span>
              {approval.comment}
            </div>
          )}
        </div>

        <div className="flex-shrink-0 flex items-center text-gray-500 hover:text-white transition-colors">
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-2 border-t border-[rgba(255,255,255,0.05)]">
              <div className="bg-black/40 rounded-xl p-4 mb-5 overflow-x-auto border border-white/5">
                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                  {formatPayload(approval.payload)}
                </pre>
              </div>

              {isPending && (
                <div className="space-y-4">
                  {isRejecting ? (
                    <motion.div 
                      initial={{ opacity: 0, y: -10 }} 
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-black/20 p-4 rounded-xl border border-red-500/20"
                    >
                      <label className="block text-sm font-medium text-red-400 mb-2">
                        拒绝原因 (必填)
                      </label>
                      <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="请输入拒绝原因..."
                        className="w-full bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded-xl p-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-red-500 focus:border-red-500 min-h-[80px] resize-none mb-3"
                      />
                      <div className="flex justify-end gap-3">
                        <button
                          onClick={() => setIsRejecting(false)}
                          disabled={loading}
                          className="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
                        >
                          取消
                        </button>
                        <button
                          onClick={handleReject}
                          disabled={loading || !comment.trim()}
                          className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 hover:bg-red-700 text-white transition-colors flex items-center shadow-lg shadow-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <XCircle className="w-4 h-4 mr-2" />}
                          确认拒绝
                        </button>
                      </div>
                    </motion.div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="附加审批意见 (选填)..."
                        className="w-full bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.05)] rounded-xl p-3 text-sm text-gray-300 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)] focus:border-[var(--color-accent)] min-h-[60px] resize-none"
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={handleApprove}
                          disabled={loading}
                          className="flex-1 py-2.5 rounded-xl text-sm font-medium bg-green-600 hover:bg-green-700 text-white transition-colors flex items-center justify-center shadow-lg shadow-green-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                          同意执行
                        </button>
                        <button
                          onClick={() => setIsRejecting(true)}
                          disabled={loading}
                          className="flex-1 py-2.5 rounded-xl text-sm font-medium bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-colors flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          拒绝执行
                        </button>
                      </div>
                    </div>
                  )}

                  {error && (
                    <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                      <AlertCircle className="w-4 h-4" />
                      {error}
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

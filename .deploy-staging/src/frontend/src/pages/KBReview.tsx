import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Check, X, Edit2, Save, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../api/client'
import { KBReviewItem } from '../types'

export default function KBReview() {
  const [items, setItems] = useState<KBReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [editSummary, setEditSummary] = useState('')
  
  const [rejectingId, setRejectingId] = useState<string | null>(null)
  const [rejectComment, setRejectComment] = useState('')
  const [approvingId, setApprovingId] = useState<string | null>(null)
  const [approveComment, setApproveComment] = useState('')

  const fetchItems = async () => {
    try {
      setLoading(true)
      const res = await api.get('/kb-review?status=pending')
      setItems(res.data.items || [])
      setError(null)
    } catch (err: any) {
      console.error('Failed to fetch KB review items', err)
      setError('无法加载知识库待审核列表')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchItems()
  }, [])

  const handleApprove = async (id: string) => {
    try {
      await api.post(`/kb-review/${id}/approve`, { comment: approveComment || null })
      setItems(items.filter(item => item.id !== id))
      setApprovingId(null)
      setApproveComment('')
    } catch (err: any) {
      console.error('Failed to approve', err)
      alert(err.response?.data?.detail || '审核通过失败')
    }
  }

  const handleReject = async (id: string) => {
    if (!rejectComment.trim()) {
      alert('请填写拒绝原因')
      return
    }
    try {
      await api.post(`/kb-review/${id}/reject`, { comment: rejectComment })
      setItems(items.filter(item => item.id !== id))
      setRejectingId(null)
      setRejectComment('')
    } catch (err: any) {
      console.error('Failed to reject', err)
      alert(err.response?.data?.detail || '拒绝失败')
    }
  }

  const handleSaveEdit = async (id: string) => {
    try {
      const res = await api.put(`/kb-review/${id}`, {
        content: editContent,
        summary: editSummary || null
      })
      setItems(items.map(item => item.id === id ? res.data : item))
      setEditingId(null)
    } catch (err: any) {
      console.error('Failed to edit', err)
      alert(err.response?.data?.detail || '保存修改失败')
    }
  }

  const toggleExpand = (item: KBReviewItem) => {
    if (expandedId === item.id) {
      setExpandedId(null)
      setEditingId(null)
      setRejectingId(null)
      setApprovingId(null)
    } else {
      setExpandedId(item.id)
      setEditingId(null)
      setRejectingId(null)
      setApprovingId(null)
    }
  }

  const startEdit = (item: KBReviewItem) => {
    setEditContent(item.content)
    setEditSummary(item.summary || '')
    setEditingId(item.id)
    setRejectingId(null)
    setApprovingId(null)
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-[#0a0a1a] text-white">
        <div className="text-gray-400">加载中...</div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-[#0a0a1a] p-6 text-white">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">知识库审核</h1>
          <p className="mt-1 text-sm text-gray-400">
            仅老板可见：审核各 AI Agent 尝试写入企业知识库的内容
          </p>
        </div>
        <div className="rounded-full bg-[rgba(255,255,255,0.08)] px-4 py-1 text-sm text-gray-300">
          待审核: <span className="font-bold text-white">{items.length}</span>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg bg-red-900/50 p-4 text-red-200 border border-red-500/50">
          {error}
        </div>
      )}

      {items.length === 0 && !error ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] py-16">
          <Check className="mb-4 h-12 w-12 text-gray-500 opacity-50" />
          <h3 className="text-lg font-medium text-gray-300">太棒了，目前没有待审核的内容</h3>
          <p className="mt-2 text-sm text-gray-500">所有知识库内容已处理完毕</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const isExpanded = expandedId === item.id
            const isEditing = editingId === item.id
            const isRejecting = rejectingId === item.id
            const isApproving = approvingId === item.id

            return (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="overflow-hidden rounded-xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] transition-colors hover:bg-[rgba(255,255,255,0.04)]"
              >
                {/* Header */}
                <div
                  className="flex cursor-pointer items-start justify-between p-4"
                  onClick={() => toggleExpand(item)}
                >
                  <div className="flex-1 pr-4">
                    <div className="flex items-center gap-3">
                      <span className="rounded-md bg-[#3B82F6]/20 px-2 py-1 text-xs font-medium text-[#3B82F6]">
                        {item.agent_type || 'Unknown Agent'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                      {item.source && (
                        <span className="text-xs text-gray-400 bg-white/5 px-2 py-0.5 rounded">
                          来源: {item.source}
                        </span>
                      )}
                    </div>
                    <h3 className="mt-2 font-medium text-gray-200">
                      {item.summary || '无摘要'}
                    </h3>
                    {!isExpanded && (
                      <p className="mt-1 line-clamp-1 text-sm text-gray-500">
                        {item.content}
                      </p>
                    )}
                  </div>
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/5 text-gray-400">
                    {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                  </div>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="border-t border-[rgba(255,255,255,0.08)] p-4 bg-black/20">
                    {isEditing ? (
                      <div className="space-y-4">
                        <div>
                          <label className="mb-1 block text-sm text-gray-400">摘要</label>
                          <input
                            type="text"
                            value={editSummary}
                            onChange={(e) => setEditSummary(e.target.value)}
                            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-[#0a0a1a] p-2 text-sm text-white focus:border-[#3B82F6] focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-sm text-gray-400">内容</label>
                          <textarea
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            rows={6}
                            className="w-full resize-y rounded-lg border border-[rgba(255,255,255,0.1)] bg-[#0a0a1a] p-3 text-sm text-white focus:border-[#3B82F6] focus:outline-none"
                          />
                        </div>
                        <div className="flex justify-end gap-2 pt-2">
                          <button
                            onClick={() => setEditingId(null)}
                            className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:text-white"
                          >
                            取消
                          </button>
                          <button
                            onClick={() => handleSaveEdit(item.id)}
                            className="flex items-center gap-2 rounded-lg bg-[#3B82F6] px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
                          >
                            <Save size={16} /> 保存修改
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="mb-6 whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
                          {item.content}
                        </div>

                        {/* Action Area */}
                        {isRejecting ? (
                          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
                            <h4 className="mb-2 text-sm font-medium text-red-200">填写拒绝原因</h4>
                            <textarea
                              value={rejectComment}
                              onChange={(e) => setRejectComment(e.target.value)}
                              placeholder="内容不准确、来源不可靠..."
                              rows={2}
                              className="mb-3 w-full rounded-lg border border-red-500/20 bg-black/50 p-2 text-sm text-white focus:border-red-500 focus:outline-none"
                            />
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => setRejectingId(null)}
                                className="rounded-lg px-3 py-1.5 text-sm text-gray-400 hover:text-white"
                              >
                                取消
                              </button>
                              <button
                                onClick={() => handleReject(item.id)}
                                className="rounded-lg bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                              >
                                确认拒绝
                              </button>
                            </div>
                          </div>
                        ) : isApproving ? (
                          <div className="rounded-lg border border-green-500/20 bg-green-500/10 p-4">
                            <h4 className="mb-2 text-sm font-medium text-green-200">
                              添加审核备注 (可选)
                            </h4>
                            <textarea
                              value={approveComment}
                              onChange={(e) => setApproveComment(e.target.value)}
                              placeholder="同意写入知识库..."
                              rows={2}
                              className="mb-3 w-full rounded-lg border border-green-500/20 bg-black/50 p-2 text-sm text-white focus:border-green-500 focus:outline-none"
                            />
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => setApprovingId(null)}
                                className="rounded-lg px-3 py-1.5 text-sm text-gray-400 hover:text-white"
                              >
                                取消
                              </button>
                              <button
                                onClick={() => handleApprove(item.id)}
                                className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700"
                              >
                                确认通过并入库
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-wrap items-center gap-3 pt-2">
                            <button
                              onClick={() => setApprovingId(item.id)}
                              className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700"
                            >
                              <Check size={16} /> 通过入库
                            </button>
                            <button
                              onClick={() => startEdit(item)}
                              className="flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.1)] bg-transparent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/5"
                            >
                              <Edit2 size={16} /> 编辑内容
                            </button>
                            <button
                              onClick={() => setRejectingId(item.id)}
                              className="ml-auto flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
                            >
                              <X size={16} /> 拒绝
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}

import { useEffect, useMemo, useState, useRef, type CSSProperties } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Lock, AlertCircle, PanelRight, ChevronLeft } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { AGENTS } from '../data/agents'
import { ChatWindow } from '../components/ChatWindow'
import { ConversationList } from '../components/ConversationList'
import FilePreviewModal from '../components/FilePreviewModal'
import FileSidebar, { type FileItem } from '../components/FileSidebar'
import type { AgentType } from '../types'
import api from '../api/client'

const MOCK_FILES: FileItem[] = [
  { id: '1', name: '品牌路径规划报告_2024Q1.pdf', type: 'pdf', size: '2.4 MB', createdAt: '2024-01-15', url: '#' },
  { id: '2', name: '竞品分析数据表.xlsx', type: 'excel', size: '1.1 MB', createdAt: '2024-01-14', url: '#' },
  { id: '3', name: '产品主图_白底版.png', type: 'image', size: '856 KB', createdAt: '2024-01-13', url: '#' },
]

function NotFoundState() {
  return (
    <div className="flex h-full items-center justify-center bg-gray-50 text-gray-900 dark:bg-[#0a0a1a] dark:text-white">
      <div className="max-w-md rounded-2xl border border-gray-200 bg-white dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(255,255,255,0.05)] p-8 text-center shadow-2xl shadow-black/30">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gray-100 dark:bg-[rgba(255,255,255,0.08)] text-[var(--color-accent)]">
          <AlertCircle size={28} />
        </div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Agent not found</h1>
        <p className="mt-3 text-sm leading-6 text-gray-500 dark:text-gray-400">当前路径对应的 Agent 类型无效，请返回 Agent 矩阵选择一个可用的 Agent。</p>
      </div>
    </div>
  )
}

function AccessDeniedState() {
  return (
    <div className="flex h-full items-center justify-center bg-gray-50 text-gray-900 dark:bg-[#0a0a1a] dark:text-white">
      <div className="max-w-md rounded-2xl border border-gray-200 bg-white dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(255,255,255,0.05)] p-8 text-center shadow-2xl shadow-black/30">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gray-100 dark:bg-[rgba(255,255,255,0.08)] text-[var(--color-accent)]">
          <Lock size={28} />
        </div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Access denied</h1>
        <p className="mt-3 text-sm leading-6 text-gray-500 dark:text-gray-400">该 Agent 仅限 boss 角色访问，当前账号没有权限进入此会话页。</p>
      </div>
    </div>
  )
}

export default function AgentChat() {
  const { type } = useParams<{ type: string }>()
  const navigate = useNavigate()
  const { role } = useAuth()
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [previewFile, setPreviewFile] = useState<FileItem | null>(null)
  const prevTypeRef = useRef<string | undefined>(undefined)
  const initializedRef = useRef(false)

  const agentInfo = useMemo(() => AGENTS.find((agent) => agent.type === type), [type])

  // Reset state when agent type changes
  useEffect(() => {
    if (prevTypeRef.current !== type) {
      setSelectedConversationId(null)
      setSidebarOpen(false)
      initializedRef.current = false
      prevTypeRef.current = type
    }
  }, [type])

  if (!agentInfo) {
    return <NotFoundState />
  }

  if (agentInfo.bossOnly && role !== 'boss') {
    return <AccessDeniedState />
  }

  const Icon = agentInfo.icon

  useEffect(() => {
    if (initializedRef.current) return
    
    let cancelled = false

    const loadLatestConversation = async () => {
      try {
        const res = await api.get(`/chat/${type}/conversations`)
        const conversations = Array.isArray(res.data)
          ? res.data
          : Array.isArray(res.data?.conversations)
            ? res.data.conversations
            : []

        if (!cancelled && conversations.length > 0) {
          setSelectedConversationId(conversations[0].id)
        }
        initializedRef.current = true
      } catch (err) {
        initializedRef.current = true
      }
    }

    loadLatestConversation()

    return () => {
      cancelled = true
    }
  }, [type])

  const themeVars = {
    '--color-primary': '#1E3A5F',
    '--color-accent': '#3B82F6',
    '--color-surface': 'rgba(255,255,255,0.08)',
    '--color-surface-hover': 'rgba(255,255,255,0.12)',
    '--color-glass': 'rgba(255,255,255,0.05)',
    '--color-glass-border': 'rgba(255,255,255,0.1)',
  } as CSSProperties

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-gray-50 text-gray-900 dark:bg-[#0a0a1a] dark:text-white" style={themeVars}>
      {/* 左侧会话列表 */}
      <div className="w-[280px] flex-shrink-0 flex flex-col border-r border-[var(--color-glass-border)] bg-[var(--color-glass)] backdrop-blur-xl overflow-hidden">
        <div className="border-b border-[var(--color-glass-border)] p-4 flex-shrink-0 space-y-4">
          <button
            onClick={() => navigate('/agents')}
            className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
          >
            <ChevronLeft size={16} />
            返回更多功能
          </button>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-100 dark:bg-[rgba(255,255,255,0.08)] text-[var(--color-accent)]">
              <Icon size={20} />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900 dark:text-white">历史对话</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">查看和切换当前 Agent 的历史会话</div>
            </div>
          </div>
        </div>
        <ConversationList
          agentType={type as AgentType}
          currentConversationId={selectedConversationId}
          onSelectConversation={setSelectedConversationId}
          onNewConversation={() => setSelectedConversationId(null)}
        />
      </div>

      {/* 中间聊天区域 */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* 类型B Agent 显示侧边栏切换按钮 */}
        {agentInfo.hasFileSidebar && (
          <div className="flex justify-end px-4 py-2 border-b border-[var(--color-glass-border)] bg-[var(--color-glass)] flex-shrink-0">
            <button
              onClick={() => setSidebarOpen(prev => !prev)}
              className={`p-2 rounded-lg transition-colors ${sidebarOpen ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-200 dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/10'}`}
              title="切换文件侧边栏"
            >
              <PanelRight size={18} />
            </button>
          </div>
        )}

        <ChatWindow
          agentType={type as AgentType}
          agentName={agentInfo.name}
          agentDescription={agentInfo.description}
          agentIcon={<Icon size={20} />}
          conversationId={selectedConversationId}
          onConversationChange={setSelectedConversationId}
        />

      </div>

      {/* 右侧文件侧边栏（仅类型B Agent） */}
      {agentInfo.hasFileSidebar && (
        <FileSidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(prev => !prev)}
          files={MOCK_FILES}
          onFilePreview={setPreviewFile}
        />
      )}

      {/* 文件预览模态框 */}
      <FilePreviewModal
        isOpen={previewFile !== null}
        onClose={() => setPreviewFile(null)}
        fileName={previewFile?.name ?? ''}
        fileType={previewFile?.type ?? ''}
        fileUrl={previewFile?.url ?? ''}
      />
    </div>
  )
}

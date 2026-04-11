import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Lock, AlertCircle, ChevronLeft } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { AGENTS } from '../data/agents'
import { ChatWindow } from '../components/ChatWindow'
import { ConversationList } from '../components/ConversationList'
import type { AgentType } from '../types'
import api from '../api/client'

function NotFoundState() {
  return (
    <div className="flex h-full items-center justify-center bg-[#0a0a1a] text-white">
      <div className="max-w-md rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.05)] p-8 text-center shadow-2xl shadow-black/30">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[rgba(255,255,255,0.08)] text-[var(--color-accent)]">
          <AlertCircle size={28} />
        </div>
        <h1 className="text-2xl font-semibold text-white">Agent not found</h1>
        <p className="mt-3 text-sm leading-6 text-gray-400">当前路径对应的 Agent 类型无效，请返回 Agent 矩阵选择一个可用的 Agent。</p>
      </div>
    </div>
  )
}

function AccessDeniedState() {
  return (
    <div className="flex h-full items-center justify-center bg-[#0a0a1a] text-white">
      <div className="max-w-md rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.05)] p-8 text-center shadow-2xl shadow-black/30">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[rgba(255,255,255,0.08)] text-[var(--color-accent)]">
          <Lock size={28} />
        </div>
        <h1 className="text-2xl font-semibold text-white">Access denied</h1>
        <p className="mt-3 text-sm leading-6 text-gray-400">该 Agent 仅限 boss 角色访问，当前账号没有权限进入此会话页。</p>
      </div>
    </div>
  )
}

export default function AgentChat() {
  const { type } = useParams<{ type: string }>()
  const { role } = useAuth()
  const navigate = useNavigate()
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)

  const agentInfo = useMemo(() => AGENTS.find((agent) => agent.type === type), [type])

  if (!agentInfo) {
    return <NotFoundState />
  }

  if (agentInfo.bossOnly && role !== 'boss') {
    return <AccessDeniedState />
  }

  const Icon = agentInfo.icon

  useEffect(() => {
    let cancelled = false

    const loadLatestConversation = async () => {
      try {
        const res = await api.get(`/chat/${type}/conversations`)
        const conversations = Array.isArray(res.data)
          ? res.data
          : Array.isArray(res.data?.conversations)
            ? res.data.conversations
            : []

        if (!cancelled && selectedConversationId === null && conversations.length > 0) {
          setSelectedConversationId(conversations[0].id)
        }
      } catch (err) {
        console.error('Failed to preload conversations', err)
      }
    }

    loadLatestConversation()

    return () => {
      cancelled = true
    }
  }, [selectedConversationId, type])

  const themeVars = {
    '--color-primary': '#1E3A5F',
    '--color-accent': '#3B82F6',
    '--color-surface': 'rgba(255,255,255,0.08)',
    '--color-glass': 'rgba(255,255,255,0.05)',
    '--color-glass-border': 'rgba(255,255,255,0.1)',
  } as CSSProperties

  return (
    <div className="flex h-full min-h-[calc(100vh-4rem)] bg-[#0a0a1a] text-white" style={themeVars}>
      <div className="w-[280px] flex-shrink-0 border-r border-[var(--color-glass-border)] bg-[var(--color-glass)] backdrop-blur-xl">
        <div className="border-b border-[var(--color-glass-border)] p-4">
          <button
            onClick={() => navigate('/agents')}
            className="mb-3 flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
          >
            <ChevronLeft size={14} />
            <span>返回</span>
          </button>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[rgba(255,255,255,0.08)] text-[var(--color-accent)]">
              <Icon size={20} />
            </div>
            <div>
              <div className="text-sm font-semibold text-white">{agentInfo.name}</div>
              <div className="text-xs text-gray-400">{agentInfo.description}</div>
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

      <div className="flex-1 p-4">
        <ChatWindow
          agentType={type as AgentType}
          agentName={agentInfo.name}
          agentIcon={<Icon size={20} />}
          conversationId={selectedConversationId}
          onConversationChange={setSelectedConversationId}
        />
      </div>
    </div>
  )
}

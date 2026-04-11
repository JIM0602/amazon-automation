import { useState, useEffect, useCallback } from 'react';
import type { AgentType, Conversation } from '../types';
import api from '../api/client';
import { PlusCircle, MessageSquare } from 'lucide-react';

export interface ConversationListProps {
  agentType: AgentType;
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
}

export function ConversationList({
  agentType,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}: ConversationListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/chat/${agentType}/conversations`);
      if (Array.isArray(res.data)) {
        setConversations(res.data);
      } else if (Array.isArray(res.data?.conversations)) {
        setConversations(res.data.conversations);
      }
    } catch (err) {
      console.error('Failed to fetch conversations', err);
    } finally {
      setLoading(false);
    }
  }, [agentType]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  return (
    <div className="flex flex-col h-full w-full glass bg-[#0a0a1a]">
      <div className="p-4 border-b border-[rgba(255,255,255,0.1)]">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-[var(--color-accent)] hover:opacity-90 transition-opacity text-white font-medium"
        >
          <PlusCircle size={18} />
          新建对话
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {loading ? (
          <div className="text-gray-500 text-sm p-4 text-center">加载中...</div>
        ) : conversations.length === 0 ? (
          <div className="text-gray-500 text-sm p-4 text-center">暂无对话记录</div>
        ) : (
          conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors duration-200 ${
                currentConversationId === conv.id
                  ? 'bg-[rgba(255,255,255,0.1)] text-white'
                  : 'text-gray-400 hover:bg-[rgba(255,255,255,0.05)] hover:text-white'
              }`}
            >
              <MessageSquare size={16} className="flex-shrink-0" />
              <div className="flex-1 overflow-hidden">
                <div className="truncate text-sm font-medium">
                  {conv.title || '新对话'}
                </div>
                <div className="text-xs opacity-60 mt-0.5 truncate">
                  {new Date(conv.created_at).toLocaleString()}
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

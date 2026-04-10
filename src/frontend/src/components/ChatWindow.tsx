import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import { Send, User, Loader2 } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import type { AgentType } from '../types';

export interface ChatWindowProps {
  agentType: AgentType;
  agentName: string;
  agentIcon: React.ReactNode;
  conversationId?: string | null;
  onConversationChange?: (id: string | null) => void;
}

export function ChatWindow({
  agentType,
  agentName,
  agentIcon,
  conversationId: externalConvId = null,
  onConversationChange,
}: ChatWindowProps) {
  const {
    messages,
    sendMessage,
    isTyping,
    conversationId,
    setConversationId,
    loadHistory,
    error
  } = useChat(agentType);

  const [input, setInput] = useState('');
  const [isInitializing, setIsInitializing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync external conversationId with internal state
  useEffect(() => {
    if (externalConvId && externalConvId !== conversationId) {
      const init = async () => {
        setIsInitializing(true);
        await loadHistory(externalConvId);
        setIsInitializing(false);
      };
      init();
    } else if (externalConvId === null && conversationId !== null) {
      setConversationId(null);
    }
  }, [externalConvId, conversationId, loadHistory, setConversationId]);

  // Notify parent of conversation id change
  useEffect(() => {
    if (conversationId && conversationId !== externalConvId && onConversationChange) {
      onConversationChange(conversationId);
    }
  }, [conversationId, externalConvId, onConversationChange]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const text = input.trim();
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-[#0a0a1a] rounded-xl overflow-hidden glass border border-[rgba(255,255,255,0.1)]">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.02)]">
        <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.05)] text-[var(--color-accent)]">
          {agentIcon}
        </div>
        <div>
          <h2 className="text-white font-semibold flex items-center gap-2">
            {agentName}
            <span className="flex h-2 w-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span>
          </h2>
          <p className="text-xs text-gray-400">Online</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {isInitializing ? (
          <div className="flex items-center justify-center h-full text-gray-500 gap-2">
            <Loader2 className="animate-spin" size={20} />
            正在加载对话记录...
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="p-4 rounded-full bg-[rgba(255,255,255,0.05)] text-gray-400">
              {agentIcon}
            </div>
            <p className="text-gray-400 font-medium">开始与 {agentName} 对话</p>
            <p className="text-xs text-gray-500 max-w-sm">
              请在下方输入框中描述您的需求，AI 将为您提供专业解答与协助。
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <motion.div
                  key={msg.id || index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`flex gap-3 w-full ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <div className="flex-shrink-0 mt-1 p-2 h-8 w-8 rounded-full bg-[rgba(255,255,255,0.1)] flex items-center justify-center text-[var(--color-accent)]">
                      {agentIcon}
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-lg ${
                      isUser
                        ? 'bg-[var(--color-accent)] text-white rounded-tr-sm'
                        : 'bg-[rgba(255,255,255,0.05)] backdrop-blur-md border border-[rgba(255,255,255,0.05)] text-gray-200 rounded-tl-sm'
                    }`}
                  >
                    {isUser ? (
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {msg.content}
                      </div>
                    ) : (
                      <div className="prose prose-invert prose-sm max-w-none text-sm leading-relaxed
                                      prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1">
                        <ReactMarkdown>{msg.content || '...'}</ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {isUser && (
                    <div className="flex-shrink-0 mt-1 h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white">
                      <User size={16} />
                    </div>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}

        {isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-3 justify-start"
          >
             <div className="flex-shrink-0 mt-1 p-2 h-8 w-8 rounded-full bg-[rgba(255,255,255,0.1)] flex items-center justify-center text-[var(--color-accent)]">
              {agentIcon}
            </div>
            <div className="bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.05)] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </div>
          </motion.div>
        )}
        
        {error && (
          <div className="text-red-400 text-sm p-3 bg-red-900/20 rounded-lg border border-red-900/50">
            发生错误: {error}
          </div>
        )}

        <div ref={messagesEndRef} className="h-4" />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-[rgba(255,255,255,0.1)] bg-[rgba(0,0,0,0.2)]">
        <div className="relative flex items-end gap-2 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] rounded-xl p-1 focus-within:border-[var(--color-accent)] focus-within:ring-1 focus-within:ring-[var(--color-accent)] transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="输入消息 (Enter 发送, Shift+Enter 换行)..."
            className="w-full max-h-[120px] min-h-[44px] bg-transparent text-white text-sm px-3 py-3 resize-none outline-none overflow-y-auto"
            rows={1}
            disabled={isTyping}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className={`flex-shrink-0 h-10 w-10 mb-0.5 mr-0.5 rounded-lg flex items-center justify-center transition-all ${
              !input.trim() || isTyping
                ? 'bg-[rgba(255,255,255,0.05)] text-gray-500 cursor-not-allowed'
                : 'bg-[var(--color-accent)] text-white hover:bg-opacity-90 shadow-md'
            }`}
          >
            <Send size={18} className={isTyping ? "opacity-50" : ""} />
          </button>
        </div>
      </div>
    </div>
  );
}

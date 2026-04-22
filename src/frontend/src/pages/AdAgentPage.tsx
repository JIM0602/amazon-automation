import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, FlaskConical, ChevronLeft, ArrowRight, Info, AlertTriangle, Send } from 'lucide-react';
import { AGENTS } from '../data/agents';
import { ChatWindow } from '../components/ChatWindow';
import { ConversationList } from '../components/ConversationList';
import type { AgentType } from '../types';
import api from '../api/client';
import { motion, AnimatePresence } from 'motion/react';

export default function AdAgentPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'chat' | 'sandbox'>('chat');
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);

  const agentType = 'ad_monitor' as AgentType;
  const agentInfo = useMemo(() => AGENTS.find((agent) => agent.type === agentType), [agentType]);
  const Icon = agentInfo?.icon || Bot;

  // Load latest conversation for the chat tab
  useEffect(() => {
    let cancelled = false;
    const loadLatestConversation = async () => {
      try {
        const res = await api.get(`/chat/${agentType}/conversations`);
        const conversations = Array.isArray(res.data)
          ? res.data
          : Array.isArray(res.data?.conversations)
            ? res.data.conversations
            : [];
        if (!cancelled && selectedConversationId === null && conversations.length > 0) {
          setSelectedConversationId(conversations[0].id);
        }
      } catch (err) {
        console.error('Failed to preload conversations', err);
      }
    };
    loadLatestConversation();
    return () => {
      cancelled = true;
    };
  }, [selectedConversationId, agentType]);

  const themeVars = {
    '--color-primary': '#1E3A5F',
    '--color-accent': '#3B82F6',
    '--color-surface': 'rgba(255,255,255,0.08)',
    '--color-glass': 'rgba(255,255,255,0.05)',
    '--color-glass-border': 'rgba(255,255,255,0.1)',
  } as CSSProperties;

  return (
    <div className="flex h-full min-h-[calc(100vh-4rem)] flex-col bg-[var(--color-bg)] text-gray-900 dark:bg-[#0a0a1a] dark:text-white" style={themeVars}>
      {/* Header & Tabs */}
      <div className="flex-shrink-0 border-b border-[var(--color-glass-border)] bg-[var(--color-glass)] px-6 py-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/ads/manage')}
            className="flex items-center justify-center rounded-lg p-2 text-gray-500 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-[rgba(255,255,255,0.1)] dark:hover:text-white"
            title="返回广告管理"
          >
            <ChevronLeft size={20} />
          </button>
          <div className="h-8 w-[1px] bg-[var(--color-glass-border)]" />
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-wide text-gray-900 dark:text-white">
            <Icon className="text-[var(--color-accent)]" size={24} />
            {agentInfo?.name || '广告优化Agent'}
          </h1>

          <div className="ml-auto flex items-center gap-1 rounded-xl border border-gray-200 bg-white/80 p-1 shadow-sm dark:border-[rgba(255,255,255,0.05)] dark:bg-[#0f0f23]">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                activeTab === 'chat'
                  ? 'bg-[var(--color-accent)] text-white shadow-md'
                  : 'text-gray-500 hover:bg-black/5 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-[rgba(255,255,255,0.05)] dark:hover:text-white'
              }`}
            >
              <Bot size={16} />
              智能会话
            </button>
            <button
              onClick={() => setActiveTab('sandbox')}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                activeTab === 'sandbox'
                  ? 'bg-amber-500 text-white shadow-md shadow-amber-500/20'
                  : 'text-gray-500 hover:bg-black/5 hover:text-amber-500 dark:text-gray-400 dark:hover:bg-[rgba(255,255,255,0.05)] dark:hover:text-amber-400'
              }`}
            >
              <FlaskConical size={16} />
              沙箱模拟
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          {activeTab === 'chat' ? (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 flex"
            >
              {/* Conversation List Sidebar */}
              <div className="w-[280px] flex-shrink-0 border-r border-[var(--color-glass-border)] bg-white/70 dark:bg-[rgba(0,0,0,0.2)] backdrop-blur-md">
                <ConversationList
                  agentType={agentType}
                  currentConversationId={selectedConversationId}
                  onSelectConversation={setSelectedConversationId}
                  onNewConversation={() => setSelectedConversationId(null)}
                />
              </div>
              {/* Chat Window */}
              <div className="flex-1 p-6">
                <ChatWindow
                  agentType={agentType}
                  agentName={agentInfo?.name || '广告监控Agent'}
                  agentDescription={agentInfo?.description}
                  agentIcon={<Icon size={20} />}
                  conversationId={selectedConversationId}
                  onConversationChange={setSelectedConversationId}
                />
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="sandbox"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 overflow-y-auto p-6"
            >
              <SandboxView />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function SandboxView() {
  const [input, setInput] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleSimulate = () => {
    if (!input.trim()) return;
    setIsSimulating(true);
    setResult(null);
    
    // Simulate API call delay
    setTimeout(() => {
      setIsSimulating(false);
      setResult('预计影响：点击量 +5%~15%，花费 +100%（$50→$100），ACoS可能变化±3%\n建议：在销售旺季前增加预算是合理的，但需监控ACoS变化');
    }, 1200);
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      {/* Warning Banner */}
      <div className="flex items-start gap-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 text-amber-900 shadow-[0_0_20px_rgba(245,158,11,0.05)] dark:text-amber-200">
        <AlertTriangle className="mt-0.5 flex-shrink-0 text-amber-400" size={24} />
        <div>
          <h3 className="text-lg font-semibold text-amber-400">🧪 模拟模式 — 不会执行真实操作</h3>
          <p className="mt-1 text-sm leading-relaxed text-amber-800/90 dark:text-amber-200/80">
            在此区域内执行的任何广告操作（如调整预算、修改出价、暂停广告等）均仅作为沙箱环境下的模拟。系统将根据历史数据与机器学习模型预估操作后的影响，不会影响 Amazon Ads 真实数据。
          </p>
        </div>
      </div>

      {/* Input Area */}
      <div className="rounded-2xl border border-gray-200 bg-white/75 p-6 shadow-xl backdrop-blur-sm dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(255,255,255,0.02)]">
        <label className="mb-3 block text-sm font-medium text-gray-700 dark:text-gray-300">
          描述您要模拟的广告操作
        </label>
        <div className="relative flex flex-col gap-4">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="例如：将 Campaign A 的每日预算从 $50 提高到 $100..."
            className="h-32 w-full resize-none rounded-xl border border-gray-200 bg-white p-4 text-gray-900 placeholder-gray-400 transition-all focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(0,0,0,0.3)] dark:text-white dark:placeholder-gray-500"
          />
          <div className="flex justify-end">
            <button
              onClick={handleSimulate}
              disabled={!input.trim() || isSimulating}
              className={`flex items-center gap-2 rounded-lg px-6 py-2.5 font-medium transition-all ${
                !input.trim() || isSimulating
                  ? 'cursor-not-allowed bg-gray-100 text-gray-400 dark:bg-[rgba(255,255,255,0.05)] dark:text-gray-500'
                  : 'bg-amber-500 text-black hover:bg-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.3)] hover:shadow-[0_0_25px_rgba(245,158,11,0.5)]'
              }`}
            >
              {isSimulating ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-black/30 border-t-black"></div>
                  模拟计算中...
                </>
              ) : (
                <>
                  <Send size={18} />
                  模拟执行
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Result Area */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="overflow-hidden rounded-2xl border border-gray-200 bg-gradient-to-br from-white/80 to-white/40 shadow-2xl backdrop-blur-md dark:border-[rgba(255,255,255,0.1)] dark:from-[rgba(255,255,255,0.05)] dark:to-transparent"
          >
            <div className="flex items-center gap-3 border-b border-gray-200 bg-white/70 px-6 py-4 dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(255,255,255,0.02)]">
              <Info className="text-blue-400" size={20} />
              <h4 className="font-semibold text-gray-900 dark:text-white">预估分析结果</h4>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {result.split('\n').map((line, idx) => {
                  const isAdvice = line.startsWith('建议：');
                  return (
                    <div 
                      key={idx} 
                      className={`flex items-start gap-3 rounded-xl p-4 ${
                        isAdvice 
                          ? 'border border-blue-500/20 bg-blue-500/10 text-blue-900 dark:text-blue-100'
                          : 'bg-gray-100 text-gray-800 dark:bg-[rgba(255,255,255,0.03)] dark:text-gray-200'
                      }`}
                    >
                      {isAdvice ? (
                        <ArrowRight className="mt-0.5 flex-shrink-0 text-blue-400" size={18} />
                      ) : (
                        <div className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
                      )}
                      <p className="leading-relaxed">{line}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

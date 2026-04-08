import { useState, useRef, useEffect } from 'react';
import { 
  Send, Bot, User, Sparkles, Loader2, FileText, Download, X, Eye, Search, 
  ArrowLeft, Filter, SortAsc, SortDesc, Calendar
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { GoogleGenAI } from '@google/genai';
import ReactMarkdown from 'react-markdown';
import { Message, Agent } from '../types';
import { cn } from '../lib/utils';

interface AgentDetailProps {
  agent: Agent;
  onBack: () => void;
}

const mockFiles = [
  { id: 'f1', name: '市场竞争分析报告_2024.pdf', date: '2026-04-03 10:20', size: '2.4 MB', type: 'pdf' },
  { id: 'f2', name: '选品建议清单_Q2.xlsx', date: '2026-04-02 15:45', size: '1.1 MB', type: 'xlsx' },
  { id: 'f3', name: '品牌视觉规范手册.pdf', date: '2026-04-01 09:12', size: '5.8 MB', type: 'pdf' },
  { id: 'f4', name: 'Listing优化方案_B08X.docx', date: '2026-03-30 14:30', size: '850 KB', type: 'docx' },
];

export default function AgentDetail({ agent, onBack }: AgentDetailProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'model', text: `您好！我是${agent.name}。我已经准备好为您提供专业的支持。您可以向我提问，或者查看我之前为您生成的文件。`, timestamp: new Date() }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [previewFile, setPreviewFile] = useState<any>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMessage, timestamp: new Date() }]);
    setIsLoading(true);
    // Mock response
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'model', text: `这是针对“${userMessage}”的初步分析。我已经为您整理了相关数据。`, timestamp: new Date() }]);
      setIsLoading(false);
    }, 1000);
  };

  const filteredFiles = mockFiles
    .filter(f => f.name.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      const dateA = new Date(a.date).getTime();
      const dateB = new Date(b.date).getTime();
      return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
    });

  return (
    <div className="h-full flex flex-col bg-[var(--bg-main)] overflow-hidden">
      <div className="p-4 border-b border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-3">
            <div className={cn("p-2 rounded-xl", agent.color)}>
              <agent.icon size={20} />
            </div>
            <div>
              <h2 className="font-bold text-[var(--text-main)] text-sm">{agent.name}</h2>
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">AI Agent Detail</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col border-r border-[var(--border-color)] bg-[var(--bg-card)]">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex gap-3 max-w-[90%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                    msg.role === 'user' ? 'bg-slate-200 dark:bg-slate-800 text-slate-600' : 'bg-brand-600 text-white'
                  }`}>
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>
                  <div className={cn(
                    "p-4 rounded-2xl shadow-sm prose prose-sm dark:prose-invert",
                    msg.role === 'user' ? 'bg-brand-600 text-white rounded-tr-none' : 'bg-slate-50 dark:bg-slate-900 text-[var(--text-main)] rounded-tl-none border border-[var(--border-color)]'
                  )}>
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white">
                    <Bot size={16} />
                  </div>
                  <div className="p-4 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                    <Loader2 size={16} className="animate-spin text-brand-600" />
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="p-4 border-t border-[var(--border-color)]">
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="输入指令..."
                className="w-full pl-4 pr-12 py-3 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
              />
              <button
                onClick={handleSend}
                className="absolute right-1.5 top-1.5 bottom-1.5 w-9 h-9 bg-brand-600 text-white rounded-lg flex items-center justify-center hover:bg-brand-500 transition-colors"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* File List Area */}
        <div className="w-[400px] flex flex-col bg-[var(--bg-main)]">
          <div className="p-4 border-b border-[var(--border-color)] space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-[var(--text-main)]">生成文件列表</h3>
              <button 
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                title="按时间排序"
              >
                {sortOrder === 'asc' ? <SortAsc size={16} /> : <SortDesc size={16} />}
              </button>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
              <input 
                type="text" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索文件名..." 
                className="w-full pl-9 pr-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
            {filteredFiles.map((file) => (
              <div 
                key={file.id}
                className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 hover:border-brand-500 transition-all group cursor-pointer"
                onClick={() => setPreviewFile(file)}
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-rose-50 dark:bg-rose-900/20 text-rose-600 rounded-lg">
                    <FileText size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-[var(--text-main)] truncate group-hover:text-brand-600 transition-colors">{file.name}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-[10px] text-slate-500 flex items-center gap-1">
                        <Calendar size={10} />
                        {file.date}
                      </span>
                      <span className="text-[10px] text-slate-400">{file.size}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2 mt-3 pt-3 border-t border-[var(--border-color)] opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="flex items-center gap-1.5 px-3 py-1 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded-lg text-[10px] font-bold">
                    <Eye size={12} />
                    在线预览
                  </button>
                  <button className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-lg text-[10px] font-bold">
                    <Download size={12} />
                    下载
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      <AnimatePresence>
        {previewFile && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-8 bg-slate-950/50 backdrop-blur-sm">
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-[var(--bg-card)] w-full max-w-4xl h-full rounded-3xl border border-[var(--border-color)] shadow-2xl flex flex-col overflow-hidden"
            >
              <div className="p-4 border-b border-[var(--border-color)] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-rose-50 dark:bg-rose-900/20 text-rose-600 rounded-lg">
                    <FileText size={20} />
                  </div>
                  <div>
                    <h3 className="font-bold text-[var(--text-main)]">{previewFile.name}</h3>
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Document Preview</p>
                  </div>
                </div>
                <button 
                  onClick={() => setPreviewFile(null)}
                  className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
                >
                  <X size={24} />
                </button>
              </div>
              <div className="flex-1 bg-slate-100 dark:bg-slate-900 p-12 flex flex-col items-center justify-center">
                <div className="w-full max-w-md bg-white dark:bg-slate-800 aspect-[3/4] shadow-2xl rounded-xl border border-slate-200 dark:border-slate-700 p-12 space-y-6">
                  <div className="h-6 w-3/4 bg-slate-100 dark:bg-slate-700 rounded-lg" />
                  <div className="space-y-3">
                    <div className="h-3 w-full bg-slate-50 dark:bg-slate-700/50 rounded" />
                    <div className="h-3 w-full bg-slate-50 dark:bg-slate-700/50 rounded" />
                    <div className="h-3 w-5/6 bg-slate-50 dark:bg-slate-700/50 rounded" />
                  </div>
                  <div className="h-40 w-full bg-slate-50 dark:bg-slate-700/50 rounded-xl" />
                </div>
                <p className="mt-8 text-slate-500 font-medium">正在加载文档预览...</p>
              </div>
              <div className="p-6 border-t border-[var(--border-color)] flex justify-end gap-4">
                <button 
                  onClick={() => setPreviewFile(null)}
                  className="px-6 py-2.5 text-slate-500 font-bold hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-all"
                >
                  关闭
                </button>
                <button className="px-8 py-2.5 bg-brand-600 text-white font-bold rounded-xl hover:bg-brand-500 transition-all shadow-lg shadow-brand-500/20 flex items-center gap-2">
                  <Download size={18} />
                  立即下载
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

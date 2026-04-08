import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Loader2, FileText, Download, X, Eye, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { GoogleGenAI } from '@google/genai';
import ReactMarkdown from 'react-markdown';
import { Message } from '../types';
import { cn } from '../lib/utils';

export default function AISupervisor() {
  const [messages, setMessages] = useState<Message[]>([
    { 
      role: 'model', 
      text: '你好！我是你的AI主管。我已经为你生成了上周的运营分析报告，你可以点击查看。', 
      timestamp: new Date(),
      file: { name: '2026-W14-运营分析报告.pdf', url: '#', type: 'pdf' }
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [previewFile, setPreviewFile] = useState<{ name: string; url: string; type: string } | null>(null);
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

    try {
      const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || '' });
      const response = await ai.models.generateContent({
        model: 'gemini-3-flash-preview',
        contents: messages.map(m => ({
          role: m.role,
          parts: [{ text: m.text }]
        })).concat([{ role: 'user', parts: [{ text: userMessage }] }]),
        config: {
          systemInstruction: "你是一个专业的亚马逊运营AI主管。如果用户要求生成文档，请在回复中包含文档信息。你的名字是'AI主管'。"
        }
      });

      const aiText = response.text || '抱歉，我暂时无法回答这个问题。';
      
      // Mock file generation for demo
      let file = undefined;
      if (userMessage.includes('报告') || userMessage.includes('文档')) {
        file = { name: 'AI生成文档.pdf', url: '#', type: 'pdf' };
      }

      setMessages(prev => [...prev, { role: 'model', text: aiText, timestamp: new Date(), file }]);
    } catch (error) {
      console.error('AI Error:', error);
      setMessages(prev => [...prev, { role: 'model', text: '连接AI服务时出现错误，请稍后再试。', timestamp: new Date() }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex bg-[var(--bg-main)] overflow-hidden">
      <div className={cn("flex-1 flex flex-col transition-all duration-300", previewFile ? "mr-[400px]" : "")}>
        <div className="p-4 border-b border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
              <Bot size={24} />
            </div>
            <div>
              <h2 className="font-bold text-[var(--text-main)]">AI主管</h2>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Online · Professional Advisor</span>
              </div>
            </div>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded-xl text-xs font-bold hover:bg-brand-100 transition-colors">
            <Sparkles size={14} />
            历史对话
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          <AnimatePresence initial={false}>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                    msg.role === 'user' ? 'bg-slate-200 dark:bg-slate-800 text-slate-600' : 'bg-brand-600 text-white'
                  }`}>
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>
                  <div className="space-y-2">
                    <div className={cn(
                      "p-4 rounded-2xl shadow-sm",
                      msg.role === 'user' 
                        ? 'bg-brand-600 text-white rounded-tr-none' 
                        : 'bg-[var(--bg-card)] text-[var(--text-main)] rounded-tl-none border border-[var(--border-color)]'
                    )}>
                      <div className="prose prose-sm max-w-none prose-slate dark:prose-invert">
                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                      </div>
                    </div>
                    {msg.file && (
                      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 flex items-center justify-between gap-4 shadow-sm">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="p-2 bg-rose-50 dark:bg-rose-900/20 text-rose-600 rounded-lg">
                            <FileText size={18} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-bold text-[var(--text-main)] truncate">{msg.file.name}</p>
                            <p className="text-[10px] text-slate-500 uppercase">{msg.file.type.toUpperCase()} · 1.2 MB</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button 
                            onClick={() => setPreviewFile(msg.file!)}
                            className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-all"
                            title="在线预览"
                          >
                            <Eye size={16} />
                          </button>
                          <button className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-all" title="下载">
                            <Download size={16} />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex gap-3 max-w-[80%]">
                <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white">
                  <Bot size={16} />
                </div>
                <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin text-brand-600" />
                  <span className="text-xs text-slate-500 italic">AI主管正在思考中...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-6 bg-[var(--bg-card)] border-t border-[var(--border-color)]">
          <div className="max-w-4xl mx-auto relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="输入你的问题，例如：'分析本周的ACOS升高的原因'..."
              className="w-full pl-6 pr-14 py-4 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-[var(--bg-card)] transition-all text-sm text-[var(--text-main)]"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="absolute right-2 top-2 bottom-2 w-10 h-10 bg-brand-600 text-white rounded-xl flex items-center justify-center hover:bg-brand-500 transition-colors disabled:opacity-50"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Preview Panel */}
      <AnimatePresence>
        {previewFile && (
          <motion.div
            initial={{ x: 400 }}
            animate={{ x: 0 }}
            exit={{ x: 400 }}
            className="fixed top-14 right-0 bottom-0 w-[400px] bg-[var(--bg-card)] border-l border-[var(--border-color)] shadow-2xl z-20 flex flex-col"
          >
            <div className="p-4 border-b border-[var(--border-color)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-rose-50 dark:bg-rose-900/20 text-rose-600 rounded-lg">
                  <FileText size={18} />
                </div>
                <h3 className="font-bold text-sm text-[var(--text-main)] truncate max-w-[200px]">{previewFile.name}</h3>
              </div>
              <button 
                onClick={() => setPreviewFile(null)}
                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="flex-1 bg-slate-100 dark:bg-slate-900 p-8 flex flex-col items-center justify-center text-center">
              <div className="w-full max-w-[280px] bg-white dark:bg-slate-800 aspect-[3/4] shadow-xl rounded-lg border border-slate-200 dark:border-slate-700 flex flex-col p-6 space-y-4">
                <div className="h-4 w-3/4 bg-slate-100 dark:bg-slate-700 rounded" />
                <div className="h-4 w-full bg-slate-100 dark:bg-slate-700 rounded" />
                <div className="h-4 w-5/6 bg-slate-100 dark:bg-slate-700 rounded" />
                <div className="flex-1" />
                <div className="h-8 w-full bg-brand-600/10 rounded" />
              </div>
              <p className="mt-6 text-sm font-medium text-slate-500">在线预览功能已开启</p>
              <p className="text-xs text-slate-400 mt-1">正在渲染文档内容...</p>
            </div>

            <div className="p-6 border-t border-[var(--border-color)]">
              <button className="w-full flex items-center justify-center gap-2 py-3 bg-brand-600 text-white font-bold rounded-xl hover:bg-brand-500 transition-all shadow-lg shadow-brand-500/20">
                <Download size={18} />
                立即下载文档
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

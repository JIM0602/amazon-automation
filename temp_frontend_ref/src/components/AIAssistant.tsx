import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { GoogleGenAI } from '@google/genai';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'model';
  text: string;
}

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'model', text: '你好！我是你的AI主管。我可以帮你分析店铺数据、优化广告策略或解答运营难题。今天有什么我可以帮你的吗？' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
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
    setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || '' });
      const response = await ai.models.generateContent({
        model: 'gemini-3-flash-preview',
        contents: [...messages, { role: 'user', text: userMessage }].map(m => ({
          role: m.role,
          parts: [{ text: m.text }]
        })),
        config: {
          systemInstruction: "你是一个专业的亚马逊运营AI主管，拥有10年以上的跨境电商经验。你的回答应该专业、严谨、具有实操性。你会分析销售额、ACOS、转化率等指标，并给出具体的优化建议。你的名字是'AI主管'。"
        }
      });

      const aiText = response.text || '抱歉，我暂时无法回答这个问题。';
      setMessages(prev => [...prev, { role: 'model', text: aiText }]);
    } catch (error) {
      console.error('AI Error:', error);
      setMessages(prev => [...prev, { role: 'model', text: '连接AI服务时出现错误，请稍后再试。' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-50">
      <div className="p-6 border-b border-slate-200 bg-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-600 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
            <Bot size={24} />
          </div>
          <div>
            <h2 className="font-bold text-slate-900">AI主管</h2>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-xs text-slate-500">在线 · 随时为你提供专业建议</span>
            </div>
          </div>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-brand-50 text-brand-600 rounded-xl text-sm font-medium hover:bg-brand-100 transition-colors">
          <Sparkles size={16} />
          历史对话
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex gap-3 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                  msg.role === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-brand-600 text-white'
                }`}>
                  {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className={`p-4 rounded-2xl shadow-sm ${
                  msg.role === 'user' 
                    ? 'bg-brand-600 text-white rounded-tr-none' 
                    : 'bg-white text-slate-800 rounded-tl-none border border-slate-100'
                }`}>
                  <div className="prose prose-sm max-w-none prose-slate">
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  </div>
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
              <div className="p-4 bg-white border border-slate-100 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                <Loader2 size={16} className="animate-spin text-brand-600" />
                <span className="text-sm text-slate-500 italic">AI主管正在思考中...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-6 bg-white border-t border-slate-200">
        <div className="max-w-4xl mx-auto relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入你的问题，例如：'如何降低本周的ACOS？'"
            className="w-full pl-6 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-2 bottom-2 w-10 h-10 bg-brand-600 text-white rounded-xl flex items-center justify-center hover:bg-brand-500 transition-colors disabled:opacity-50 disabled:hover:bg-brand-600"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-center text-[10px] text-slate-400 mt-3">
          AI主管的回答仅供参考，请结合实际业务情况进行决策
        </p>
      </div>
    </div>
  );
}

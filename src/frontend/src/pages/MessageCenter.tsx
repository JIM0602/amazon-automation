import { useState } from 'react';
import { 
  Mail, Send, User, AlertCircle, Archive, Trash2, MoreVertical, Search as SearchIcon
} from 'lucide-react';
import { motion } from 'motion/react';

const mockMessages = [
  { id: 1, sender: 'Amazon System', subject: 'Your seller account status update', preview: 'Important information regarding your seller account...', time: '10:24 AM', type: 'system', unread: true },
  { id: 2, sender: 'Buyer: John Doe', subject: 'Inquiry about order #114-0281014', preview: 'Hi, I would like to know when my order will be shipped...', time: 'Yesterday', type: 'buyer', unread: true },
  { id: 3, sender: 'Amazon Support', subject: 'Case ID: 123456789 - Resolved', preview: 'We have resolved your inquiry regarding the listing issue...', time: '2 days ago', type: 'system', unread: false },
  { id: 4, sender: 'Buyer: Jane Smith', subject: 'Return request for SKU-2024-001', preview: 'The item arrived damaged. I want to request a return...', time: '3 days ago', type: 'buyer', unread: false },
];

export default function MessageCenter() {
  const [selectedId, setSelectedId] = useState(1);
  const [reply, setReply] = useState('');

  const selectedMsg = mockMessages.find(m => m.id === selectedId);

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full flex flex-col md:flex-row bg-[#0a0a1a] overflow-hidden"
    >
      {/* Message List */}
      <div className="w-full md:w-80 glass flex flex-col border-b md:border-b-0 md:border-r border-[var(--color-glass-border)]">
        <div className="p-4 border-b border-[var(--color-glass-border)] space-y-4">
          <h2 className="font-bold text-gray-100">消息中心</h2>
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
            <input 
              type="text" 
              placeholder="搜索消息..." 
              className="w-full pl-9 pr-4 py-2 bg-[var(--color-surface)] border border-[var(--color-glass-border)] rounded-xl text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto custom-scrollbar pb-1">
            <button className="px-3 py-1 bg-[var(--color-accent)]/20 text-[#3B82F6] rounded-lg text-[10px] font-bold whitespace-nowrap">全部</button>
            <button className="px-3 py-1 text-gray-400 text-[10px] font-bold hover:bg-[var(--color-surface)] rounded-lg transition-colors whitespace-nowrap">未读</button>
            <button className="px-3 py-1 text-gray-400 text-[10px] font-bold hover:bg-[var(--color-surface)] rounded-lg transition-colors whitespace-nowrap">系统</button>
            <button className="px-3 py-1 text-gray-400 text-[10px] font-bold hover:bg-[var(--color-surface)] rounded-lg transition-colors whitespace-nowrap">AI报告</button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {mockMessages.map((msg) => (
            <div 
              key={msg.id}
              onClick={() => setSelectedId(msg.id)}
              className={`p-4 border-b border-[var(--color-glass-border)] cursor-pointer transition-all hover:bg-[var(--color-surface)] ${
                selectedId === msg.id ? 'bg-[var(--color-accent)]/10 border-l-4 border-l-[#3B82F6]' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-bold truncate max-w-[150px] ${
                  msg.unread ? 'text-gray-100' : 'text-gray-400'
                }`}>
                  {msg.sender}
                </span>
                <span className="text-[10px] text-gray-500 font-mono">{msg.time}</span>
              </div>
              <h4 className={`text-xs truncate mb-1 ${
                msg.unread ? 'font-bold text-gray-100' : 'text-gray-400'
              }`}>
                {msg.subject}
              </h4>
              <p className="text-[10px] text-gray-500 truncate">{msg.preview}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Message Content */}
      <div className="flex-1 flex flex-col bg-[#0a0a1a]">
        {selectedMsg ? (
          <>
            <div className="p-4 border-b border-[var(--color-glass-border)] glass flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white ${
                  selectedMsg.type === 'system' ? 'bg-amber-500/80' : 'bg-[var(--color-accent)]/80'
                }`}>
                  {selectedMsg.type === 'system' ? <AlertCircle size={20} /> : <User size={20} />}
                </div>
                <div>
                  <h3 className="font-bold text-gray-100">{selectedMsg.sender}</h3>
                  <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{selectedMsg.subject}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 hidden sm:flex">
                <button className="p-2 text-gray-400 hover:text-[#3B82F6] hover:bg-[var(--color-surface)] rounded-lg transition-all"><Archive size={18} /></button>
                <button className="p-2 text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all"><Trash2 size={18} /></button>
                <button className="p-2 text-gray-400 hover:text-gray-200 hover:bg-[var(--color-surface)] rounded-lg transition-all"><MoreVertical size={18} /></button>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-8 custom-scrollbar">
              <div className="flex justify-start">
                <div className="max-w-full sm:max-w-[80%] glass border border-[var(--color-glass-border)] rounded-2xl p-6 text-sm text-gray-300 leading-relaxed">
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--color-glass-border)]">
                    <span className="font-bold text-gray-100">From: {selectedMsg.sender}</span>
                    <span className="text-xs text-gray-500 font-mono">{selectedMsg.time}</span>
                  </div>
                  <p className="mb-4">Dear Seller,</p>
                  <p className="mb-4">{selectedMsg.preview} This is a detailed message content placeholder. In a real application, this would contain the full body of the Amazon system or buyer message.</p>
                  <p>Best regards,<br />{selectedMsg.sender}</p>
                </div>
              </div>

              <div className="flex justify-end">
                <div className="max-w-full sm:max-w-[80%] bg-[var(--color-accent)]/20 border border-[var(--color-accent)]/30 text-gray-100 rounded-2xl p-6 text-sm shadow-lg shadow-[#3B82F6]/10">
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--color-accent)]/20">
                    <span className="font-bold text-[#3B82F6]">You (Admin)</span>
                    <span className="text-xs text-[#3B82F6]/60 font-mono">Yesterday 14:20</span>
                  </div>
                  <p className="text-gray-200">Thank you for your message. We are currently investigating the issue and will get back to you as soon as possible.</p>
                </div>
              </div>
            </div>

            <div className="p-4 sm:p-6 glass border-t border-[var(--color-glass-border)]">
              <div className="relative">
                <textarea 
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="输入回复内容..." 
                  className="w-full pl-4 pr-16 py-4 bg-[var(--color-surface)] border border-[var(--color-glass-border)] rounded-2xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)] min-h-[100px] resize-none"
                />
                <button className="absolute right-4 bottom-4 w-10 h-10 bg-[#3B82F6] text-white rounded-xl flex items-center justify-center hover:bg-[#2563EB] transition-colors shadow-lg shadow-[#3B82F6]/20">
                  <Send size={18} />
                </button>
              </div>
              <div className="flex items-center gap-4 mt-3">
                <button className="text-[10px] font-bold text-[#3B82F6] uppercase tracking-wider hover:underline">使用模板回复</button>
                <button className="text-[10px] font-bold text-gray-400 uppercase tracking-wider hover:underline">标记为已解决</button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-4">
            <div className="w-20 h-20 rounded-full glass border border-[var(--color-glass-border)] flex items-center justify-center text-gray-400">
              <Mail size={40} />
            </div>
            <h3 className="font-bold text-gray-100">选择一条消息查看详情</h3>
            <p className="text-sm text-gray-500 max-w-xs mx-auto">
              您可以从左侧列表中选择系统通知或买家咨询进行查看和回复。
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

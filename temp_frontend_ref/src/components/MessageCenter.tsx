import { useState } from 'react';
import { 
  Search, Mail, Send, User, Bot, Clock, Filter, CheckCircle2, 
  AlertCircle, Archive, Trash2, MoreVertical, Search as SearchIcon
} from 'lucide-react';
import { cn } from '../lib/utils';

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
    <div className="h-full flex bg-[var(--bg-main)] overflow-hidden">
      {/* Message List */}
      <div className="w-80 border-r border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col">
        <div className="p-4 border-b border-[var(--border-color)] space-y-4">
          <h2 className="font-bold text-[var(--text-main)]">消息中心</h2>
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input 
              type="text" 
              placeholder="搜索消息..." 
              className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded-lg text-[10px] font-bold">全部</button>
            <button className="px-3 py-1 text-slate-500 text-[10px] font-bold hover:bg-slate-50 rounded-lg">未读</button>
            <button className="px-3 py-1 text-slate-500 text-[10px] font-bold hover:bg-slate-50 rounded-lg">系统</button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {mockMessages.map((msg) => (
            <div 
              key={msg.id}
              onClick={() => setSelectedId(msg.id)}
              className={cn(
                "p-4 border-b border-[var(--border-color)] cursor-pointer transition-all hover:bg-slate-50 dark:hover:bg-slate-800/50",
                selectedId === msg.id && "bg-brand-50 dark:bg-brand-900/10 border-l-4 border-l-brand-600"
              )}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={cn(
                  "text-xs font-bold truncate max-w-[150px]",
                  msg.unread ? "text-[var(--text-main)]" : "text-slate-500"
                )}>
                  {msg.sender}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">{msg.time}</span>
              </div>
              <h4 className={cn(
                "text-xs truncate mb-1",
                msg.unread ? "font-bold text-[var(--text-main)]" : "text-slate-500"
              )}>
                {msg.subject}
              </h4>
              <p className="text-[10px] text-slate-400 truncate">{msg.preview}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Message Content */}
      <div className="flex-1 flex flex-col bg-[var(--bg-card)]">
        {selectedMsg ? (
          <>
            <div className="p-4 border-b border-[var(--border-color)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-10 h-10 rounded-xl flex items-center justify-center text-white",
                  selectedMsg.type === 'system' ? "bg-amber-500" : "bg-brand-600"
                )}>
                  {selectedMsg.type === 'system' ? <AlertCircle size={20} /> : <User size={20} />}
                </div>
                <div>
                  <h3 className="font-bold text-[var(--text-main)]">{selectedMsg.sender}</h3>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{selectedMsg.subject}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="p-2 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-all"><Archive size={18} /></button>
                <button className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"><Trash2 size={18} /></button>
                <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-lg transition-all"><MoreVertical size={18} /></button>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
              <div className="flex justify-start">
                <div className="max-w-[80%] bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-2xl p-6 text-sm text-[var(--text-main)] leading-relaxed">
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--border-color)]">
                    <span className="font-bold">From: {selectedMsg.sender}</span>
                    <span className="text-xs text-slate-400 font-mono">{selectedMsg.time}</span>
                  </div>
                  <p className="mb-4">Dear Seller,</p>
                  <p className="mb-4">{selectedMsg.preview} This is a detailed message content placeholder. In a real application, this would contain the full body of the Amazon system or buyer message.</p>
                  <p>Best regards,<br />{selectedMsg.sender}</p>
                </div>
              </div>

              <div className="flex justify-end">
                <div className="max-w-[80%] bg-brand-600 text-white rounded-2xl p-6 text-sm shadow-lg shadow-brand-500/20">
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/20">
                    <span className="font-bold">You (Admin)</span>
                    <span className="text-xs text-white/60 font-mono">Yesterday 14:20</span>
                  </div>
                  <p>Thank you for your message. We are currently investigating the issue and will get back to you as soon as possible.</p>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-[var(--border-color)]">
              <div className="relative">
                <textarea 
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="输入回复内容..." 
                  className="w-full pl-4 pr-16 py-4 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[100px] resize-none"
                />
                <button className="absolute right-4 bottom-4 w-10 h-10 bg-brand-600 text-white rounded-xl flex items-center justify-center hover:bg-brand-500 transition-colors shadow-lg shadow-brand-500/20">
                  <Send size={18} />
                </button>
              </div>
              <div className="flex items-center gap-4 mt-3">
                <button className="text-[10px] font-bold text-brand-600 uppercase tracking-wider hover:underline">使用模板回复</button>
                <button className="text-[10px] font-bold text-slate-400 uppercase tracking-wider hover:underline">标记为已解决</button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-4">
            <div className="w-20 h-20 rounded-full bg-slate-50 dark:bg-slate-900 flex items-center justify-center text-slate-200">
              <Mail size={40} />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-slate-200">选择一条消息查看详情</h3>
            <p className="text-sm text-slate-500 max-w-xs mx-auto">
              您可以从左侧列表中选择系统通知或买家咨询进行查看和回复。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

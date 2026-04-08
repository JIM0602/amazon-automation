import { useState } from 'react';
import { 
  TrendingUp, 
  Search, 
  MessageSquare, 
  Filter, 
  Download,
  ExternalLink,
  ChevronRight,
  Bot
} from 'lucide-react';
import { motion } from 'motion/react';

const adData = [
  { id: 'p1', name: '智能家居摄像头 - 黑色', spend: '¥1,200', sales: '¥8,500', acos: '14.1%', roas: '7.08', status: 'active' },
  { id: 'p2', name: '无线蓝牙耳机 - 降噪版', spend: '¥2,400', sales: '¥12,000', acos: '20.0%', roas: '5.00', status: 'active' },
  { id: 'p3', name: '便携式充电宝 - 20000mAh', spend: '¥800', sales: '¥3,200', acos: '25.0%', roas: '4.00', status: 'paused' },
  { id: 'p4', name: '人体工学办公椅 - 灰色', spend: '¥3,500', sales: '¥18,000', acos: '19.4%', roas: '5.14', status: 'active' },
];

export default function AdSystem() {
  const [activeTab, setActiveTab] = useState<'data' | 'chat'>('data');

  return (
    <div className="h-full flex flex-col">
      <div className="p-8 pb-0">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">广告系统</h1>
            <p className="text-slate-500">精准投放，AI驱动广告回报率最大化</p>
          </div>
          <div className="flex bg-white border border-slate-200 rounded-xl p-1 shadow-sm">
            <button
              onClick={() => setActiveTab('data')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'data' ? 'bg-slate-900 text-white shadow-md' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <TrendingUp size={16} />
              数据看板
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'chat' ? 'bg-slate-900 text-white shadow-md' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <MessageSquare size={16} />
              广告分析Agent
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-8 pb-8">
        {activeTab === 'data' ? (
          <div className="space-y-6">
            <div className="flex items-center justify-between bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-4 flex-1">
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input 
                    type="text" 
                    placeholder="搜索产品或广告组..." 
                    className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 transition-all"
                  />
                </div>
                <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors">
                  <Filter size={16} />
                  筛选
                </button>
              </div>
              <button className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-500 transition-colors">
                <Download size={16} />
                导出报告
              </button>
            </div>

            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">产品名称</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">状态</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">花费</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">销售额</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">ACOS</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">ROAS</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {adData.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-slate-100 flex-shrink-0" />
                          <span className="font-medium text-slate-900">{item.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${
                          item.status === 'active' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${item.status === 'active' ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                          {item.status === 'active' ? '投放中' : '已暂停'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-slate-600">{item.spend}</td>
                      <td className="px-6 py-4 text-right font-mono text-slate-900 font-bold">{item.sales}</td>
                      <td className="px-6 py-4 text-right">
                        <span className={`font-mono font-bold ${parseFloat(item.acos) > 20 ? 'text-rose-600' : 'text-emerald-600'}`}>
                          {item.acos}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-slate-600">{item.roas}</td>
                      <td className="px-6 py-4">
                        <button className="p-2 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-all">
                          <ExternalLink size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm h-full flex flex-col overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500 flex items-center justify-center text-white">
                <Bot size={24} />
              </div>
              <div>
                <h3 className="font-bold text-slate-900">广告分析Agent</h3>
                <p className="text-xs text-slate-500">专注于PPC优化、关键词拓词及预算分配建议</p>
              </div>
            </div>
            <div className="flex-1 p-6 flex flex-col items-center justify-center text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center text-slate-300">
                <MessageSquare size={32} />
              </div>
              <div>
                <h4 className="font-bold text-slate-900">开始广告深度分析</h4>
                <p className="text-sm text-slate-500 max-w-xs mx-auto mt-1">
                  您可以询问：“分析本周ACOS升高的原因”或“为新品制定一套广告架构方案”。
                </p>
              </div>
              <button className="px-6 py-2.5 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition-all flex items-center gap-2">
                发起对话
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

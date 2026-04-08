import { useState } from 'react';
import { 
  Search, Filter, Download, RefreshCw, ChevronLeft, ChevronRight, 
  MoreHorizontal, Calendar, TrendingUp, MousePointer2, BarChart3, 
  Plus, Settings, LayoutGrid, List, Target, Zap, ChevronDown, CheckCircle2
} from 'lucide-react';
import { cn } from '../lib/utils';

const campaigns = [
  { id: 'c1', name: 'PC0102-尖刺2-prong', orders: 7, conv: '12.28%', acos: '17.66%', top: '-', rest: '-', product: '-', business: '-', start: '2026-02-27', end: '无结束日期', tags: '-', status: 'active' },
  { id: 'c2', name: 'PC0102-尖刺1-pull', orders: 5, conv: '31.25%', acos: '7.80%', top: '-', rest: '-', product: '-', business: '-', start: '2026-02-27', end: '无结束日期', tags: '-', status: 'active' },
  { id: 'c3', name: 'PC0102-尖刺1-核心词', orders: 1, conv: '10.00%', acos: '12.02%', top: '-', rest: '-', product: '-', business: '-', start: '2026-02-24', end: '无结束日期', tags: '-', status: 'active' },
  { id: 'c4', name: 'PC0102-尖刺3-核心词', orders: 0, conv: '0.00%', acos: '0.00%', top: '-', rest: '-', product: '-', business: '-', start: '2026-02-24', end: '无结束日期', tags: '-', status: 'active' },
  { id: 'c5', name: 'PC0102-尖刺3-核心词', orders: 1, conv: '25.00%', acos: '11.24%', top: '-', rest: '-', product: '-', business: '-', start: '2026-03-10', end: '无结束日期', tags: '-', status: 'active' },
];

export default function AdManagement() {
  const [activeSubTab, setActiveSubTab] = useState('campaigns');

  const subTabs = [
    { id: 'groups', label: '广告组合' },
    { id: 'campaigns', label: '广告活动' },
    { id: 'adgroups', label: '广告组' },
    { id: 'products', label: '广告产品' },
    { id: 'targeting', label: '投放' },
    { id: 'keywords', label: '搜索词' },
    { id: 'negative', label: '否定投放' },
    { id: 'placement', label: '广告位' },
    { id: 'logs', label: '广告日志' },
  ];

  return (
    <div className="h-full flex flex-col bg-[var(--bg-main)]">
      {/* Sub Tabs */}
      <div className="bg-[var(--bg-card)] border-b border-[var(--border-color)] px-4 flex items-center justify-between">
        <div className="flex">
          {subTabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={cn(
                "px-4 py-3 text-xs font-bold transition-all border-b-2",
                activeSubTab === tab.id 
                  ? "border-brand-600 text-brand-600" 
                  : "border-transparent text-slate-500 hover:text-[var(--text-main)]"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-4 text-[10px] text-slate-500 font-bold">
          <span>美国太平洋: 2026-04-06 03:51:38</span>
          <button className="flex items-center gap-1 text-brand-600">
            <RefreshCw size={10} />
            同步 SP预算上限
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="p-4 border-b border-[var(--border-color)] bg-[var(--bg-card)] space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>Pudiwind-...</option>
          </select>
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>广告活动类型</option>
          </select>
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>所有竞价策略</option>
          </select>
          <div className="flex items-center gap-1 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <span>已开启</span>
            <X size={12} className="text-slate-400" />
          </div>
          <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <Calendar size={14} className="text-slate-400" />
            <span>2026-03-28 ~ 2026-03-28</span>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
            <input type="checkbox" className="rounded border-slate-300" />
            对比
          </label>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input 
              type="text" 
              placeholder="请输入广告活动名称" 
              className="w-full pl-9 pr-4 py-1.5 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg text-xs"
            />
          </div>
          <button className="px-4 py-1.5 border border-[var(--border-color)] rounded-lg text-xs font-bold text-slate-500">筛选模板</button>
          <button className="px-4 py-1.5 border border-[var(--border-color)] rounded-lg text-xs font-bold text-slate-500">重置</button>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <span className="px-2 py-0.5 bg-orange-50 text-orange-600 rounded text-[10px] font-bold">有成交 3</span>
            <span className="px-2 py-0.5 bg-orange-50 text-orange-600 rounded text-[10px] font-bold">有点选无成交 10</span>
            <span className="px-2 py-0.5 bg-orange-50 text-orange-600 rounded text-[10px] font-bold">有曝光无点击 1</span>
            <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px] font-bold">无曝光 1</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar Tree */}
        <div className="w-48 border-r border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col">
          <div className="p-3 border-b border-[var(--border-color)] relative">
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
            <input type="text" placeholder="搜索广告组合" className="w-full pl-8 pr-2 py-1 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded text-[10px]" />
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
            <div className="flex items-center gap-2 px-2 py-1.5 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded text-xs font-bold">
              <LayoutGrid size={14} />
              全部广告组合
            </div>
            <div className="px-2 py-1.5 text-slate-500 text-xs hover:bg-slate-50 rounded cursor-pointer">无广告组合</div>
            <div className="px-2 py-1.5 text-slate-500 text-xs hover:bg-slate-50 rounded cursor-pointer flex items-center gap-2">
              <CheckCircle2 size={12} className="text-brand-600" />
              PC0102-SBVASIN-CPC
            </div>
          </div>
        </div>

        {/* Table Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="p-3 border-b border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button className="px-3 py-1.5 bg-brand-600 text-white rounded text-xs font-bold flex items-center gap-2">
                创建广告 <ChevronDown size={12} />
              </button>
              <button className="px-3 py-1.5 border border-[var(--border-color)] text-slate-500 rounded text-xs font-bold flex items-center gap-2">
                调整 <ChevronDown size={12} />
              </button>
              <button className="px-3 py-1.5 border border-[var(--border-color)] text-slate-300 rounded text-xs font-bold" disabled>添加标签</button>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-slate-500">
                <input type="checkbox" className="rounded border-slate-300" />
                显示图表
              </label>
              <button className="p-1.5 border border-[var(--border-color)] rounded text-slate-500"><Settings size={14} /></button>
              <button className="p-1.5 border border-[var(--border-color)] rounded text-slate-500"><Download size={14} /></button>
            </div>
          </div>

          <div className="flex-1 overflow-auto custom-scrollbar">
            <table className="erp-table min-w-[1500px]">
              <thead>
                <tr>
                  <th className="w-10"><input type="checkbox" className="rounded border-slate-300" /></th>
                  <th>广告活动</th>
                  <th className="text-right">广告订单量</th>
                  <th className="text-right">广告转化率</th>
                  <th className="text-right">ACoS</th>
                  <th className="text-right">搜索结果顶部(首页) 广告位</th>
                  <th className="text-right">搜索结果其余位置</th>
                  <th className="text-right">产品页面广告位</th>
                  <th>开始日期</th>
                  <th>结束日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr className="bg-slate-50/50 font-bold">
                  <td className="w-10"></td>
                  <td>汇总 15</td>
                  <td className="text-right">7</td>
                  <td className="text-right">12.28%</td>
                  <td className="text-right">17.66%</td>
                  <td className="text-right">-</td>
                  <td className="text-right">-</td>
                  <td className="text-right">-</td>
                  <td></td>
                  <td></td>
                  <td></td>
                </tr>
                {campaigns.map((c) => (
                  <tr key={c.id}>
                    <td className="w-10"><input type="checkbox" className="rounded border-slate-300" /></td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-emerald-500 rounded-full" />
                        <span className="text-brand-600 dark:text-brand-400 font-medium hover:underline cursor-pointer">{c.name}</span>
                      </div>
                    </td>
                    <td className="text-right font-mono">{c.orders}</td>
                    <td className="text-right font-mono">{c.conv}</td>
                    <td className="text-right font-mono font-bold text-emerald-600">{c.acos}</td>
                    <td className="text-right text-slate-400">-</td>
                    <td className="text-right text-slate-400">-</td>
                    <td className="text-right text-slate-400">-</td>
                    <td className="font-mono text-slate-500">
                      <div className="flex items-center gap-1">
                        <Calendar size={10} />
                        {c.start}
                      </div>
                    </td>
                    <td className="font-mono text-slate-500">
                      <div className="flex items-center gap-1">
                        <Calendar size={10} />
                        {c.end}
                      </div>
                    </td>
                    <td>
                      <button className="text-brand-600 hover:underline">分析</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function X({ size, className }: { size: number, className?: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
    </svg>
  );
}

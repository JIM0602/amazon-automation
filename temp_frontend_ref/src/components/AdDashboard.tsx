import { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { 
  TrendingUp, MousePointer2, BarChart3, Calendar, ChevronDown, Filter, Search, 
  Target, Zap, DollarSign, Percent, Activity, Settings, Maximize2, ChevronRight,
  ChevronUp, ChevronDown as ChevronDownIcon
} from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

const trendData = [
  { name: '04-01', date: '2026-04-01', week: '周三', spend: 425.03, orders: 45, sales: 65, revenue: 8500, clicks: 1200, impressions: 45000, conv: 3.75, acos: 12.5, acoas: 8.2 },
  { name: '04-02', date: '2026-04-02', week: '周四', spend: 410.00, orders: 38, sales: 55, revenue: 7200, clicks: 1050, impressions: 42000, conv: 3.62, acos: 14.0, acoas: 9.5 },
  { name: '04-03', date: '2026-04-03', week: '周五', spend: 380.00, orders: 30, sales: 42, revenue: 5500, clicks: 850, impressions: 38000, conv: 3.53, acos: 16.4, acoas: 10.8 },
  { name: '04-04', date: '2026-04-04', week: '周六', spend: 450.00, orders: 42, sales: 58, revenue: 7800, clicks: 1100, impressions: 44000, conv: 3.82, acos: 13.5, acoas: 8.9 },
  { name: '04-05', date: '2026-04-05', week: '周日', spend: 480.00, orders: 28, sales: 35, revenue: 5200, clicks: 800, impressions: 36000, conv: 3.50, acos: 15.2, acoas: 10.1 },
  { name: '04-06', date: '2026-04-06', week: '周一', spend: 0, orders: 0, sales: 0, revenue: 0, clicks: 0, impressions: 0, conv: 0, acos: 0, acoas: 0 },
];

const initialCampaignRanking = [
  { id: 1, name: 'PC0102-尖刺2-prong', clicks: 1250, ctr: 2.6, orders: 48, sales: 9200, qty: 65, spend: 1150, cpc: 0.92, acos: 12.5, acoas: 8.2 },
  { id: 2, name: 'PC0102-SBVASIN-CPC', clicks: 980, ctr: 2.1, orders: 35, sales: 6800, qty: 42, spend: 950, cpc: 0.97, acos: 14.0, acoas: 9.5 },
  { id: 3, name: 'DC0101-SPVKW', clicks: 850, ctr: 2.4, orders: 30, sales: 5500, qty: 38, spend: 900, cpc: 1.06, acos: 16.4, acoas: 10.8 },
  { id: 4, name: 'Home-SD-AU-VCPM', clicks: 1100, ctr: 0.8, orders: 42, sales: 7800, qty: 55, spend: 1050, cpc: 0.95, acos: 13.5, acoas: 8.9 },
];

export default function AdDashboard() {
  const [statDimension, setStatDimension] = useState<'today' | '24h'>('today');
  const [chartTime, setChartTime] = useState('month');
  const [campaignTime, setCampaignTime] = useState('7d');
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);

  const stats = [
    { title: '广告花费', value: '¥4,200', change: 15.1, icon: DollarSign, color: 'text-orange-600', bg: 'bg-orange-50 dark:bg-orange-900/20' },
    { title: '广告订单量', value: '324', change: 10.5, icon: MousePointer2, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20' },
    { title: '广告销量', value: '456', change: 8.2, icon: TrendingUp, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { title: '广告转化率', value: '3.68%', change: 1.2, icon: Activity, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
    { title: 'ACoS', value: '17.1%', change: -1.2, icon: Percent, color: 'text-rose-600', bg: 'bg-rose-50 dark:bg-rose-900/20' },
    { title: 'ACoAS', value: '12.4%', change: 0.8, icon: BarChart3, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
  ];

  const metrics = [
    { id: 'spend', title: '广告花费 (US$)', value: '425.03', mom: '-8.08%', yoy: '20.11%', color: '#f59e0b', active: true },
    { id: 'orders', title: '广告订单量', value: '45', mom: '10.5%', yoy: '15.2%', color: '#f97316', active: true },
    { id: 'sales', title: '广告销量', value: '65', mom: '8.2%', yoy: '12.4%', color: '#3b82f6', active: true },
    { id: 'conv', title: '广告转化率', value: '3.75%', mom: '1.2%', yoy: '0.8%', color: '#10b981', active: true, isPercent: true },
    { id: 'acos', title: 'ACoS', value: '61.69%', mom: '15.39%', yoy: '-50.18%', color: '#f97316', active: true, isPercent: true },
    { id: 'acoas', title: 'ACoAS', value: '29.71%', mom: '-26.41%', yoy: '-68.37%', color: '#0ea5e9', active: true, isPercent: true },
  ];

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'desc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  const sortedCampaignRanking = useMemo(() => {
    if (!sortConfig) return initialCampaignRanking;
    return [...initialCampaignRanking].sort((a, b) => {
      const aValue = a[sortConfig.key as keyof typeof a];
      const bValue = b[sortConfig.key as keyof typeof b];
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [sortConfig]);

  const SortIcon = ({ column }: { column: string }) => {
    if (sortConfig?.key !== column) return <ChevronDownIcon size={12} className="text-slate-300" />;
    return sortConfig.direction === 'asc' ? <ChevronUp size={12} className="text-brand-600" /> : <ChevronDownIcon size={12} className="text-brand-600" />;
  };

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full custom-scrollbar bg-slate-50 dark:bg-slate-950">
      {/* Part 1: Stats Overview */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-800 dark:text-slate-200">广告数据大盘</h1>
        <div className="flex bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-1 shadow-sm">
          <button
            onClick={() => setStatDimension('today')}
            className={cn("px-3 py-1 rounded-md text-xs font-medium transition-all", statDimension === 'today' ? "bg-brand-600 text-white" : "text-slate-500 hover:text-slate-800")}
          >
            站点今天
          </button>
          <button
            onClick={() => setStatDimension('24h')}
            className={cn("px-3 py-1 rounded-md text-xs font-medium transition-all", statDimension === '24h' ? "bg-brand-600 text-white" : "text-slate-500 hover:text-slate-800")}
          >
            最近24小时
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm"
          >
            <div className="flex items-center justify-between mb-2">
              <div className={cn("p-1.5 rounded-lg", stat.bg, stat.color)}>
                <stat.icon size={16} />
              </div>
              <span className={cn(
                "text-[10px] font-bold px-1.5 py-0.5 rounded-full",
                stat.change >= 0 ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600" : "bg-rose-50 dark:bg-rose-900/20 text-rose-600"
              )}>
                {stat.change >= 0 ? '↑' : '↓'} {Math.abs(stat.change)}%
              </span>
            </div>
            <p className="text-slate-500 text-[10px] uppercase tracking-wider font-bold">{stat.title}</p>
            <p className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-0.5">{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Part 2: Ad Trend Analysis (Saihu Style) */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800 dark:text-slate-200">广告综合指标</span>
            <ChevronRight size={16} className="text-slate-400" />
          </div>
          <div className="flex items-center gap-3">
            <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
              {['站点今日', '本周', '本月', '本年'].map((t) => (
                <button
                  key={t}
                  onClick={() => setChartTime(t)}
                  className={cn(
                    "px-3 py-1 rounded-md text-xs font-medium transition-all",
                    chartTime === t ? "bg-white dark:bg-slate-700 text-brand-600 shadow-sm" : "text-slate-500 hover:text-slate-800"
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs text-slate-600 dark:text-slate-300">
              <Calendar size={14} />
              <span>2026-04-01 ~ 2026-04-06</span>
            </div>
            <select className="bg-slate-100 dark:bg-slate-800 border-none rounded-lg px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300">
              <option>指标对比</option>
            </select>
            <div className="flex items-center gap-2 text-slate-400">
              <Settings size={16} className="cursor-pointer hover:text-slate-600" />
              <Maximize2 size={16} className="cursor-pointer hover:text-slate-600" />
            </div>
          </div>
        </div>

        {/* Metric Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 border-b border-slate-100 dark:border-slate-800">
          {metrics.map((metric) => (
            <div 
              key={metric.id} 
              className={cn(
                "p-4 border-r border-slate-100 dark:border-slate-800 last:border-r-0 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors",
                "border-t-4"
              )}
              style={{ borderTopColor: metric.color }}
            >
              <p className="text-xs text-slate-500 mb-1">{metric.title}</p>
              <p className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">{metric.value}</p>
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-slate-400">环比</span>
                  <span className={cn("font-bold flex items-center", metric.mom.startsWith('-') ? "text-emerald-500" : "text-rose-500")}>
                    {metric.mom} {metric.mom.startsWith('-') ? '↓' : '↑'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-slate-400">同比</span>
                  <span className={cn("font-bold flex items-center", metric.yoy.startsWith('-') ? "text-emerald-500" : "text-rose-500")}>
                    {metric.yoy} {metric.yoy.startsWith('-') ? '↓' : '↑'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Chart Area */}
        <div className="p-6 h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="name" 
                axisLine={false} 
                tickLine={false} 
                tick={({ x, y, payload }) => {
                  const item = trendData.find(d => d.name === payload.value);
                  return (
                    <g transform={`translate(${x},${y})`}>
                      <text x={0} y={0} dy={16} textAnchor="middle" fill="#94a3b8" fontSize={10}>{item?.date}</text>
                      <text x={0} y={0} dy={30} textAnchor="middle" fill="#64748b" fontSize={10} fontWeight="bold">{item?.week}</text>
                    </g>
                  );
                }}
                height={50}
              />
              <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{fontSize: 11, fill: '#94a3b8'}} />
              <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{fontSize: 11, fill: '#94a3b8'}} tickFormatter={(val) => `${val}%`} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.9)', borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              />
              <Line yAxisId="left" type="monotone" dataKey="spend" stroke="#f59e0b" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="left" type="monotone" dataKey="orders" stroke="#f97316" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="left" type="monotone" dataKey="sales" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="conv" stroke="#10b981" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="acos" stroke="#f97316" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="acoas" stroke="#0ea5e9" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Part 3: Campaign Ranking with Sorting */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h3 className="font-bold text-slate-800 dark:text-slate-200">广告活动排行榜</h3>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
              <input 
                type="text" 
                placeholder="搜索广告活动..." 
                className="pl-8 pr-4 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select 
              value={campaignTime}
              onChange={(e) => setCampaignTime(e.target.value)}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300"
            >
              <option value="today">今天</option>
              <option value="7d">最近7天</option>
              <option value="30d">最近30天</option>
            </select>
            <button className="p-2 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
              <Filter size={14} className="text-slate-500" />
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="erp-table">
            <thead>
              <tr>
                <th className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('name')}>
                  <div className="flex items-center gap-1">广告活动名 <SortIcon column="name" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('clicks')}>
                  <div className="flex items-center justify-end gap-1">点击量 <SortIcon column="clicks" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('ctr')}>
                  <div className="flex items-center justify-end gap-1">点击率 <SortIcon column="ctr" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('orders')}>
                  <div className="flex items-center justify-end gap-1">订单量 <SortIcon column="orders" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('sales')}>
                  <div className="flex items-center justify-end gap-1">销售额 <SortIcon column="sales" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('qty')}>
                  <div className="flex items-center justify-end gap-1">销售量 <SortIcon column="qty" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('spend')}>
                  <div className="flex items-center justify-end gap-1">花费 <SortIcon column="spend" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('cpc')}>
                  <div className="flex items-center justify-end gap-1">CPC <SortIcon column="cpc" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('acos')}>
                  <div className="flex items-center justify-end gap-1">ACoS <SortIcon column="acos" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('acoas')}>
                  <div className="flex items-center justify-end gap-1">ACoAS <SortIcon column="acoas" /></div>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedCampaignRanking.map((camp) => (
                <tr key={camp.id}>
                  <td className="font-medium text-brand-600 dark:text-brand-400">{camp.name}</td>
                  <td className="text-right font-mono">{camp.clicks.toLocaleString()}</td>
                  <td className="text-right font-mono">{camp.ctr}%</td>
                  <td className="text-right font-mono font-bold">{camp.orders}</td>
                  <td className="text-right font-mono font-bold">¥{camp.sales.toLocaleString()}</td>
                  <td className="text-right font-mono">{camp.qty}</td>
                  <td className="text-right font-mono text-slate-500">¥{camp.spend.toLocaleString()}</td>
                  <td className="text-right font-mono">¥{camp.cpc.toFixed(2)}</td>
                  <td className="text-right font-mono text-rose-600 font-bold">{camp.acos}%</td>
                  <td className="text-right font-mono text-indigo-600">{camp.acoas}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

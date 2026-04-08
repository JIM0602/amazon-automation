import { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { 
  TrendingUp, ShoppingBag, ClipboardList, DollarSign, Percent, 
  RotateCcw, MousePointer2, BarChart3, Calendar, ChevronDown, Filter, Search,
  Settings, Maximize2, ChevronUp, ChevronDown as ChevronDownIcon, ChevronRight
} from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

const trendData = [
  { name: '04-01', date: '2026-04-01', week: '周三', sales: 137, orders: 117, revenue: 1430.43, spend: 425.03, adSales: 689.02, acos: 61.69, acoas: 29.71 },
  { name: '04-02', date: '2026-04-02', week: '周四', sales: 145, orders: 125, revenue: 1520.50, spend: 410.00, adSales: 720.00, acos: 56.94, acoas: 26.97 },
  { name: '04-03', date: '2026-04-03', week: '周五', sales: 120, orders: 105, revenue: 1280.20, spend: 380.00, adSales: 650.00, acos: 58.46, acoas: 29.68 },
  { name: '04-04', date: '2026-04-04', week: '周六', sales: 160, orders: 140, revenue: 1680.00, spend: 450.00, adSales: 850.00, acos: 52.94, acoas: 26.78 },
  { name: '04-05', date: '2026-04-05', week: '周日', sales: 190, orders: 165, revenue: 1950.00, spend: 480.00, adSales: 980.00, acos: 48.97, acoas: 24.61 },
  { name: '04-06', date: '2026-04-06', week: '周一', sales: 0, orders: 0, revenue: 0, spend: 0, adSales: 0, acos: 0, acoas: 0 },
];

const initialSkuRanking = [
  { id: 1, image: 'https://picsum.photos/seed/p1/50/50', sku: 'SKU-2024-001', sales: 1200, orders: 85, revenue: 24000, spend: 3200, acos: 13.3, acoas: 10.2, profit: 4500, margin: 18.7, fba: 450, days: 15 },
  { id: 2, image: 'https://picsum.photos/seed/p2/50/50', sku: 'SKU-2024-002', sales: 980, orders: 72, revenue: 18500, spend: 2800, acos: 15.1, acoas: 12.5, profit: 3200, margin: 17.3, fba: 320, days: 12 },
  { id: 3, image: 'https://picsum.photos/seed/p3/50/50', sku: 'SKU-2024-003', sales: 850, orders: 60, revenue: 15200, spend: 2100, acos: 13.8, acoas: 11.1, profit: 2800, margin: 18.4, fba: 150, days: 8 },
  { id: 4, image: 'https://picsum.photos/seed/p4/50/50', sku: 'SKU-2024-004', sales: 720, orders: 55, revenue: 12800, spend: 1900, acos: 14.8, acoas: 12.0, profit: 2100, margin: 16.4, fba: 80, days: 5 },
];

export default function DataDashboard() {
  const [statDimension, setStatDimension] = useState<'today' | '24h'>('today');
  const [chartTime, setChartTime] = useState('month');
  const [skuTime, setSkuTime] = useState('7d');
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);

  const metrics = [
    { id: 'sales', title: '销量', value: '137', mom: '174%', yoy: '372.41%', color: '#3b82f6', active: true },
    { id: 'orders', title: '订单量', value: '117', mom: '148.94%', yoy: '368%', color: '#6366f1', active: true },
    { id: 'revenue', title: '销售额 (US$)', value: '1,430.43', mom: '24.90%', yoy: '279.72%', color: '#10b981', active: true },
    { id: 'spend', title: '广告花费 (US$)', value: '425.03', mom: '-8.08%', yoy: '20.11%', color: '#f59e0b', active: true },
    { id: 'adSales', title: '广告销售额 (US$)', value: '689.02', mom: '-20.34%', yoy: '141.10%', color: '#6366f1', active: true },
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

  const sortedSkuRanking = useMemo(() => {
    if (!sortConfig) return initialSkuRanking;
    return [...initialSkuRanking].sort((a, b) => {
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

  const stats = [
    { title: '销售额', value: '¥12,430.43', change: 12.5, icon: DollarSign, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
    { title: '订单量', value: '117', change: 8.2, icon: ShoppingBag, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { title: '销售量', value: '137', change: 10.5, icon: ClipboardList, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
    { title: '广告花费', value: '¥425.03', change: -5.1, icon: DollarSign, color: 'text-orange-600', bg: 'bg-orange-50 dark:bg-orange-900/20' },
    { title: '广告订单量', value: '45', change: 15.2, icon: MousePointer2, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20' },
    { title: 'ACoS', value: '61.69%', change: 15.4, icon: Percent, color: 'text-rose-600', bg: 'bg-rose-50 dark:bg-rose-900/20' },
    { title: 'ACoAS', value: '29.71%', change: -26.4, icon: BarChart3, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
    { title: '退货数量', value: '3', change: -50.0, icon: RotateCcw, color: 'text-slate-600', bg: 'bg-slate-50 dark:bg-slate-900/20' },
  ];

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full custom-scrollbar bg-slate-50 dark:bg-slate-950">
      {/* Part 1: Stats Overview */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-800 dark:text-slate-200">数据大盘</h1>
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

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
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

      {/* Part 2: Trend Analysis (Saihu Style) */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800 dark:text-slate-200">综合指标</span>
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
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-7 border-b border-slate-100 dark:border-slate-800">
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
              <Line yAxisId="left" type="monotone" dataKey="sales" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="left" type="monotone" dataKey="orders" stroke="#6366f1" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="left" type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="left" type="monotone" dataKey="spend" stroke="#f59e0b" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="acos" stroke="#f97316" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="acoas" stroke="#0ea5e9" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Part 3: SKU Ranking with Sorting */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h3 className="font-bold text-slate-800 dark:text-slate-200">SKU 排行榜</h3>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
              <input 
                type="text" 
                placeholder="搜索 SKU..." 
                className="pl-8 pr-4 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select 
              value={skuTime}
              onChange={(e) => setSkuTime(e.target.value)}
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
                <th>产品主图</th>
                <th className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('sku')}>
                  <div className="flex items-center gap-1">产品 SKU <SortIcon column="sku" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('sales')}>
                  <div className="flex items-center justify-end gap-1">销量 <SortIcon column="sales" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('orders')}>
                  <div className="flex items-center justify-end gap-1">订单量 <SortIcon column="orders" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('revenue')}>
                  <div className="flex items-center justify-end gap-1">销售额 <SortIcon column="revenue" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('spend')}>
                  <div className="flex items-center justify-end gap-1">广告花费 <SortIcon column="spend" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('acos')}>
                  <div className="flex items-center justify-end gap-1">ACoS <SortIcon column="acos" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('acoas')}>
                  <div className="flex items-center justify-end gap-1">ACoAS <SortIcon column="acoas" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('profit')}>
                  <div className="flex items-center justify-end gap-1">毛利润 <SortIcon column="profit" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('margin')}>
                  <div className="flex items-center justify-end gap-1">毛利率 <SortIcon column="margin" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('fba')}>
                  <div className="flex items-center justify-end gap-1">FBA可售 <SortIcon column="fba" /></div>
                </th>
                <th className="text-right cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => handleSort('days')}>
                  <div className="flex items-center justify-end gap-1">预计可售天数 <SortIcon column="days" /></div>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedSkuRanking.map((sku) => (
                <tr key={sku.id}>
                  <td>
                    <img src={sku.image} alt={sku.sku} className="w-10 h-10 rounded border border-slate-200 dark:border-slate-700" referrerPolicy="no-referrer" />
                  </td>
                  <td className="font-medium text-brand-600 dark:text-brand-400">{sku.sku}</td>
                  <td className="text-right font-mono">{sku.sales}</td>
                  <td className="text-right font-mono">{sku.orders}</td>
                  <td className="text-right font-mono font-bold">¥{sku.revenue.toLocaleString()}</td>
                  <td className="text-right font-mono text-slate-500">¥{sku.spend.toLocaleString()}</td>
                  <td className="text-right font-mono text-emerald-600">{sku.acos}%</td>
                  <td className="text-right font-mono text-indigo-600">{sku.acoas}%</td>
                  <td className="text-right font-mono font-bold text-emerald-600">¥{sku.profit.toLocaleString()}</td>
                  <td className="text-right font-mono">{sku.margin}%</td>
                  <td className="text-right font-mono">{sku.fba}</td>
                  <td className="text-right font-mono">
                    <span className={cn(
                      "px-2 py-0.5 rounded-full text-[10px] font-bold",
                      sku.days < 10 ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600"
                    )}>
                      {sku.days} 天
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

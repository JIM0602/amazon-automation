import { useState, useEffect, useMemo } from 'react';
import { motion } from 'motion/react';
import {
  DollarSign,
  ShoppingBag,
  TrendingUp,
  Percent,
  BarChart3,
  Activity,
  ChevronDown,
  ChevronUp,
  Search,
  AlertTriangle,
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  Target
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import api from '../api/client';

interface DashboardSummary {
  adSpend: number;
  adSpendChange: number;
  adOrders: number;
  adOrdersChange: number;
  adSales: number;
  adSalesChange: number;
  conversionRate: number;
  conversionChange: number;
  acos: number;
  acosChange: number;
  acoas: number;
  acoasChange: number;
}

interface TrendData {
  date: string;
  name: string;
  spend: number;
  orders: number;
  sales: number;
  conv: number;
  acos: number;
  acoas: number;
}

interface CampaignData {
  id: string;
  name: string;
  clicks: number;
  ctr: number;
  orders: number;
  sales: number;
  qty: number;
  spend: number;
  cpc: number;
  acos: number;
  acoas: number;
}

interface SafetyLog {
  id: string;
  timestamp: string;
  level: 'warning' | 'block' | 'info';
  message: string;
  campaign: string;
}

export default function AdDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const [chartTime, setChartTime] = useState<'today' | 'week' | 'month' | 'year'>('month');
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [trendLoading, setTrendLoading] = useState(false);

  const [campaigns, setCampaigns] = useState<CampaignData[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [campaignSearch, setCampaignSearch] = useState('');
  const [sortConfig, setSortConfig] = useState<{ key: keyof CampaignData; direction: 'asc' | 'desc' } | null>(null);

  const [safetyLogs, setSafetyLogs] = useState<SafetyLog[]>([]);

  useEffect(() => {
    let mounted = true;

    async function fetchSummary() {
      try {
        const res = await api.get('/ads/dashboard/summary');
        if (mounted && res.data) setSummary(res.data);
      } catch (err) {
        console.warn('Dashboard summary not available', err);
      } finally {
        if (mounted) setSummaryLoading(false);
      }
    }

    async function fetchCampaigns() {
      try {
        const res = await api.get('/ads/dashboard/campaigns');
        if (mounted && res.data) setCampaigns(res.data);
      } catch (err) {
        console.warn('Campaigns data not available', err);
      } finally {
        if (mounted) setCampaignsLoading(false);
      }
    }

    async function fetchSafetyLogs() {
      try {
        const res = await api.get('/ads/dashboard/safety-log');
        if (mounted && res.data) setSafetyLogs(res.data);
      } catch (err) {
        console.warn('Safety logs not available', err);
      }
    }

    fetchSummary();
    fetchCampaigns();
    fetchSafetyLogs();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    async function fetchTrend() {
      setTrendLoading(true);
      try {
        const days = chartTime === 'today' ? 1 : chartTime === 'week' ? 7 : chartTime === 'month' ? 30 : 365;
        const res = await api.get(`/ads/dashboard/trend?days=${days}`);
        if (mounted && res.data) setTrendData(res.data);
      } catch (err) {
        console.warn('Trend data not available', err);
      } finally {
        if (mounted) setTrendLoading(false);
      }
    }
    fetchTrend();
    return () => {
      mounted = false;
    };
  }, [chartTime]);

  const handleSort = (key: keyof CampaignData) => {
    let direction: 'asc' | 'desc' = 'desc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  const filteredAndSortedCampaigns = useMemo(() => {
    let filtered = campaigns.filter(c => c.name.toLowerCase().includes(campaignSearch.toLowerCase()));
    if (!sortConfig) return filtered;
    return filtered.sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [campaigns, campaignSearch, sortConfig]);

  const SortIcon = ({ column }: { column: keyof CampaignData }) => {
    if (sortConfig?.key !== column) return <ChevronDown size={14} className="text-gray-600 inline ml-1" />;
    return sortConfig.direction === 'asc' ? (
      <ChevronUp size={14} className="text-[var(--color-accent)] inline ml-1" />
    ) : (
      <ChevronDown size={14} className="text-[var(--color-accent)] inline ml-1" />
    );
  };

  const renderChange = (value: number | undefined, invertColors = false) => {
    if (value === undefined) return <span className="text-gray-500">—</span>;
    const isPositive = value >= 0;
    const colorClass = invertColors 
      ? (isPositive ? 'text-red-500' : 'text-[#10b981]') // Higher ACoS/Spend is usually "bad" (red)
      : (isPositive ? 'text-[#10b981]' : 'text-red-500'); // Higher Sales is "good" (green)
    
    return (
      <div className={`flex items-center text-sm font-medium ${colorClass}`}>
        {isPositive ? <ArrowUpRight className="w-4 h-4 mr-1" /> : <ArrowDownRight className="w-4 h-4 mr-1" />}
        <span>{Math.abs(value).toFixed(1)}%</span>
      </div>
    );
  };

  const kpis = [
    { title: '广告花费', icon: <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `$${summary.adSpend.toLocaleString()}` : '—', change: summary?.adSpendChange, invert: true },
    { title: '广告订单量', icon: <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? summary.adOrders.toLocaleString() : '—', change: summary?.adOrdersChange },
    { title: '广告销量', icon: <TrendingUp className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `$${summary.adSales.toLocaleString()}` : '—', change: summary?.adSalesChange },
    { title: '广告转化率', icon: <Activity className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `${summary.conversionRate.toFixed(1)}%` : '—', change: summary?.conversionChange },
    { title: 'ACoS', icon: <Percent className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `${summary.acos.toFixed(1)}%` : '—', change: summary?.acosChange, invert: true },
    { title: 'ACoAS', icon: <BarChart3 className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `${summary.acoas.toFixed(1)}%` : '—', change: summary?.acoasChange, invert: true },
  ];

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-gray-100">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">广告数据大盘</h1>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((kpi, i) => (
          <motion.div
            key={kpi.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="glass p-5 rounded-xl border border-white/5 bg-white/5 backdrop-blur-md relative overflow-hidden"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                {kpi.icon}
              </div>
            </div>
            <p className="text-sm text-gray-400 font-medium mb-1">{kpi.title}</p>
            <div className="flex items-end justify-between">
              <h3 className="text-2xl font-bold tracking-tight">
                {summaryLoading ? <span className="text-gray-500 text-sm font-normal">加载中...</span> : kpi.value}
              </h3>
              {!summaryLoading && renderChange(kpi.change, kpi.invert)}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Chart Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass rounded-xl border border-white/5 bg-white/5 overflow-hidden backdrop-blur-md"
      >
        <div className="p-5 border-b border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <h2 className="text-lg font-medium flex items-center gap-2">
            <Activity className="w-5 h-5 text-[var(--color-accent)]" />
            广告综合指标
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
              {([
                { id: 'today', label: '今日' },
                { id: 'week', label: '本周' },
                { id: 'month', label: '本月' },
                { id: 'year', label: '本年' }
              ] as const).map(t => (
                <button
                  key={t.id}
                  onClick={() => setChartTime(t.id)}
                  className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
                    chartTime === t.id
                      ? 'bg-white/10 text-white shadow-sm'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-6 h-[400px] w-full relative">
          {trendLoading ? (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">加载中...</div>
          ) : trendData.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">暂无数据</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} dy={10} />
                <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} dx={-10} tickFormatter={(val) => `$${val}`} />
                <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} dx={10} tickFormatter={(val) => `${val}%`} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'rgba(10, 10, 26, 0.9)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#f3f4f6' }}
                  itemStyle={{ color: '#e5e7eb' }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Line yAxisId="left" type="monotone" dataKey="spend" name="花费" stroke="#f59e0b" strokeWidth={2} dot={false} />
                <Line yAxisId="left" type="monotone" dataKey="sales" name="销量" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line yAxisId="left" type="monotone" dataKey="orders" name="订单量" stroke="#10b981" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="acos" name="ACoS" stroke="#ef4444" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Campaign Ranking Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2 glass rounded-xl border border-white/5 bg-white/5 overflow-hidden backdrop-blur-md flex flex-col"
        >
          <div className="p-5 border-b border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <Target className="w-5 h-5 text-[var(--color-accent)]" />
              广告活动排名
            </h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="搜索广告活动..."
                value={campaignSearch}
                onChange={(e) => setCampaignSearch(e.target.value)}
                className="pl-9 pr-4 py-1.5 bg-black/40 border border-white/10 rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] transition-colors w-64 text-gray-200"
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-400 uppercase bg-white/5 border-b border-white/5">
                <tr>
                  {([
                    { key: 'name', label: '广告活动名' },
                    { key: 'spend', label: '花费' },
                    { key: 'orders', label: '订单量' },
                    { key: 'sales', label: '销售额' },
                    { key: 'acos', label: 'ACoS' }
                  ] as const).map(col => (
                    <th key={col.key} className="px-6 py-4 font-medium cursor-pointer hover:text-gray-200 transition-colors" onClick={() => handleSort(col.key as keyof CampaignData)}>
                      {col.label} <SortIcon column={col.key as keyof CampaignData} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {campaignsLoading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">加载中...</td>
                  </tr>
                ) : filteredAndSortedCampaigns.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">暂无数据</td>
                  </tr>
                ) : (
                  filteredAndSortedCampaigns.map((camp, idx) => (
                    <tr key={camp.id || idx} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-200">{camp.name}</td>
                      <td className="px-6 py-4">${camp.spend.toFixed(2)}</td>
                      <td className="px-6 py-4">{camp.orders}</td>
                      <td className="px-6 py-4">${camp.sales.toFixed(2)}</td>
                      <td className="px-6 py-4">{camp.acos.toFixed(1)}%</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Side Panel: Safety Rails & Simulation */}
        <div className="space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass rounded-xl border border-white/5 bg-white/5 overflow-hidden backdrop-blur-md"
          >
            <div className="p-4 border-b border-white/5">
              <h2 className="text-base font-medium flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                安全围栏日志
              </h2>
            </div>
            <div className="p-4 space-y-3">
              {safetyLogs.length === 0 ? (
                <div className="text-center text-sm text-gray-500 py-4">暂无拦截记录</div>
              ) : (
                safetyLogs.map((log, i) => (
                  <div key={i} className="flex gap-3 text-sm p-3 rounded-lg bg-black/20 border border-white/5">
                    {log.level === 'block' ? (
                      <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                    ) : log.level === 'warning' ? (
                      <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="text-gray-200">{log.message}</p>
                      <p className="text-xs text-gray-500 mt-1">{log.campaign} • {log.timestamp}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="glass rounded-xl border border-white/5 bg-white/5 overflow-hidden backdrop-blur-md"
          >
            <div className="p-4 border-b border-white/5">
              <h2 className="text-base font-medium flex items-center gap-2">
                <Activity className="w-4 h-4 text-[var(--color-accent)]" />
                最新沙盒推演结果
              </h2>
            </div>
            <div className="p-4 text-sm">
              <div className="p-4 rounded-lg bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/20 mb-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-300">预期 ACoS</span>
                  <span className="text-lg font-bold text-[var(--color-accent)]">15.2%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">预期销量提升</span>
                  <span className="text-[#10b981] font-medium">+12.5%</span>
                </div>
              </div>
              <p className="text-gray-400 text-xs">基于过去 30 天数据，模拟提升竞价策略的整体影响。置信度：高 (89%)</p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}


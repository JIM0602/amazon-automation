import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  DollarSign,
  ShoppingBag,
  TrendingUp,
  Percent,
  BarChart3,
  Activity,
  Clock,
  ArrowUpRight,
  ArrowDownRight
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
import type { AgentRun } from '../types';

interface DashboardSummary {
  totalSales: number;
  salesChange: number;
  totalOrders: number;
  ordersChange: number;
  adSpend: number;
  adSpendChange: number;
  acos: number;
  acosChange: number;
  conversionRate: number;
  conversionChange: number;
}

interface SalesTrend {
  date: string;
  sales: number;
  orders: number;
}

interface TopProduct {
  sku: string;
  sales: number;
  orders: number;
  inventory: number;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return `${diff}秒前`;
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
  return `${Math.floor(diff / 86400)}天前`;
}

type DateRange = '7' | '30' | '90';

type SortField = 'sku' | 'sales' | 'orders' | 'inventory';
type SortDirection = 'asc' | 'desc';

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const [dateRange, setDateRange] = useState<DateRange>('30');
  const [trendData, setTrendData] = useState<SalesTrend[]>([]);
  const [trendLoading, setTrendLoading] = useState(false);

  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const [sortField, setSortField] = useState<SortField>('sales');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      // Summary
      try {
        const res = await api.get('/dashboard/summary');
        if (mounted && res.data) setSummary(res.data);
      } catch (err) {
        console.warn('Dashboard summary not available', err);
        // Fallback to null
      } finally {
        if (mounted) setSummaryLoading(false);
      }

      // Products (simulate or try fetch if endpoint existed, but we assume it might not)
      try {
        const res = await api.get('/dashboard/top-products');
        if (mounted && res.data) setTopProducts(res.data);
      } catch (err) {
        console.warn('Top products not available', err);
      } finally {
        if (mounted) setProductsLoading(false);
      }

      // Agent Runs
      try {
        const res = await api.get('/agents/runs', { params: { limit: 10 } });
        if (mounted && res.data && Array.isArray(res.data.items || res.data)) {
          setAgentRuns(res.data.items || res.data);
        }
      } catch (err) {
        console.warn('Agent runs not available', err);
      } finally {
        if (mounted) setRunsLoading(false);
      }
    }

    fetchData();
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    async function fetchTrend() {
      if (mounted) setTrendLoading(true);
      try {
        const res = await api.get('/dashboard/sales-trend', { params: { days: dateRange } });
        if (mounted && res.data) setTrendData(res.data);
      } catch (err) {
        console.warn('Sales trend not available', err);
        if (mounted) setTrendData([]);
      } finally {
        if (mounted) setTrendLoading(false);
      }
    }
    fetchTrend();
    return () => { mounted = false; };
  }, [dateRange]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedProducts = [...topProducts].sort((a, b) => {
    let valA = a[fieldToKey(sortField)];
    let valB = b[fieldToKey(sortField)];
    if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
    if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  function fieldToKey(field: SortField): keyof TopProduct {
    return field;
  }

  const renderChange = (value: number | undefined) => {
    if (value === undefined) return <span className="text-gray-500">—</span>;
    const isPositive = value >= 0;
    return (
      <div className={`flex items-center text-sm ${isPositive ? 'text-[#10b981]' : 'text-red-500'}`}>
        {isPositive ? <ArrowUpRight className="w-4 h-4 mr-1" /> : <ArrowDownRight className="w-4 h-4 mr-1" />}
        <span>{Math.abs(value).toFixed(1)}%</span>
      </div>
    );
  };

  const kpis = [
    { title: '总销售额', icon: <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `$${summary.totalSales.toLocaleString()}` : '—', change: summary?.salesChange },
    { title: '总订单量', icon: <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? summary.totalOrders.toLocaleString() : '—', change: summary?.ordersChange },
    { title: '广告花费', icon: <BarChart3 className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `$${summary.adSpend.toLocaleString()}` : '—', change: summary?.adSpendChange },
    { title: 'ACoS', icon: <Percent className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `${summary.acos.toFixed(1)}%` : '—', change: summary?.acosChange },
    { title: '转化率', icon: <TrendingUp className="w-5 h-5 text-[var(--color-accent)]" />, value: summary ? `${summary.conversionRate.toFixed(1)}%` : '—', change: summary?.conversionChange },
  ];

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-gray-100">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">数据大盘</h1>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {kpis.map((kpi, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
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
              {!summaryLoading && renderChange(kpi.change)}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Sales Trend Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass rounded-xl border border-white/5 bg-white/5 p-6 backdrop-blur-md"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
          <h2 className="text-lg font-medium flex items-center gap-2">
            <Activity className="w-5 h-5 text-[var(--color-accent)]" />
            销售与订单趋势
          </h2>
          <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
            {(['7', '30', '90'] as DateRange[]).map(days => (
              <button
                key={days}
                onClick={() => setDateRange(days)}
                className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
                  dateRange === days
                    ? 'bg-white/10 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }`}
              >
                {days}天
              </button>
            ))}
          </div>
        </div>

        <div className="h-[300px] w-full relative">
          {trendLoading ? (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">加载中...</div>
          ) : trendData.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">暂无数据</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#9ca3af" 
                  tick={{ fill: '#9ca3af', fontSize: 12 }} 
                  axisLine={false} 
                  tickLine={false} 
                />
                <YAxis 
                  yAxisId="left" 
                  stroke="#9ca3af" 
                  tick={{ fill: '#9ca3af', fontSize: 12 }} 
                  axisLine={false} 
                  tickLine={false} 
                  tickFormatter={(val) => `$${val}`}
                />
                <YAxis 
                  yAxisId="right" 
                  orientation="right" 
                  stroke="#9ca3af" 
                  tick={{ fill: '#9ca3af', fontSize: 12 }} 
                  axisLine={false} 
                  tickLine={false} 
                />
                <Tooltip 
                  contentStyle={{ 
                    background: 'rgba(0,0,0,0.8)', 
                    border: '1px solid rgba(255,255,255,0.1)', 
                    borderRadius: '8px', 
                    color: '#fff' 
                  }} 
                  itemStyle={{ color: '#fff' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                <Line 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="sales" 
                  name="销售额" 
                  stroke="var(--color-accent, #3B82F6)" 
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: 'var(--color-accent, #3B82F6)' }} 
                />
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="orders" 
                  name="订单量" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: '#10b981' }} 
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Top Products Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="xl:col-span-2 glass rounded-xl border border-white/5 bg-white/5 p-6 backdrop-blur-md overflow-hidden flex flex-col"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />
              Top Products
            </h2>
          </div>
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="text-gray-400 border-b border-white/10">
                <tr>
                  {(['sku', 'sales', 'orders', 'inventory'] as SortField[]).map(field => (
                    <th 
                      key={field} 
                      className="pb-3 px-4 font-medium cursor-pointer hover:text-gray-200 transition-colors"
                      onClick={() => handleSort(field)}
                    >
                      <div className="flex items-center gap-1">
                        {field === 'sku' ? 'SKU' : field === 'sales' ? '销售额' : field === 'orders' ? '订单量' : '库存'}
                        {sortField === field && (
                          <span className="text-[var(--color-accent)] text-xs">
                            {sortDirection === 'asc' ? '↑' : '↓'}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {productsLoading ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-gray-500">加载中...</td>
                  </tr>
                ) : sortedProducts.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-gray-500">暂无数据</td>
                  </tr>
                ) : (
                  sortedProducts.map((p) => (
                    <tr key={p.sku} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="py-3 px-4 font-medium text-gray-200">{p.sku}</td>
                      <td className="py-3 px-4">${p.sales.toLocaleString()}</td>
                      <td className="py-3 px-4">{p.orders.toLocaleString()}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          p.inventory < 10 ? 'bg-red-500/20 text-red-400' : 'bg-white/10 text-gray-300'
                        }`}>
                          {p.inventory.toLocaleString()}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Agent Activity Feed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass rounded-xl border border-white/5 bg-white/5 p-6 backdrop-blur-md flex flex-col"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <Activity className="w-5 h-5 text-[var(--color-accent)]" />
              Agent Activity
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto pr-2 space-y-4 max-h-[400px]">
            {runsLoading ? (
              <div className="py-8 text-center text-gray-500 text-sm">加载中...</div>
            ) : agentRuns.length === 0 ? (
              <div className="py-8 text-center text-gray-500 text-sm">暂无运行记录</div>
            ) : (
              agentRuns.map((run) => (
                <div key={run.id} className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                  <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                    run.status === 'success' ? 'bg-[#10b981] shadow-[0_0_8px_rgba(16,185,129,0.5)]' :
                    run.status === 'error' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' :
                    'bg-[#f59e0b] shadow-[0_0_8px_rgba(245,158,11,0.5)] animate-pulse'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-200 truncate capitalize">
                        {run.agent_type.replace('_', ' ')}
                      </span>
                      {run.started_at && (
                        <span className="text-xs text-gray-500 flex items-center gap-1 whitespace-nowrap">
                          <Clock className="w-3 h-3" />
                          {timeAgo(run.started_at)}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400 truncate">
                      {run.status === 'success' ? 'Task completed successfully' : 
                       run.status === 'error' ? run.error_message || 'Task failed' : 
                       'Running task...'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}

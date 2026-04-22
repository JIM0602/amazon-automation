import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  DollarSign,
  ShoppingBag,
  TrendingUp,
  Percent,
  Activity,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import api from '../api/client';
import TrendChart from '../components/TrendChart';
import { DataTable } from '../components/DataTable';
import type { Column, SortOrder } from '../types/table';

interface MetricValue {
  value: number;
  change_percentage: number;
}

interface DashboardMetrics {
  total_sales: MetricValue;
  total_orders: MetricValue;
  units_sold: MetricValue;
  ad_spend: MetricValue;
  ad_orders: MetricValue;
  tacos: MetricValue;
  acos: MetricValue;
  returns_count: MetricValue;
}

export interface SkuRankingItem {
  [key: string]: unknown;
  sku: string;
  image_url: string;
  sales: number;
  orders: number;
  units_sold: number;
  returns_count: number;
  ad_spend: number;
  acos: number;
  tacos: number;
  gross_profit: number | null;
  gross_margin: number | null;
  fba_stock: number;
  estimated_days: number;
}

type TimeRange = 'site_today' | 'last_24h';

const METRIC_TIME_RANGE_LABELS: Record<TimeRange, string> = {
  site_today: '站点今天',
  last_24h: '最近24小时',
};

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>('site_today');
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const [skuRanking, setSkuRanking] = useState<SkuRankingItem[]>([]);
  const [skuSummary, setSkuSummary] = useState<Partial<SkuRankingItem>>({});
  const [skuTotal, setSkuTotal] = useState(0);
  const [skuLoading, setSkuLoading] = useState(true);
  
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState('sales');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [skuTimeRange, setSkuTimeRange] = useState('site_today');
  const [skuStartDate, setSkuStartDate] = useState('');
  const [skuEndDate, setSkuEndDate] = useState('');

  const handleMetricTimeRangeChange = (range: TimeRange) => {
    setTimeRange(range);
  };

  const skuTimeRangeOptions = [
    { value: 'site_today', label: '站点今天' },
    { value: 'last_24h', label: '最近24小时' },
    { value: 'this_week', label: '本周' },
    { value: 'this_month', label: '本月' },
    { value: 'this_year', label: '本年' },
    { value: 'custom', label: '自定义' },
  ] as const;

  type SkuTimeRange = typeof skuTimeRangeOptions[number]['value'];

  const isCustomSkuTimeRange = skuTimeRange === 'custom';

  const handleSkuTimeRangeChange = (range: SkuTimeRange) => {
    setSkuTimeRange(range);
    setPage(1);
  };

  const metricRatioLabel = 'TACoS / ACoAS';

  // Fetch metrics based on timeRange
  useEffect(() => {
    let mounted = true;
    async function fetchMetrics() {
      if (mounted) setMetricsLoading(true);
      try {
        const res = await api.get('/dashboard/metrics', { params: { time_range: timeRange } });
        if (mounted && res.data) {
          setMetrics(res.data);
          const now = new Date();
          setLastUpdated(`${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`);
        }
      } catch (err) {
        console.warn('Dashboard metrics not available', err);
      } finally {
        if (mounted) setMetricsLoading(false);
      }
    }
    fetchMetrics();
    return () => { mounted = false; };
  }, [timeRange]);

  // Fetch SKU Ranking data
  useEffect(() => {
    let mounted = true;

    async function fetchSkuRanking() {
      if (isCustomSkuTimeRange && (!skuStartDate || !skuEndDate)) {
        if (mounted) setSkuLoading(false);
        return;
      }

      if (mounted) setSkuLoading(true);
      try {
        const res = await api.get('/dashboard/sku_ranking', {
          params: {
            time_range: skuTimeRange,
            sort_by: sortBy || 'sales',
            sort_order: sortOrder || 'desc',
            page,
            page_size: pageSize,
            ...(isCustomSkuTimeRange
              ? { start_date: skuStartDate, end_date: skuEndDate }
              : {}),
          }
        });
        if (mounted && res.data) {
          setSkuRanking(res.data.items || []);
          setSkuTotal(res.data.total_count || 0);
          setSkuSummary(res.data.summary_row || {});
        }
      } catch (err) {
        console.warn('SKU ranking not available', err);
      } finally {
        if (mounted) setSkuLoading(false);
      }
    }

    fetchSkuRanking();
    return () => { mounted = false; };
  }, [skuTimeRange, skuStartDate, skuEndDate, sortBy, sortOrder, page, pageSize]);

  const handleTableSort = (key: string, order: SortOrder) => {
    setSortBy(key);
    setSortOrder(order || 'desc');
    setPage(1); // Reset to page 1 on sort
  };

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
    { title: '总销售额', icon: <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />, value: metrics ? `$${metrics.total_sales.value.toLocaleString()}` : '—', change: metrics?.total_sales.change_percentage },
    { title: '总订单量', icon: <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />, value: metrics ? metrics.total_orders.value.toLocaleString() : '—', change: metrics?.total_orders.change_percentage },
    { title: '销售量', icon: <TrendingUp className="w-5 h-5 text-[var(--color-accent)]" />, value: metrics ? metrics.units_sold.value.toLocaleString() : '—', change: metrics?.units_sold.change_percentage },
    { title: '广告花费', icon: <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />, value: metrics ? `$${metrics.ad_spend.value.toLocaleString()}` : '—', change: metrics?.ad_spend.change_percentage },
    { title: '广告订单量', icon: <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />, value: metrics ? metrics.ad_orders.value.toLocaleString() : '—', change: metrics?.ad_orders.change_percentage },
    { title: metricRatioLabel, icon: <Percent className="w-5 h-5 text-[var(--color-accent)]" />, value: metrics ? `${(metrics.tacos.value * 100).toFixed(1)}% / ${(metrics.acos.value * 100).toFixed(1)}%` : '—', change: metrics?.tacos.change_percentage },
    { title: '退货数量', icon: <Activity className="w-5 h-5 text-[var(--color-accent)]" />, value: metrics ? metrics.returns_count.value.toLocaleString() : '—', change: metrics?.returns_count.change_percentage },
  ];

  const columns: Column<SkuRankingItem>[] = [
    { key: 'sku', title: 'SKU码', sortable: false },
    {
      key: 'image_url',
      title: '商品主图',
      sortable: false,
      render: (value) => (
        <img
          src={value as string}
          className="w-12 h-12 rounded object-cover"
          alt="thumbnail"
        />
      ),
    },
    { key: 'sales', title: '销售额', sortable: true, render: (val) => `$${Number(val).toLocaleString()}` },
    { key: 'orders', title: '订单量', sortable: true, render: (val) => Number(val).toLocaleString() },
    { key: 'units_sold', title: '销售量', sortable: true, render: (val) => Number(val).toLocaleString() },
    { key: 'returns_count', title: '退货量', sortable: true, render: (val) => Number(val).toLocaleString() },
    { key: 'ad_spend', title: '广告花费', sortable: true, render: (val) => `$${Number(val).toLocaleString()}` },
    { key: 'acos', title: 'ACoS', sortable: true, render: (val) => <span>{(Number(val) * 100).toFixed(1)}%</span> },
    { key: 'tacos', title: 'TACoS', sortable: true, render: (val) => <span>{(Number(val) * 100).toFixed(1)}%</span> },
    { key: 'gross_profit', title: '毛利润', sortable: true, render: () => <span className="text-gray-500">-</span> },
    { key: 'gross_margin', title: '毛利率', sortable: true, render: () => <span className="text-gray-500">-</span> },
    { key: 'fba_stock', title: 'FBA可售数', sortable: true, render: (val) => Number(val).toLocaleString() },
    { key: 'estimated_days', title: '预计可售天数', sortable: true, render: (val) => Number(val).toLocaleString() },
  ];

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-gray-900 dark:text-gray-100">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">数据大盘</h1>
        <div className="flex flex-wrap items-center gap-4">
          {lastUpdated && (
            <div className="text-xs text-[#f59e0b] bg-[#f59e0b]/10 border border-[#f59e0b]/20 px-3 py-1.5 rounded-full flex items-center shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] mr-2 animate-pulse"></span>
              Mock数据 · 最后更新: {lastUpdated}
            </div>
          )}
          <div className="flex bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10">
            {(['site_today', 'last_24h'] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => handleMetricTimeRangeChange(range)}
                className={`px-4 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                  timeRange === range
                    ? 'bg-white text-blue-600 dark:bg-white/10 dark:text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-900 hover:bg-white/50 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5'
                }`}
              >
                {METRIC_TIME_RANGE_LABELS[range]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass p-5 rounded-xl border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5 backdrop-blur-md relative overflow-hidden"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="p-2 bg-white/50 dark:bg-white/5 rounded-lg border border-gray-200 dark:border-white/10">
                {kpi.icon}
              </div>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 font-medium mb-1">{kpi.title}</p>
            <div className="flex items-end justify-between">
              <h3 className="text-2xl font-bold tracking-tight">
                {metricsLoading ? <span className="text-gray-500 text-sm font-normal">加载中...</span> : kpi.value}
              </h3>
              {!metricsLoading && renderChange(kpi.change)}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Trend Chart */}
      <TrendChart />

      {/* SKU Ranking Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass rounded-xl border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5 p-6 backdrop-blur-md overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />
            SKU排名
          </h2>
          <div className="flex flex-wrap items-center justify-end gap-3 w-full md:w-auto">
            {isCustomSkuTimeRange && (
              <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="date"
                  value={skuStartDate}
                  onChange={(e) => setSkuStartDate(e.target.value)}
                  className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
                />
                <span>-</span>
                <input
                  type="date"
                  value={skuEndDate}
                  onChange={(e) => setSkuEndDate(e.target.value)}
                  className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
                />
              </div>
            )}
            <div className="flex bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10 overflow-x-auto max-w-full">
              {skuTimeRangeOptions.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => handleSkuTimeRangeChange(value)}
                  className={`px-4 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                    skuTimeRange === value
                      ? 'bg-white text-blue-600 dark:bg-white/10 dark:text-white shadow-sm'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-white/50 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="h-[calc(100vh-21rem)] min-h-[420px] overflow-hidden">
          <DataTable
            columns={columns}
            data={skuRanking}
            loading={skuLoading}
            rowKey="sku"
            summaryRow={skuSummary}
            onSort={handleTableSort}
            stickyHeaderOffset={0}
            className="h-full"
            pagination={{
              current: page,
              pageSize: pageSize,
              total: skuTotal,
              onChange: (p, ps) => { setPage(p); setPageSize(ps); }
            }}
          />
        </div>
      </motion.div>
    </div>
  );
}

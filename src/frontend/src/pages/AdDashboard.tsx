import { useState, useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import {
  DollarSign,
  ShoppingBag,
  TrendingUp,
  Percent,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Target,
  Settings,
  Eye,
  MousePointerClick
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
import { DataTable } from '../components/DataTable';
import type { Column } from '../types/table';

interface MetricValue {
  value: number;
  change_percentage: number;
}

interface AdDashboardMetrics {
  ad_spend: MetricValue;
  ad_sales: MetricValue;
  acos: MetricValue;
  clicks: MetricValue;
  impressions: MetricValue;
  ctr: MetricValue;
  cvr: MetricValue;
  cpc: MetricValue;
  ad_orders: MetricValue;
  ad_units: MetricValue;
}

export interface CampaignRankingItem {
  [key: string]: unknown;
  name: string;
  clicks: number;
  ctr: number;
  ad_orders: number;
  ad_sales: number;
  ad_units: number;
  ad_spend: number;
  cpc: number;
  acos: number;
  tacos: number;
}

type TimeRangeCard = 'site_today' | 'last_24h';
type TimeRangeChart = 'site_today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year' | 'custom';
type TimeRangeRanking = 'site_today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year' | 'custom';
type MetricKey = 'ad_spend' | 'ad_sales' | 'acos' | 'clicks' | 'impressions' | 'ctr' | 'cvr' | 'cpc' | 'ad_units' | 'ad_orders' | 'tacos';

interface TrendData {
  date: string;
  ad_spend?: number;
  ad_sales?: number;
  acos?: number;
  clicks?: number;
  impressions?: number;
  ctr?: number;
  cvr?: number;
  cpc?: number;
  ad_units?: number;
  ad_orders?: number;
  tacos?: number;
}

const CHART_METRICS: Record<MetricKey, { label: string; color: string; yAxisId: 'left' | 'right'; isPercent?: boolean }> = {
  ad_spend: { label: '广告花费', color: '#ef4444', yAxisId: 'left' },
  ad_sales: { label: '广告销售额', color: '#8b5cf6', yAxisId: 'left' },
  acos: { label: 'ACoS', color: '#f97316', yAxisId: 'right', isPercent: true },
  clicks: { label: '点击量', color: '#3b82f6', yAxisId: 'left' },
  impressions: { label: '曝光量', color: '#10b981', yAxisId: 'left' },
  ctr: { label: 'CTR', color: '#0ea5e9', yAxisId: 'right', isPercent: true },
  cvr: { label: '转化率', color: '#f59e0b', yAxisId: 'right', isPercent: true },
  cpc: { label: 'CPC', color: '#ec4899', yAxisId: 'left' },
  ad_units: { label: '广告销量', color: '#14b8a6', yAxisId: 'left' },
  ad_orders: { label: '广告订单量', color: '#6366f1', yAxisId: 'left' },
  tacos: { label: 'TACoS / ACoAS', color: '#a855f7', yAxisId: 'right', isPercent: true },
};

const CHART_TIME_RANGES: Record<TimeRangeChart, string> = {
  site_today: '站点今天',
  last_24h: '最近24小时',
  this_week: '本周',
  this_month: '本月',
  this_year: '本年',
  custom: '自定义'
};

const MAX_METRICS = 6;

export default function AdDashboard() {
  // Metrics Cards State
  const [metrics, setMetrics] = useState<AdDashboardMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [cardTime, setCardTime] = useState<TimeRangeCard>('site_today');

  // Trend Chart State
  const [chartTime, setChartTime] = useState<TimeRangeChart>('this_week');
  const [chartStartDate, setChartStartDate] = useState<string>('');
  const [chartEndDate, setChartEndDate] = useState<string>('');
  const [chartMetrics, setChartMetrics] = useState<Set<MetricKey>>(new Set(['ad_spend', 'ad_sales', 'acos']));
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [trendLoading, setTrendLoading] = useState(false);
  const [showGearPopover, setShowGearPopover] = useState(false);
  const gearPopoverRef = useRef<HTMLDivElement>(null);

  // Campaign Ranking State
  const [campaigns, setCampaigns] = useState<CampaignRankingItem[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [campaignTimeRange, setCampaignTimeRange] = useState<TimeRangeRanking>('site_today');
  const [campaignStartDate, setCampaignStartDate] = useState('');
  const [campaignEndDate, setCampaignEndDate] = useState('');
  const [campaignPage, setCampaignPage] = useState(1);
  const [campaignPageSize, setCampaignPageSize] = useState(20);
  const [campaignTotal, setCampaignTotal] = useState(0);

  // Click outside to close popover
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (gearPopoverRef.current && !gearPopoverRef.current.contains(event.target as Node)) {
        setShowGearPopover(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch Metrics
  useEffect(() => {
    let mounted = true;
    async function fetchMetrics() {
      if (mounted) setMetricsLoading(true);
      try {
        const res = await api.get('/ads/dashboard/metrics', { params: { time_range: cardTime } });
        if (mounted && res.data) setMetrics(res.data);
      } catch (err) {
        console.warn('Dashboard metrics not available', err);
      } finally {
        if (mounted) setMetricsLoading(false);
      }
    }
    fetchMetrics();
    return () => { mounted = false; };
  }, [cardTime]);

  // Fetch Trend Data
  useEffect(() => {
    let mounted = true;
    async function fetchTrend() {
      if (chartTime === 'custom' && (!chartStartDate || !chartEndDate)) return;
      if (chartMetrics.size === 0) return;

      if (mounted) setTrendLoading(true);
      try {
        const params: Record<string, string> = {
          time_range: chartTime,
          metrics: Array.from(chartMetrics).join(',')
        };
        if (chartTime === 'custom') {
          params.start_date = chartStartDate;
          params.end_date = chartEndDate;
        }
        const res = await api.get('/ads/dashboard/trend', { params });
        if (mounted && res.data && Array.isArray(res.data.data)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const mappedData = res.data.data.map((item: any) => {
            const row: any = { ...item };
            ['acos', 'ctr', 'cvr', 'tacos'].forEach(k => {
              if (row[k] !== undefined) row[k] = row[k] * 100;
            });
            return row as TrendData;
          });
          setTrendData(mappedData);
        } else if (mounted) {
          setTrendData([]);
        }
      } catch (err) {
        console.warn('Failed to fetch trend data', err);
        if (mounted) setTrendData([]);
      } finally {
        if (mounted) setTrendLoading(false);
      }
    }
    if (chartTime !== 'custom' || (chartStartDate && chartEndDate)) {
      fetchTrend();
    }
    return () => { mounted = false; };
  }, [chartTime, chartStartDate, chartEndDate, chartMetrics]);

  // Fetch Campaign Ranking
  useEffect(() => {
    let mounted = true;
    async function fetchCampaignRanking() {
      if (campaignTimeRange === 'custom' && (!campaignStartDate || !campaignEndDate)) {
        if (mounted) setCampaignsLoading(false);
        return;
      }

      if (mounted) setCampaignsLoading(true);
      try {
        const res = await api.get('/ads/dashboard/campaign_ranking', {
          params: {
            time_range: campaignTimeRange,
            page: campaignPage,
            page_size: campaignPageSize,
            ...(campaignTimeRange === 'custom'
              ? { start_date: campaignStartDate, end_date: campaignEndDate }
              : {}),
          }
        });
        if (mounted && res.data && res.data.items) {
          setCampaigns(res.data.items);
          setCampaignTotal(res.data.total_count || res.data.items.length);
        }
      } catch (err) {
        console.warn('Campaign ranking not available', err);
      } finally {
        if (mounted) setCampaignsLoading(false);
      }
    }
    fetchCampaignRanking();
    return () => { mounted = false; };
  }, [campaignTimeRange, campaignStartDate, campaignEndDate, campaignPage, campaignPageSize]);

  const renderChange = (value: number | undefined, invertColor = false) => {
    if (value === undefined) return <span className="text-gray-500">-</span>;
    const isPositive = value >= 0;
    const isGood = invertColor ? !isPositive : isPositive;
    return (
      <div className={`flex items-center text-sm font-medium ${isGood ? 'text-[#10b981]' : 'text-red-500'}`}>
        {isPositive ? <ArrowUpRight className="w-4 h-4 mr-1" /> : <ArrowDownRight className="w-4 h-4 mr-1" />}
        <span>{Math.abs(value).toFixed(1)}%</span>
      </div>
    );
  };

  const kpiConfig = [
    { title: '广告花费', icon: <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />, key: 'ad_spend', prefix: '$', invertColor: true },
    { title: '广告销售额', icon: <TrendingUp className="w-5 h-5 text-[var(--color-accent)]" />, key: 'ad_sales', prefix: '$' },
    { title: 'ACoS', icon: <Percent className="w-5 h-5 text-[var(--color-accent)]" />, key: 'acos', suffix: '%', isPercent: true, invertColor: true },
    { title: '点击量', icon: <MousePointerClick className="w-5 h-5 text-[var(--color-accent)]" />, key: 'clicks' },
    { title: '曝光量', icon: <Eye className="w-5 h-5 text-[var(--color-accent)]" />, key: 'impressions' },
    { title: 'CTR', icon: <Percent className="w-5 h-5 text-[var(--color-accent)]" />, key: 'ctr', suffix: '%', isPercent: true },
    { title: '转化率(CVR)', icon: <Activity className="w-5 h-5 text-[var(--color-accent)]" />, key: 'cvr', suffix: '%', isPercent: true },
    { title: 'CPC', icon: <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />, key: 'cpc', prefix: '$' },
    { title: '广告订单量', icon: <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />, key: 'ad_orders' },
    { title: '广告销量', icon: <ShoppingBag className="w-5 h-5 text-[var(--color-accent)]" />, key: 'ad_units' },
  ];

  const columns: Column<CampaignRankingItem>[] = [
    { key: 'name', title: '广告活动名', sortable: false },
    { key: 'clicks', title: '广告点击量', sortable: true, render: (val) => Number(val).toLocaleString() },
    { key: 'ctr', title: '广告点击率', sortable: true, render: (val) => `${(Number(val) * 100).toFixed(2)}%` },
    { key: 'ad_orders', title: '广告订单量', sortable: true, render: (val) => Number(val).toLocaleString() },
    { key: 'ad_sales', title: '广告销售额', sortable: true, render: (val) => `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` },
    { key: 'ad_units', title: '广告销售量', sortable: true, render: (val) => Number(val).toLocaleString() },
    { key: 'ad_spend', title: '广告花费', sortable: true, render: (val) => `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` },
    { key: 'cpc', title: 'CPC', sortable: true, render: (val) => `$${Number(val).toFixed(2)}` },
    { key: 'acos', title: 'ACoS', sortable: true, render: (val) => `${(Number(val) * 100).toFixed(1)}%` },
    { key: 'tacos', title: 'TACoS / ACoAS', sortable: true, render: (val, row) => `${(Number(val) * 100).toFixed(1)}% / ${(Number(row.acos) * 100).toFixed(1)}%` },
  ];

  const hasLeftAxis = Array.from(chartMetrics).some(m => CHART_METRICS[m].yAxisId === 'left');
  const hasRightAxis = Array.from(chartMetrics).some(m => CHART_METRICS[m].yAxisId === 'right');

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-gray-900 dark:text-gray-100">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">广告数据大盘</h1>
        <div className="flex flex-wrap items-center gap-4">
          <div className="text-xs text-[#f59e0b] bg-[#f59e0b]/10 border border-[#f59e0b]/20 px-3 py-1.5 rounded-full flex items-center shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] mr-2 animate-pulse"></span>
            Mock数据
          </div>
          <div className="flex bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10">
            {(['site_today', 'last_24h'] as TimeRangeCard[]).map(range => (
              <button
                key={range}
                onClick={() => setCardTime(range)}
                className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
                  cardTime === range
                    ? 'bg-white text-blue-600 shadow-sm dark:bg-white/10 dark:text-white'
                    : 'text-gray-500 hover:text-gray-900 hover:bg-white/50 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5'
                }`}
              >
                {range === 'site_today' ? '站点今天' : '最近24小时'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {kpiConfig.map((kpi, i) => {
          const data = metrics ? metrics[kpi.key as keyof AdDashboardMetrics] : null;
          let displayVal = '-';
          if (data && data.value !== undefined) {
            let val = data.value;
            if (kpi.isPercent) val = val * 100;
            displayVal = `${kpi.prefix || ''}${val.toLocaleString(undefined, { maximumFractionDigits: kpi.isPercent || kpi.key === 'cpc' ? 2 : 0 })}${kpi.suffix || ''}`;
          }
          return (
            <motion.div
              key={kpi.key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass p-5 rounded-xl border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5 backdrop-blur-md relative overflow-hidden"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-gray-100/50 dark:bg-white/5 rounded-lg border border-gray-200/50 dark:border-white/10">
                  {kpi.icon}
                </div>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 font-medium mb-1">{kpi.title}</p>
              <div className="flex items-end justify-between">
                <h3 className="text-2xl font-bold tracking-tight">
                  {metricsLoading ? <span className="text-gray-500 text-sm font-normal">加载中...</span> : displayVal}
                </h3>
                {!metricsLoading && renderChange(data?.change_percentage, kpi.invertColor)}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Trend Chart Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass rounded-xl border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5 p-6 backdrop-blur-md"
      >
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-6 gap-4 relative">
          <h2 className="text-lg font-medium flex items-center gap-2 flex-shrink-0">
            <Activity className="w-5 h-5 text-[var(--color-accent)]" />
            广告综合指标
          </h2>

          <div className="flex flex-wrap items-center justify-end gap-3 w-full lg:w-auto">
            {chartTime === 'custom' && (
              <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input 
                  type="date" 
                  value={chartStartDate}
                  onChange={e => setChartStartDate(e.target.value)}
                  className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
                />
                <span>-</span>
                <input 
                  type="date" 
                  value={chartEndDate}
                  onChange={e => setChartEndDate(e.target.value)}
                  className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
                />
              </div>
            )}
            
            <div className="flex bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10 overflow-x-auto max-w-full">
              {(Object.entries(CHART_TIME_RANGES) as [TimeRangeChart, string][]).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setChartTime(key as TimeRangeChart)}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                    chartTime === key
                      ? 'bg-white text-blue-600 shadow-sm dark:bg-white/10 dark:text-white'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-white/50 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="relative" ref={gearPopoverRef}>
              <button
                onClick={() => setShowGearPopover(!showGearPopover)}
                className="p-2 rounded-md bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-200 dark:hover:bg-white/10 transition-colors text-gray-600 dark:text-gray-300"
              >
                <Settings className="w-5 h-5" />
              </button>
              
              {showGearPopover && (
                <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-xl shadow-xl z-50 p-4">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-medium text-sm text-gray-700 dark:text-gray-200">指标选择 ({chartMetrics.size}/{MAX_METRICS})</h3>
                  </div>
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-2">
                    {(Object.entries(CHART_METRICS) as [MetricKey, typeof CHART_METRICS[MetricKey]][]).map(([key, config]) => {
                      const mKey = key as MetricKey;
                      const isSelected = chartMetrics.has(mKey);
                      const isDisabled = !isSelected && chartMetrics.size >= MAX_METRICS;
                      return (
                        <label key={key} className={`flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
                          <input
                            type="checkbox"
                            className="rounded border-gray-600 text-[var(--color-accent)] focus:ring-[var(--color-accent)] bg-gray-800"
                            checked={isSelected}
                            disabled={isDisabled}
                            onChange={() => {
                              setChartMetrics(prev => {
                                const next = new Set(prev);
                                if (next.has(mKey)) {
                                  if (next.size > 1) next.delete(mKey);
                                } else if (next.size < MAX_METRICS) {
                                  next.add(mKey);
                                }
                                return next;
                              });
                            }}
                          />
                          <span style={{ color: config.color }}>●</span>
                          <span className="text-gray-300">{config.label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="h-[350px] w-full relative">
          {trendLoading ? (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">加载中...</div>
          ) : trendData.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">暂无数据</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 10, right: hasRightAxis ? 10 : 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#9ca3af" 
                  tick={{ fill: '#9ca3af', fontSize: 12 }} 
                  axisLine={false} 
                  tickLine={false} 
                  dy={10}
                />
                {hasLeftAxis && (
                  <YAxis 
                    yAxisId="left" 
                    stroke="#9ca3af" 
                    tick={{ fill: '#9ca3af', fontSize: 12 }} 
                    axisLine={false} 
                    tickLine={false} 
                    tickFormatter={(val) => val >= 1000 ? `${(val/1000).toFixed(1)}k` : val}
                    dx={-10}
                  />
                )}
                {hasRightAxis && (
                  <YAxis 
                    yAxisId="right" 
                    orientation="right" 
                    stroke="#9ca3af" 
                    tick={{ fill: '#9ca3af', fontSize: 12 }} 
                    axisLine={false} 
                    tickLine={false} 
                    tickFormatter={(val) => `${val}%`}
                    dx={10}
                    domain={[0, 'auto']}
                  />
                )}
                <Tooltip 
                  contentStyle={{ 
                    background: 'rgba(0,0,0,0.8)', 
                    border: '1px solid rgba(255,255,255,0.1)', 
                    borderRadius: '8px', 
                    color: '#fff' 
                  }} 
                  itemStyle={{ color: '#fff', fontSize: '14px', paddingTop: '4px' }}
                  labelStyle={{ color: '#9ca3af', fontSize: '12px', marginBottom: '8px' }}
                  formatter={(value, name) => {
                    const numValue = Number(value) || 0;
                    const strName = String(name);
                    const metric = Object.values(CHART_METRICS).find(m => m.label === strName);
                    if (metric?.isPercent) return [`${numValue.toFixed(2)}%`, strName];
                    if (strName.includes('金额') || strName.includes('花费') || strName.includes('销售额') || strName === 'CPC') return [`$${numValue.toLocaleString()}`, strName];
                    return [numValue.toLocaleString(), strName];
                  }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 20 }} />
                
                {Array.from(chartMetrics).map(key => {
                  const metric = CHART_METRICS[key];
                  return (
                    <Line 
                      key={key}
                      yAxisId={metric.yAxisId}
                      type="monotone" 
                      dataKey={key} 
                      name={metric.label} 
                      stroke={metric.color} 
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: metric.color }} 
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </motion.div>

      {/* Campaign Ranking Table Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass rounded-xl border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5 p-6 backdrop-blur-md overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium flex items-center gap-2">
            <Target className="w-5 h-5 text-[var(--color-accent)]" />
            广告活动排名
          </h2>
          <div className="flex flex-wrap items-center justify-end gap-3 w-full md:w-auto">
            {campaignTimeRange === 'custom' && (
              <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="date"
                  value={campaignStartDate}
                  onChange={(e) => setCampaignStartDate(e.target.value)}
                  className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
                />
                <span>-</span>
                <input
                  type="date"
                  value={campaignEndDate}
                  onChange={(e) => setCampaignEndDate(e.target.value)}
                  className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
                />
              </div>
            )}
            <div className="flex bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10 overflow-x-auto max-w-full">
              {(Object.entries(CHART_TIME_RANGES) as [TimeRangeRanking, string][]).map(([range, label]) => (
                <button
                  key={range}
                  onClick={() => { setCampaignTimeRange(range); setCampaignPage(1); }}
                  className={`px-4 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                    campaignTimeRange === range
                      ? 'bg-white text-blue-600 shadow-sm dark:bg-white/10 dark:text-white'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-white/50 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="h-[500px] overflow-auto">
          <DataTable
            columns={columns}
            data={campaigns}
            loading={campaignsLoading}
            rowKey="name"
            pagination={{
              current: campaignPage,
              pageSize: campaignPageSize,
              total: campaignTotal,
              onChange: (p, ps) => { setCampaignPage(p); setCampaignPageSize(ps); }
            }}
          />
        </div>
      </motion.div>
    </div>
  );
}

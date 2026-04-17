import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Activity } from 'lucide-react';
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

type TimeRange = 'site_today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year' | 'custom';
type MetricKey = 'sales' | 'orders' | 'units_sold' | 'ad_spend' | 'ad_sales' | 'acos' | 'tacos';

interface TrendData {
  date: string;
  sales?: number;
  orders?: number;
  units_sold?: number;
  ad_spend?: number;
  ad_sales?: number;
  acos?: number;
  tacos?: number;
}

const METRICS: Record<MetricKey, { label: string; color: string; yAxisId: 'left' | 'right'; isPercent?: boolean }> = {
  sales: { label: '销售额', color: '#3b82f6', yAxisId: 'left' },
  orders: { label: '订单量', color: '#10b981', yAxisId: 'left' },
  units_sold: { label: '销售量', color: '#f59e0b', yAxisId: 'left' },
  ad_spend: { label: '广告花费', color: '#ef4444', yAxisId: 'left' },
  ad_sales: { label: '广告销售额', color: '#8b5cf6', yAxisId: 'left' },
  acos: { label: 'ACoS', color: '#f97316', yAxisId: 'right', isPercent: true },
  tacos: { label: 'TACoS', color: '#06b6d4', yAxisId: 'right', isPercent: true },
};

const TIME_RANGES: Record<TimeRange, string> = {
  site_today: '站点今天',
  last_24h: '最近24小时',
  this_week: '本周',
  this_month: '本月',
  this_year: '本年',
  custom: '自定义'
};

export default function TrendChart() {
  const [timeRange, setTimeRange] = useState<TimeRange>('this_week');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  
  const [selectedMetrics, setSelectedMetrics] = useState<Set<MetricKey>>(
    new Set(['sales', 'orders', 'ad_spend'])
  );

  const [data, setData] = useState<TrendData[]>([]);
  const [loading, setLoading] = useState(false);

  const toggleMetric = (metric: MetricKey) => {
    setSelectedMetrics(prev => {
      const next = new Set(prev);
      if (next.has(metric)) {
        if (next.size > 1) next.delete(metric); // Prevent unselecting all
      } else {
        next.add(metric);
      }
      return next;
    });
  };

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      if (timeRange === 'custom' && (!startDate || !endDate)) return;
      if (selectedMetrics.size === 0) return;

      if (mounted) setLoading(true);
      try {
        const metricsParam = Array.from(selectedMetrics).join(',');
        const params: Record<string, string> = {
          time_range: timeRange,
          metrics: metricsParam
        };
        if (timeRange === 'custom') {
          params.start_date = startDate;
          params.end_date = endDate;
        }

        const res = await api.get('/dashboard/trend', { params });
        if (mounted && res.data && Array.isArray(res.data)) {
          // Multiply ACoS/TACoS by 100 on the fly
          const mappedData = res.data.map((item: TrendData) => {
            const row: TrendData = { ...item };
            if (row.acos !== undefined) row.acos = row.acos * 100;
            if (row.tacos !== undefined) row.tacos = row.tacos * 100;
            return row;
          });
          setData(mappedData);
        } else if (mounted) {
          setData([]);
        }
      } catch (err) {
        console.warn('Failed to fetch trend data', err);
        if (mounted) setData([]);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    
    // Auto trigger when custom date is fully provided or non-custom timeRange is selected
    if (timeRange !== 'custom' || (startDate && endDate)) {
      fetchData();
    } else {
      setData([]);
    }
    return () => { mounted = false; };
  }, [timeRange, startDate, endDate, selectedMetrics]);

  // Determine which Y-axes are needed
  const hasLeftAxis = Array.from(selectedMetrics).some(m => METRICS[m].yAxisId === 'left');
  const hasRightAxis = Array.from(selectedMetrics).some(m => METRICS[m].yAxisId === 'right');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="glass rounded-xl border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5 p-6 backdrop-blur-md"
    >
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-6 gap-4">
        <h2 className="text-lg font-medium flex items-center gap-2 flex-shrink-0">
          <Activity className="w-5 h-5 text-[var(--color-accent)]" />
          趋势图
        </h2>

        <div className="flex flex-wrap items-center justify-end gap-3 w-full lg:w-auto">
          {timeRange === 'custom' && (
            <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input 
                type="date" 
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
              />
              <span>-</span>
              <input 
                type="date" 
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10 rounded px-2 py-1.5 outline-none focus:border-blue-500 dark:focus:border-white/20 dark:[color-scheme:dark]"
              />
            </div>
          )}
          
          <div className="flex bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10 overflow-x-auto max-w-full">
            {(Object.entries(TIME_RANGES) as [TimeRange, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTimeRange(key)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                  timeRange === key
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

      <div className="flex flex-wrap gap-2 mb-6">
        {(Object.entries(METRICS) as [MetricKey, typeof METRICS[MetricKey]][]).map(([key, { label, color }]) => {
          const isSelected = selectedMetrics.has(key);
          return (
            <button
              key={key}
              onClick={() => toggleMetric(key)}
              style={{
                backgroundColor: isSelected ? `${color}20` : 'rgba(255,255,255,0.05)',
                borderColor: isSelected ? `${color}50` : 'rgba(255,255,255,0.1)',
                color: isSelected ? color : '#9ca3af'
              }}
              className="px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 flex items-center gap-2 hover:bg-white/10"
            >
              <div 
                className="w-2 h-2 rounded-full" 
                style={{ backgroundColor: isSelected ? color : 'transparent', border: `1px solid ${isSelected ? color : '#6b7280'}` }} 
              />
              {label}
            </button>
          );
        })}
      </div>

      <div className="h-[350px] w-full relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500">加载中...</div>
        ) : data.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500">暂无数据</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: hasRightAxis ? 10 : 10, left: 10, bottom: 0 }}>
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
                  const metric = Object.values(METRICS).find(m => m.label === strName);
                  if (metric?.isPercent) return [`${numValue.toFixed(2)}%`, strName];
                  if (strName === '销售额' || strName === '广告花费' || strName === '广告销售额') return [`$${numValue.toLocaleString()}`, strName];
                  return [numValue.toLocaleString(), strName];
                }}
              />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 20 }} />
              
              {Array.from(selectedMetrics).map(key => {
                const metric = METRICS[key];
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
  );
}

import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { 
  DollarSign, 
  Bot, 
  Cpu, 
  CalendarDays,
  AlertTriangle
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  BarChart,
  Bar,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine,
  Cell
} from 'recharts';
import api from '../api/client';

interface AgentCost {
  agent_type: string;
  total_cost: number;
  call_count: number;
}

interface ModelCost {
  model: string;
  total_cost: number;
  call_count: number;
}

interface TrendData {
  date: string;
  total_cost: number;
}

interface CostData {
  by_agent: AgentCost[];
  by_model: ModelCost[];
  daily_trend: TrendData[];
  total_cost: number;
  daily_limit: number;
  today_cost: number;
}

type Period = 'daily' | 'weekly' | 'monthly';

export default function CostMonitor() {
  const [data, setData] = useState<CostData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>('daily');
  const [days, setDays] = useState(30);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/monitoring/costs?period=${period}&days=${days}`);
      setData(res.data);
    } catch (err: any) {
      console.error('Failed to fetch cost data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [period, days]);

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

  const getPercentOfLimit = () => {
    if (!data || !data.daily_limit) return 0;
    return Math.min((data.today_cost / data.daily_limit) * 100, 100);
  };

  const limitPercent = getPercentOfLimit();
  const isNearLimit = limitPercent > 80;
  const isOverLimit = limitPercent >= 100;

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-gray-100 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-100">API 费用监控</h1>
            <p className="text-gray-400 mt-1">LLM 成本与 Agent 运行消耗追踪</p>
          </div>

          <div className="flex bg-white/5 border border-[var(--color-glass-border)] rounded-lg p-1">
            <button
              onClick={() => { setPeriod('daily'); setDays(7); }}
              className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
                period === 'daily' && days === 7 
                  ? 'bg-[var(--color-accent)] text-white' 
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              近 7 天
            </button>
            <button
              onClick={() => { setPeriod('daily'); setDays(30); }}
              className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
                period === 'daily' && days === 30 
                  ? 'bg-[var(--color-accent)] text-white' 
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              近 30 天
            </button>
          </div>
        </div>

        {error && (
          <div className="glass border border-red-500/30 bg-red-500/10 text-red-400 p-4 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
            </div>
            <button 
              onClick={fetchData}
              className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 rounded text-sm transition-colors"
            >
              重试
            </button>
          </div>
        )}

        {loading && !data ? (
          <div className="py-20 text-center text-gray-400">
            <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            正在加载数据...
          </div>
        ) : data && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass rounded-xl border border-[var(--color-glass-border)] p-6"
              >
                <div className="flex items-center gap-3 mb-2 text-gray-400">
                  <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />
                  <h3 className="font-medium">今日费用</h3>
                </div>
                <div className="text-3xl font-bold">${data.today_cost.toFixed(2)}</div>
                <div className="mt-2 text-xs text-gray-500 flex items-center gap-2">
                  <div className="h-1.5 flex-1 bg-white/10 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${
                        isOverLimit ? 'bg-red-500' : isNearLimit ? 'bg-yellow-500' : 'bg-[var(--color-accent)]'
                      }`}
                      style={{ width: `${limitPercent}%` }}
                    />
                  </div>
                  <span>{data.daily_limit ? `${limitPercent.toFixed(0)}% 预算` : ''}</span>
                </div>
              </motion.div>

              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="glass rounded-xl border border-[var(--color-glass-border)] p-6"
              >
                <div className="flex items-center gap-3 mb-2 text-gray-400">
                  <CalendarDays className="w-5 h-5 text-[var(--color-accent)]" />
                  <h3 className="font-medium">阶段总费用 ({days}天)</h3>
                </div>
                <div className="text-3xl font-bold">${data.total_cost.toFixed(2)}</div>
              </motion.div>

              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass rounded-xl border border-[var(--color-glass-border)] p-6"
              >
                <div className="flex items-center gap-3 mb-2 text-gray-400">
                  <Bot className="w-5 h-5 text-[var(--color-accent)]" />
                  <h3 className="font-medium">Agent 数量</h3>
                </div>
                <div className="text-3xl font-bold">{data.by_agent.length}</div>
              </motion.div>

              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="glass rounded-xl border border-[var(--color-glass-border)] p-6"
              >
                <div className="flex items-center gap-3 mb-2 text-gray-400">
                  <Cpu className="w-5 h-5 text-[var(--color-accent)]" />
                  <h3 className="font-medium">总调用次数</h3>
                </div>
                <div className="text-3xl font-bold">
                  {data.by_model.reduce((acc, curr) => acc + curr.call_count, 0)}
                </div>
              </motion.div>
            </div>

            {/* Trend Chart */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="glass rounded-xl border border-[var(--color-glass-border)] p-6"
            >
              <h2 className="text-lg font-medium mb-6 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-[var(--color-accent)]" />
                日度费用趋势
              </h2>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.daily_trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#9ca3af" 
                      tick={{ fill: '#9ca3af', fontSize: 12 }}
                      tickFormatter={(val) => val.split('-').slice(1).join('/')}
                    />
                    <YAxis 
                      stroke="#9ca3af" 
                      tick={{ fill: '#9ca3af', fontSize: 12 }}
                      tickFormatter={(val) => `$${val}`}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(10, 10, 26, 0.9)', 
                        borderColor: 'rgba(255,255,255,0.1)',
                        color: '#f3f4f6'
                      }}
                      itemStyle={{ color: 'var(--color-accent)' }}
                      formatter={(val: any) => [`$${Number(val).toFixed(4)}`, '总费用']}
                      labelStyle={{ color: '#9ca3af', marginBottom: '8px' }}
                    />
                    {data.daily_limit > 0 && (
                      <ReferenceLine 
                        y={data.daily_limit} 
                        stroke="#ef4444" 
                        strokeDasharray="3 3" 
                        label={{ position: 'top', value: '预算限制', fill: '#ef4444', fontSize: 12 }} 
                      />
                    )}
                    <Line 
                      type="monotone" 
                      dataKey="total_cost" 
                      stroke="var(--color-accent)" 
                      strokeWidth={3}
                      dot={{ fill: 'var(--color-accent)', r: 4 }}
                      activeDot={{ r: 6, strokeWidth: 0 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            {/* Bottom Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Agent Table */}
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="glass rounded-xl border border-[var(--color-glass-border)] p-6 overflow-hidden flex flex-col"
              >
                <h2 className="text-lg font-medium mb-6 flex items-center gap-2">
                  <Bot className="w-5 h-5 text-[var(--color-accent)]" />
                  按 Agent 统计
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr className="border-b border-white/10 text-gray-400">
                        <th className="pb-3 font-medium">Agent 类型</th>
                        <th className="pb-3 font-medium text-right">调用次数</th>
                        <th className="pb-3 font-medium text-right">总费用</th>
                        <th className="pb-3 font-medium text-right">平均单次</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {data.by_agent.map((agent, i) => (
                        <tr key={agent.agent_type || i} className="hover:bg-white/5 transition-colors">
                          <td className="py-3 text-gray-200 capitalize">
                            {agent.agent_type.replace(/_/g, ' ')}
                          </td>
                          <td className="py-3 text-right">{agent.call_count}</td>
                          <td className="py-3 text-right font-medium text-[var(--color-accent)]">
                            ${agent.total_cost.toFixed(4)}
                          </td>
                          <td className="py-3 text-right text-gray-400">
                            ${(agent.total_cost / Math.max(1, agent.call_count)).toFixed(4)}
                          </td>
                        </tr>
                      ))}
                      {data.by_agent.length === 0 && (
                        <tr>
                          <td colSpan={4} className="py-8 text-center text-gray-500">暂无数据</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </motion.div>

              {/* Model Chart */}
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="glass rounded-xl border border-[var(--color-glass-border)] p-6"
              >
                <h2 className="text-lg font-medium mb-6 flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-[var(--color-accent)]" />
                  按模型费用分布
                </h2>
                <div className="h-[300px] w-full">
                  {data.by_model.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart 
                        data={data.by_model} 
                        layout="vertical"
                        margin={{ top: 0, right: 30, left: 40, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
                        <XAxis 
                          type="number" 
                          stroke="#9ca3af" 
                          tick={{ fill: '#9ca3af', fontSize: 12 }}
                          tickFormatter={(val) => `$${val}`}
                        />
                        <YAxis 
                          type="category" 
                          dataKey="model" 
                          stroke="#9ca3af" 
                          tick={{ fill: '#9ca3af', fontSize: 12 }}
                          width={100}
                        />
                        <Tooltip 
                          cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                          contentStyle={{ 
                            backgroundColor: 'rgba(10, 10, 26, 0.9)', 
                            borderColor: 'rgba(255,255,255,0.1)',
                            color: '#f3f4f6'
                          }}
                          formatter={(val: any, name: any) => {
                            if (name === 'total_cost') return [`$${Number(val).toFixed(4)}`, '费用'];
                            return [val, name];
                          }}
                        />
                        <Bar 
                          dataKey="total_cost" 
                          radius={[0, 4, 4, 0]}
                          barSize={24}
                        >
                          {data.by_model.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-500">
                      暂无数据
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

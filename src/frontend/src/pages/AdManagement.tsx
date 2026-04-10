import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  Target,
  Search,
  Filter,
  Calendar,
  Play,
  History,
  Activity,
  Zap,
  MoreHorizontal
} from 'lucide-react';
import api from '../api/client';

interface Campaign {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'paused' | 'archived';
  orders: number;
  convRate: number;
  acos: number;
  startDate: string;
  endDate: string | null;
  budget: number;
}

interface Recommendation {
  id: string;
  campaignId: string;
  campaignName: string;
  currentBid: number;
  suggestedBid: number;
  reason: string;
  confidence: number;
  status: 'pending' | 'approved' | 'rejected';
}

interface HistoryLog {
  id: string;
  timestamp: string;
  action: string;
  result: string;
}

const TABS = [
  '广告组合', '广告活动', '广告组', '广告产品', 
  '投放', '搜索词', '否定投放', '广告位', '广告日志'
];

export default function AdManagement() {
  const [activeTab, setActiveTab] = useState('广告活动');
  
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);

  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recsLoading, setRecsLoading] = useState(true);

  const [historyLogs, setHistoryLogs] = useState<HistoryLog[]>([]);

  // Simulation form
  const [simMode, setSimMode] = useState('What-If');
  const [simDays, setSimDays] = useState(30);
  const [simTargetAcos, setSimTargetAcos] = useState(15);
  const [simRunning, setSimRunning] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const [campsRes, recsRes, histRes] = await Promise.allSettled([
          api.get('/ads/manage/campaigns'),
          api.get('/ads/manage/recommendations'),
          api.get('/ads/manage/history')
        ]);
        
        if (!mounted) return;

        if (campsRes.status === 'fulfilled' && campsRes.value.data) {
          setCampaigns(campsRes.value.data);
        }
        if (recsRes.status === 'fulfilled' && recsRes.value.data) {
          setRecommendations(recsRes.value.data);
        }
        if (histRes.status === 'fulfilled' && histRes.value.data) {
          setHistoryLogs(histRes.value.data);
        }
      } catch (err) {
        console.warn('Failed to fetch ad management data', err);
      } finally {
        if (mounted) {
          setCampaignsLoading(false);
          setRecsLoading(false);
        }
      }
    }
    fetchData();
    return () => { mounted = false; };
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await api.post(`/ads/manage/recommendations/${id}/approve`);
      setRecommendations(prev => prev.filter(r => r.id !== id));
      // In a real app, you might create an approval request via POST /approvals instead
    } catch (err) {
      console.error('Failed to approve recommendation', err);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.post(`/ads/manage/recommendations/${id}/reject`);
      setRecommendations(prev => prev.filter(r => r.id !== id));
    } catch (err) {
      console.error('Failed to reject recommendation', err);
    }
  };

  const runSimulation = async () => {
    setSimRunning(true);
    setSimResult(null);
    try {
      const res = await api.post('/ads/simulation/run', {
        mode: simMode,
        days: simDays,
        targetAcos: simTargetAcos
      });
      setSimResult(res.data || { success: true, message: '模拟完成' });
    } catch (err) {
      console.error('Simulation failed', err);
      setSimResult({ error: true, message: '模拟运行失败' });
    } finally {
      setSimRunning(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-gray-100 flex flex-col h-[calc(100vh-theme(spacing.16))]">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">广告管理</h1>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm hover:bg-white/10 transition-colors flex items-center gap-2">
            <Activity className="w-4 h-4" />
            批量操作
          </button>
          <button className="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-[var(--color-accent)]/20">
            <Target className="w-4 h-4" />
            新建广告活动
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/10 overflow-x-auto custom-scrollbar">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
              activeTab === tab
                ? 'border-[var(--color-accent)] text-[var(--color-accent)]'
                : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-white/20'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 flex-1 min-h-0">
        
        {/* Main Content Area (Table) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="xl:col-span-2 glass rounded-xl border border-white/5 bg-white/5 backdrop-blur-md flex flex-col overflow-hidden"
        >
          {/* Filters */}
          <div className="p-4 border-b border-white/5 flex flex-wrap gap-3 items-center bg-black/20">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="搜索广告活动..."
                className="pl-9 pr-4 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm focus:outline-none focus:border-[var(--color-accent)] transition-colors w-64 text-gray-200"
              />
            </div>
            
            <button className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm hover:bg-white/10 transition-colors flex items-center gap-2 text-gray-300">
              <Filter className="w-4 h-4" />
              状态: 开启
            </button>
            <button className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm hover:bg-white/10 transition-colors flex items-center gap-2 text-gray-300">
              <Calendar className="w-4 h-4" />
              过去30天
            </button>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto custom-scrollbar">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-400 uppercase bg-white/5 border-b border-white/5 sticky top-0 backdrop-blur-md z-10">
                <tr>
                  <th className="px-6 py-4 w-12"><input type="checkbox" className="rounded border-gray-600 bg-transparent" /></th>
                  <th className="px-6 py-4 font-medium">广告活动</th>
                  <th className="px-6 py-4 font-medium">状态</th>
                  <th className="px-6 py-4 font-medium">广告订单量</th>
                  <th className="px-6 py-4 font-medium">广告转化率</th>
                  <th className="px-6 py-4 font-medium">ACoS</th>
                  <th className="px-6 py-4 font-medium">预算</th>
                  <th className="px-6 py-4 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {campaignsLoading ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-8 text-center text-gray-500">加载中...</td>
                  </tr>
                ) : campaigns.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-8 text-center text-gray-500">暂无数据</td>
                  </tr>
                ) : (
                  campaigns.map((camp, idx) => (
                    <tr key={camp.id || idx} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4"><input type="checkbox" className="rounded border-gray-600 bg-transparent" /></td>
                      <td className="px-6 py-4 font-medium text-[var(--color-accent)]">{camp.name}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${camp.status === 'active' ? 'bg-[#10b981]' : camp.status === 'paused' ? 'bg-amber-500' : 'bg-gray-500'}`}></span>
                          <span className="capitalize">{camp.status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">{camp.orders}</td>
                      <td className="px-6 py-4">{camp.convRate.toFixed(1)}%</td>
                      <td className="px-6 py-4">{camp.acos.toFixed(1)}%</td>
                      <td className="px-6 py-4">${camp.budget}</td>
                      <td className="px-6 py-4">
                        <button className="p-1 hover:bg-white/10 rounded text-gray-400 hover:text-gray-200">
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Right Sidebar */}
        <div className="space-y-6 overflow-y-auto custom-scrollbar pr-2">
          
          {/* Recommendations Panel */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass rounded-xl border border-[var(--color-accent)]/30 bg-white/5 overflow-hidden backdrop-blur-md shadow-[0_0_15px_rgba(59,130,246,0.05)]"
          >
            <div className="p-4 border-b border-white/5 flex items-center justify-between bg-[var(--color-accent)]/5">
              <h2 className="text-base font-medium flex items-center gap-2 text-[var(--color-accent)]">
                <Zap className="w-4 h-4" />
                算法推荐
              </h2>
              <span className="px-2 py-0.5 bg-[var(--color-accent)] text-white text-xs font-bold rounded-full">
                {recommendations.length}
              </span>
            </div>
            <div className="p-4 space-y-4">
              {recsLoading ? (
                <div className="text-center text-gray-500 py-4 text-sm">加载中...</div>
              ) : recommendations.length === 0 ? (
                <div className="text-center text-gray-500 py-4 text-sm">暂无待处理推荐</div>
              ) : (
                recommendations.map(rec => (
                  <div key={rec.id} className="p-3 rounded-lg bg-black/40 border border-white/5 space-y-3">
                    <div>
                      <p className="text-sm font-medium text-gray-200 truncate" title={rec.campaignName}>{rec.campaignName}</p>
                      <p className="text-xs text-gray-400 mt-1">{rec.reason}</p>
                    </div>
                    <div className="flex items-center justify-between text-sm bg-white/5 p-2 rounded">
                      <div className="flex flex-col">
                        <span className="text-gray-500 text-xs">当前竞价</span>
                        <span className="text-gray-300">${rec.currentBid.toFixed(2)}</span>
                      </div>
                      <Activity className="w-4 h-4 text-gray-600" />
                      <div className="flex flex-col items-end">
                        <span className="text-[var(--color-accent)] text-xs">建议竞价</span>
                        <span className="text-[var(--color-accent)] font-medium">${rec.suggestedBid.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="flex gap-2 pt-1">
                      <button onClick={() => handleReject(rec.id)} className="flex-1 py-1.5 border border-white/10 rounded text-xs hover:bg-white/5 transition-colors text-gray-300">
                        忽略
                      </button>
                      <button onClick={() => handleApprove(rec.id)} className="flex-1 py-1.5 bg-[var(--color-accent)] text-white rounded text-xs hover:opacity-90 transition-opacity">
                        采纳
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>

          {/* Simulation Launcher */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass rounded-xl border border-white/5 bg-white/5 overflow-hidden backdrop-blur-md"
          >
            <div className="p-4 border-b border-white/5">
              <h2 className="text-base font-medium flex items-center gap-2">
                <Play className="w-4 h-4 text-[#10b981]" />
                沙盒推演
              </h2>
            </div>
            <div className="p-4 space-y-4">
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">推演模式</label>
                  <select 
                    value={simMode}
                    onChange={(e) => setSimMode(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[var(--color-accent)]"
                  >
                    <option value="What-If">What-If (策略变更影响)</option>
                    <option value="Backtest">Backtest (历史数据回测)</option>
                    <option value="Stress Test">Stress Test (预算缩减压测)</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">推演天数</label>
                    <input 
                      type="number" 
                      value={simDays}
                      onChange={(e) => setSimDays(parseInt(e.target.value) || 30)}
                      className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[var(--color-accent)]"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">目标 ACoS (%)</label>
                    <input 
                      type="number" 
                      value={simTargetAcos}
                      onChange={(e) => setSimTargetAcos(parseInt(e.target.value) || 15)}
                      className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[var(--color-accent)]"
                    />
                  </div>
                </div>
              </div>
              
              <button 
                onClick={runSimulation}
                disabled={simRunning}
                className="w-full py-2 bg-[#10b981]/20 border border-[#10b981]/30 text-[#10b981] rounded-lg text-sm font-medium hover:bg-[#10b981]/30 transition-colors disabled:opacity-50"
              >
                {simRunning ? '推演计算中...' : '运行沙盒模拟'}
              </button>

              {simResult && (
                <div className={`p-3 rounded-lg text-sm ${simResult.error ? 'bg-red-500/10 text-red-400' : 'bg-[#10b981]/10 text-[#10b981]'}`}>
                  {simResult.message}
                </div>
              )}
            </div>
          </motion.div>

          {/* Historical Logs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass rounded-xl border border-white/5 bg-white/5 overflow-hidden backdrop-blur-md"
          >
            <div className="p-4 border-b border-white/5">
              <h2 className="text-base font-medium flex items-center gap-2">
                <History className="w-4 h-4 text-gray-400" />
                历史优化记录
              </h2>
            </div>
            <div className="p-4 space-y-3">
              {historyLogs.length === 0 ? (
                <div className="text-center text-sm text-gray-500 py-2">暂无记录</div>
              ) : (
                historyLogs.slice(0, 5).map(log => (
                  <div key={log.id} className="flex flex-col gap-1 text-sm border-b border-white/5 pb-2 last:border-0 last:pb-0">
                    <span className="text-gray-300 font-medium">{log.action}</span>
                    <span className="text-gray-500 text-xs">{log.timestamp} • {log.result}</span>
                  </div>
                ))
              )}
            </div>
          </motion.div>
          
        </div>
      </div>
    </div>
  );
}

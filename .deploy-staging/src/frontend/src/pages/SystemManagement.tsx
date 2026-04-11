import { useState, useEffect } from 'react';
import { 
  Shield, RefreshCw, CheckCircle2, User, Bot, Clock, Key, Settings, Save, AlertCircle
} from 'lucide-react';
import { motion } from 'motion/react';
import api from '../api/client';

interface UserInfo {
  username: string;
  role: string;
}

interface AgentConfig {
  [key: string]: string;
}

interface ApiStatus {
  [key: string]: boolean;
}

interface SystemConfig {
  [key: string]: string;
}

const TABS = [
  { id: 'users', label: '用户管理', icon: User },
  { id: 'agents', label: 'Agent 配置', icon: Bot },
  { id: 'scheduler', label: '计划任务', icon: Clock },
  { id: 'api-keys', label: 'API 密钥状态', icon: Key },
  { id: 'system', label: '系统配置', icon: Settings },
];

export default function SystemManagement() {
  const [activeTab, setActiveTab] = useState('users');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // States
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [agents, setAgents] = useState<AgentConfig>({});
  const [apiStatus, setApiStatus] = useState<ApiStatus>({});
  const [sysConfig, setSysConfig] = useState<SystemConfig>({});

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [uRes, aRes, apiRes, sysRes] = await Promise.all([
        api.get('/system/users'),
        api.get('/system/agent-config'),
        api.get('/system/api-status'),
        api.get('/system/config')
      ]);
      setUsers(uRes.data);
      setAgents(aRes.data);
      setApiStatus(apiRes.data);
      setSysConfig(sysRes.data);
    } catch (err: any) {
      console.error('Error fetching system data', err);
      setError(err?.response?.data?.detail || 'Failed to fetch data. Ensure you have boss privileges.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleUpdateAgentModel = async (agentType: string, newModel: string) => {
    try {
      await api.put(`/system/agent-config/${agentType}`, { model: newModel });
      setAgents(prev => ({ ...prev, [agentType]: newModel }));
    } catch (err) {
      console.error('Failed to update agent model', err);
    }
  };

  const handleUpdateSysConfig = async (key: string, newValue: string) => {
    try {
      await api.put(`/system/config/${key}`, { value: newValue });
      setSysConfig(prev => ({ ...prev, [key]: newValue }));
    } catch (err) {
      console.error('Failed to update system config', err);
    }
  };

  return (
    <div className="p-4 sm:p-8 space-y-8 bg-[#0a0a1a] min-h-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">系统管理</h1>
          <p className="text-gray-400 text-sm mt-1">监控服务器状态及管理系统配置</p>
        </div>
        <button 
          onClick={fetchData}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-2 glass border border-[var(--color-glass-border)] text-gray-200 rounded-xl text-sm font-medium hover:bg-[var(--color-surface)] transition-colors shadow-sm disabled:opacity-50 w-full sm:w-auto"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          刷新状态
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl glass border border-rose-500/30 bg-rose-500/10 text-rose-400 flex items-center gap-3">
          <AlertCircle size={20} />
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex overflow-x-auto custom-scrollbar gap-2 pb-2">
        {TABS.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                isActive 
                  ? 'bg-[var(--color-accent)]/20 text-[#3B82F6] border border-[#3B82F6]/30' 
                  : 'glass border border-[var(--color-glass-border)] text-gray-400 hover:text-gray-200 hover:bg-[var(--color-surface)]'
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content Area */}
      <motion.div 
        key={activeTab}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="glass rounded-2xl border border-[var(--color-glass-border)] overflow-hidden"
      >
        {/* User Management */}
        {activeTab === 'users' && (
          <div>
            <div className="p-6 border-b border-[var(--color-glass-border)] flex items-center gap-3">
              <Shield className="text-[#3B82F6]" size={20} />
              <h3 className="font-bold text-gray-100">用户权限管理 (ENV)</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[var(--color-surface)]">
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">用户名</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">角色权限</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-glass-border)]">
                  {users.length > 0 ? users.map((u) => (
                    <tr key={u.username} className="text-sm hover:bg-[var(--color-surface)] transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-200">{u.username}</td>
                      <td className="px-6 py-4 text-gray-400">
                        <span className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                          u.role === 'boss' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1 text-emerald-400 text-xs font-bold">
                          <CheckCircle2 size={14} /> 正常
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan={3} className="px-6 py-8 text-center text-gray-500 text-sm">暂无数据或无权限</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Agent Config */}
        {activeTab === 'agents' && (
          <div>
            <div className="p-6 border-b border-[var(--color-glass-border)] flex items-center gap-3">
              <Bot className="text-[#3B82F6]" size={20} />
              <h3 className="font-bold text-gray-100">Agent 模型分配配置</h3>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {Object.keys(agents).length > 0 ? Object.entries(agents).map(([agentType, model]) => (
                <div key={agentType} className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-glass-border)] space-y-3">
                  <div className="text-sm font-bold text-gray-200 capitalize truncate" title={agentType}>
                    {agentType.replace(/_/g, ' ')}
                  </div>
                  <div className="flex items-center gap-2">
                    <select 
                      value={model}
                      onChange={(e) => handleUpdateAgentModel(agentType, e.target.value)}
                      className="flex-1 bg-[#0a0a1a] border border-[var(--color-glass-border)] text-gray-300 text-xs rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#3B82F6]"
                    >
                      <option value="gpt-4o">GPT-4o (Reasoning)</option>
                      <option value="gpt-4o-mini">GPT-4o-mini (Fast)</option>
                      <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Writing)</option>
                      <option value="claude-3-haiku-20240307">Claude 3 Haiku (Fast)</option>
                    </select>
                  </div>
                </div>
              )) : (
                <div className="col-span-full py-8 text-center text-gray-500 text-sm">暂无数据或无权限</div>
              )}
            </div>
          </div>
        )}

        {/* Scheduler */}
        {activeTab === 'scheduler' && (
          <div>
            <div className="p-6 border-b border-[var(--color-glass-border)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Clock className="text-[#3B82F6]" size={20} />
                <h3 className="font-bold text-gray-100">计划任务管理 (Mock)</h3>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[var(--color-surface)]">
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">任务名称</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Cron 表达式</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">上次执行</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-glass-border)]">
                  <tr className="text-sm hover:bg-[var(--color-surface)] transition-colors">
                    <td className="px-6 py-4 font-medium text-gray-200">Daily Report Gen</td>
                    <td className="px-6 py-4 text-gray-400 font-mono text-xs">0 8 * * *</td>
                    <td className="px-6 py-4 text-gray-500 text-xs">今天 08:00</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-emerald-400 text-xs font-bold">
                        <CheckCircle2 size={14} /> Active
                      </div>
                    </td>
                  </tr>
                  <tr className="text-sm hover:bg-[var(--color-surface)] transition-colors">
                    <td className="px-6 py-4 font-medium text-gray-200">Data Sync SP-API</td>
                    <td className="px-6 py-4 text-gray-400 font-mono text-xs">0 */4 * * *</td>
                    <td className="px-6 py-4 text-gray-500 text-xs">今天 12:00</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-emerald-400 text-xs font-bold">
                        <CheckCircle2 size={14} /> Active
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* API Keys */}
        {activeTab === 'api-keys' && (
          <div>
            <div className="p-6 border-b border-[var(--color-glass-border)] flex items-center gap-3">
              <Key className="text-[#3B82F6]" size={20} />
              <h3 className="font-bold text-gray-100">API 密钥配置状态</h3>
            </div>
            <div className="p-6">
              <div className="max-w-2xl space-y-3">
                {Object.keys(apiStatus).length > 0 ? Object.entries(apiStatus).map(([name, isConfigured]) => (
                  <div key={name} className="flex items-center justify-between p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-glass-border)]">
                    <span className="font-bold text-gray-200">{name}</span>
                    {isConfigured ? (
                      <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold tracking-wide">
                        <CheckCircle2 size={14} /> 已配置
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-bold tracking-wide">
                        <AlertCircle size={14} /> 未配置
                      </div>
                    )}
                  </div>
                )) : (
                  <div className="py-8 text-center text-gray-500 text-sm">暂无数据或无权限</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* System Config */}
        {activeTab === 'system' && (
          <div>
            <div className="p-6 border-b border-[var(--color-glass-border)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Settings className="text-[#3B82F6]" size={20} />
                <h3 className="font-bold text-gray-100">高级系统配置 (KV Store)</h3>
              </div>
            </div>
            <div className="p-6">
              <div className="max-w-3xl space-y-4">
                {Object.keys(sysConfig).length > 0 ? Object.entries(sysConfig).map(([key, val]) => (
                  <div key={key} className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-glass-border)]">
                    <div className="sm:w-1/3 font-medium text-gray-300 text-sm truncate" title={key}>
                      {key}
                    </div>
                    <div className="flex-1 flex gap-2">
                      <input 
                        type="text" 
                        value={val}
                        onChange={(e) => setSysConfig(prev => ({ ...prev, [key]: e.target.value }))}
                        className="flex-1 bg-[#0a0a1a] border border-[var(--color-glass-border)] text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#3B82F6]"
                      />
                      <button 
                        onClick={() => handleUpdateSysConfig(key, val)}
                        className="p-2 bg-[#3B82F6]/10 text-[#3B82F6] hover:bg-[#3B82F6]/20 border border-[#3B82F6]/30 rounded-lg transition-colors flex-shrink-0"
                        title="保存设置"
                      >
                        <Save size={18} />
                      </button>
                    </div>
                  </div>
                )) : (
                  <div className="py-8 text-center text-gray-500 text-sm">当前无自定义配置，或无权限查看</div>
                )}
              </div>
            </div>
          </div>
        )}

      </motion.div>
    </div>
  );
}

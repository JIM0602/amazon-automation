import React, { useState, useEffect } from 'react';
import { DataTable } from '../../components/DataTable';
import { Column } from '../../types/table';
import api from '../../api/client';
import { Edit2, CheckCircle2, XCircle } from 'lucide-react';

interface AgentConfig {
  agent_type: string;
  display_name_cn: string;
  description?: string;
  is_active: boolean;
  visible_roles: string[];
  sort_order: number;
  provider?: string;
  model?: string;
  [key: string]: unknown;
}

export default function AgentConfigPage() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentConfig | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    display_name_cn: '',
    provider: 'OpenAI',
    model: '',
    is_active: true,
    visible_roles: [] as string[],
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3000);
  };

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const response = await api.get('/agents/config');
      if (response.data) {
        // Assume response.data is the array or response.data.agents
        const data = Array.isArray(response.data) ? response.data : response.data.agents || [];
        // Sort by sort_order
        setAgents(data.sort((a: AgentConfig, b: AgentConfig) => a.sort_order - b.sort_order));
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      showToast('获取Agent配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleEditClick = (agent: AgentConfig) => {
    setSelectedAgent(agent);
    setFormData({
      display_name_cn: agent.display_name_cn || '',
      provider: agent.provider || 'OpenAI',
      model: agent.model || '',
      is_active: agent.is_active ?? true,
      visible_roles: agent.visible_roles || [],
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedAgent(null);
    setFormError('');
  };

  const handleRoleChange = (role: string, checked: boolean) => {
    setFormData((prev) => {
      const newRoles = checked
        ? [...prev.visible_roles, role]
        : prev.visible_roles.filter((r) => r !== role);
      return { ...prev, visible_roles: newRoles };
    });
  };

  const handleSave = async () => {
    if (!selectedAgent) return;
    if (!formData.display_name_cn.trim()) {
      setFormError('中文名不能为空');
      return;
    }

    setSubmitting(true);
    try {
      await api.put(`/agents/config/${selectedAgent.agent_type}`, {
        display_name_cn: formData.display_name_cn,
        provider: formData.provider,
        model: formData.model,
        is_active: formData.is_active,
        visible_roles: formData.visible_roles,
      });
      showToast('保存成功');
      closeModal();
      fetchAgents();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  const columns: Column<AgentConfig>[] = [
    {
      key: 'index',
      title: '序号',
      width: '80px',
      render: (_, __, index) => <span>{index + 1}</span>,
    },
    {
      key: 'display_name_cn',
      title: '中文名',
      render: (val) => <span className="font-medium text-gray-900 dark:text-white">{val as React.ReactNode}</span>,
    },
    {
      key: 'agent_type',
      title: 'Agent类型标识',
      render: (val) => <code className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-sm text-gray-600 dark:text-gray-300">{val as string}</code>,
    },
    {
      key: 'provider',
      title: 'LLM提供商',
      render: (val) => <span>{(val as string) || '-'}</span>,
    },
    {
      key: 'model',
      title: '模型名',
      render: (val) => <span className="text-gray-500 dark:text-gray-400">{(val as string) || '-'}</span>,
    },
    {
      key: 'is_active',
      title: '状态',
      render: (val) => {
        return val ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            启用
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400">
            <XCircle className="w-3 h-3 mr-1" />
            停用
          </span>
        );
      },
    },
    {
      key: 'visible_roles',
      title: '可见角色',
      render: (val) => {
        const roles = val as string[];
        if (!roles || roles.length === 0) return <span className="text-gray-400">-</span>;
        const labels = roles.map(r => r === 'boss' ? 'Boss' : r === 'operator' ? '运营' : r);
        return <span>{labels.join(', ')}</span>;
      },
    },
    {
      key: 'action',
      title: '操作',
      width: '100px',
      align: 'center',
      render: (_, row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleEditClick(row);
          }}
          className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
          title="编辑配置"
        >
          <Edit2 className="w-4 h-4" />
        </button>
      ),
    },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agent配置管理</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Agent中文名和LLM配置可在此修改。系统核心Agent不可新增或删除，仅支持修改现有配置。
        </p>
      </div>

      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
        <DataTable
          columns={columns}
          data={agents}
          rowKey="agent_type"
          loading={loading}
          emptyText="暂无Agent配置"
        />
      </div>

      {/* Toast */}
      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50">
          {toastMsg}
        </div>
      )}

      {/* Edit Modal */}
      {isModalOpen && selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                编辑 Agent - {selectedAgent.agent_type}
              </h3>
            </div>
            
            <div className="p-6 space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-md border border-red-200 dark:border-red-800">
                  {formError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  中文名 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.display_name_cn}
                  onChange={(e) => setFormData({ ...formData, display_name_cn: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                  placeholder="例如：AI主管"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  LLM提供商
                </label>
                <select
                  value={formData.provider}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                >
                  <option value="OpenAI">OpenAI</option>
                  <option value="OpenRouter">OpenRouter</option>
                  <option value="Anthropic">Anthropic</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  模型名
                </label>
                <input
                  type="text"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                  placeholder="例如：gpt-4o"
                />
              </div>

              <div className="flex items-center">
                <input
                  id="is_active"
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
                />
                <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900 dark:text-gray-300">
                  启用该Agent
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  可见角色
                </label>
                <div className="flex gap-4">
                  <label className="inline-flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.visible_roles.includes('boss')}
                      onChange={(e) => handleRoleChange('boss', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Boss</span>
                  </label>
                  <label className="inline-flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.visible_roles.includes('operator')}
                      onChange={(e) => handleRoleChange('operator', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">运营</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeModal}
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white dark:bg-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                取消
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={submitting}
                className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect } from 'react';
import { DataTable } from '../components/DataTable';
import { Pagination } from '../components/Pagination';
import { Column } from '../types/table';
import api from '../api/client';
import { formatSiteTime } from '../utils/timezone';
import { Check, X, Clock, AlertCircle } from 'lucide-react';

interface ApprovalItem {
  id: string;
  agent_type: string;
  action_description: string;
  requested_at: string;
  status: string;
  duration_seconds: number | null;
  llm_cost: number | null;
  result_summary: string | null;
  [key: string]: unknown;
}

const agentNameMap: Record<string, string> = {
  core_management: 'AI主管',
  keyword_library: '关键词Agent',
  selection: '选品Agent',
  listing: 'Listing Agent',
  competitor: '竞品分析Agent',
  inventory: '库存Agent',
  whitepaper: '白皮书Agent',
  persona: '买家Persona',
  image_generation: '图片生成Agent',
  product_listing: '商品发布Agent',
  ad_monitor: '广告监控Agent',
  auditor: '审计Agent',
  post_service: '售后Agent',
};

const getStatusBadge = (status: string) => {
  switch (status?.toLowerCase()) {
    case 'success':
    case 'approved':
      return <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300">成功</span>;
    case 'failed':
    case 'rejected':
      return <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300">失败</span>;
    case 'running':
    case 'in_progress':
      return <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">进行中</span>;
    case 'pending':
      return <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300">待审批</span>;
    default:
      return <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">{status}</span>;
  }
};

export default function ApprovalsPage() {
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending');
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3000);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (activeTab === 'pending') {
        params.append('status', 'pending');
      } else {
        params.append('status', 'all');
      }

      const response = await api.get(`/approvals?${params.toString()}`);
      if (response.data) {
        setItems(response.data.approvals || response.data.items || []);
        setTotal(response.data.total ?? response.data.total_count ?? 0);
      }
    } catch (error) {
      showToast('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1); // Reset page on tab change
  }, [activeTab]);

  useEffect(() => {
    fetchData();
  }, [activeTab, page, pageSize]);

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    try {
      await api.post(`/approvals/${id}/${action}`);
      showToast(action === 'approve' ? '已通过' : '已拒绝');
      fetchData();
    } catch (err) {
      showToast('操作失败，请重试');
    }
  };

  const columns: Column<ApprovalItem>[] = [
    {
      key: 'requested_at',
      title: '运行时间',
      render: (val) => val ? formatSiteTime(new Date(val as string)) : '-',
    },
    {
      key: 'agent_type',
      title: 'Agent名称',
      render: (val) => agentNameMap[val as string] || (val as string),
    },
    {
      key: 'status',
      title: '运行状态',
      render: (val) => getStatusBadge(val as string),
    },
    {
      key: 'duration_seconds',
      title: '耗时',
      render: (val) => val != null ? `${val}s` : '-',
    },
    {
      key: 'llm_cost',
      title: 'LLM花费',
      render: (val) => val != null ? `$${Number(val).toFixed(3)}` : '-',
    },
    {
      key: 'result_summary',
      title: '结果摘要',
      render: (val, row) => {
        const summary = val as string;
        if (!summary) return '-';
        const isExpanded = !!expandedRows[row.id as string];
        if (summary.length <= 30) return summary;

        return (
          <div className="max-w-xs md:max-w-sm lg:max-w-md break-words whitespace-normal">
            {isExpanded ? summary : `${summary.substring(0, 30)}...`}
            <button 
              className="ml-2 text-blue-600 dark:text-blue-400 hover:underline text-xs"
              onClick={() => setExpandedRows(prev => ({ ...prev, [row.id as string]: !isExpanded }))}
            >
              {isExpanded ? '收起' : '展开'}
            </button>
          </div>
        );
      }
    }
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">审批中心</h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('pending')}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
              ${activeTab === 'pending' 
                ? 'border-blue-500 text-blue-600 dark:text-blue-400' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }
            `}
          >
            待审批
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
              ${activeTab === 'history'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }
            `}
          >
            Agent任务历史
          </button>
        </nav>
      </div>

      {/* Content */}
      <div className="min-h-[400px]">
        {activeTab === 'pending' ? (
          <div>
            {loading ? (
              <div className="flex justify-center py-12 text-gray-500 dark:text-gray-400">加载中...</div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-100 dark:border-gray-700">
                <AlertCircle className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-lg">暂无待审批事项</p>
              </div>
            ) : (
              <div className="space-y-4">
                {items.map(item => (
                  <div key={item.id as string} className="flex flex-col sm:flex-row justify-between p-5 bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-100 dark:border-gray-700 items-start sm:items-center gap-4 transition-all hover:shadow-md">
                    <div className="flex flex-col space-y-2 flex-1">
                      <div className="flex items-center space-x-3">
                        <span className="font-semibold text-lg text-gray-900 dark:text-white">
                          {agentNameMap[item.agent_type as string] || item.agent_type}
                        </span>
                        {getStatusBadge(item.status as string)}
                        <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center">
                          <Clock className="h-4 w-4 mr-1" />
                          {item.requested_at ? formatSiteTime(new Date(item.requested_at as string)) : '-'}
                        </span>
                      </div>
                      <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                        {item.action_description}
                      </p>
                    </div>
                    <div className="flex items-center space-x-3 sm:ml-4 shrink-0">
                      <button 
                        onClick={() => handleAction(item.id as string, 'approve')}
                        className="flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors"
                      >
                        <Check className="h-4 w-4 mr-1" />
                        通过
                      </button>
                      <button 
                        onClick={() => handleAction(item.id as string, 'reject')}
                        className="flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium transition-colors"
                      >
                        <X className="h-4 w-4 mr-1" />
                        拒绝
                      </button>
                    </div>
                  </div>
                ))}
                {total > 0 && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-100 dark:border-gray-700">
                    <Pagination
                      current={page}
                      pageSize={pageSize}
                      total={total}
                      onChange={(p, s) => {
                        setPage(p);
                        setPageSize(s);
                      }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-100 dark:border-gray-700">
            <DataTable
              columns={columns}
              data={items}
              loading={loading}
              rowKey="id"
              pagination={{
                current: page,
                pageSize: pageSize,
                total: total,
                onChange: (p, s) => {
                  setPage(p);
                  setPageSize(s);
                }
              }}
            />
          </div>
        )}
      </div>

      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50 transition-opacity">
          {toastMsg}
        </div>
      )}
    </div>
  );
}

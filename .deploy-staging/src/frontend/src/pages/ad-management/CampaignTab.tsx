import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';
import api from '../../api/client';

interface CampaignData {
  id: string;
  name: string;
  status: string;
  portfolio_id: string;
  portfolio_name: string;
  ad_type: string;
  daily_budget: number;
  budget_remaining: number;
  bidding_strategy: string;
  impressions: number;
  clicks: number;
  ctr: number;
  ad_spend: number;
  cpc: number;
  ad_orders: number;
  cvr: number;
  acos: number;
  start_date: string;
  [key: string]: unknown;
}

const StatusBadge = ({ status }: { status: string }) => {
  const colors: Record<string, string> = {
    'enabled': 'bg-green-500/20 text-green-400',
    'paused': 'bg-yellow-500/20 text-yellow-400',
    'archived': 'bg-gray-500/20 text-gray-400',
  };
  const labels: Record<string, string> = {
    'enabled': '启用',
    'paused': '暂停',
    'archived': '已归档',
  };
  const colorClass = colors[status] || 'bg-gray-500/20 text-gray-400';
  const label = labels[status] || status;
  return <span className={`px-2 py-0.5 rounded text-xs ${colorClass}`}>{label}</span>;
};

const AdTypeBadge = ({ type }: { type: string }) => {
  const colors: Record<string, string> = {
    'SP': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    'SB': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    'SD': 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  };
  const colorClass = colors[type] || 'bg-gray-500/20 text-gray-400 border border-gray-500/30';
  return <span className={`px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>{type}</span>;
};

const ToggleSwitch = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => {
  return (
    <button
      type="button"
      className={`${
        checked ? 'bg-blue-500' : 'bg-gray-200 dark:bg-gray-700'
      } relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none`}
      onClick={(e) => {
        e.stopPropagation();
        onChange();
      }}
    >
      <span
        aria-hidden="true"
        className={`${
          checked ? 'translate-x-4' : 'translate-x-0'
        } pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}
      />
    </button>
  );
};

export default function CampaignTab({ portfolioIds, adType, page, pageSize, onPageChange }: TabProps) {
  const navigate = useNavigate();
  const [data, setData] = useState<CampaignData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<CampaignData>>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = {
          page,
          page_size: pageSize,
          ad_type: adType,
        };
        if (portfolioIds && portfolioIds.length > 0) {
          params.portfolio_id = portfolioIds[0];
        }
        
        const response = await api.get('/ads/campaigns', { params });
        const result = response.data;
        
        setData(result.items || []);
        setTotal(result.total_count || 0);
        if (result.summary_row) {
          setSummaryRow(result.summary_row);
        }
      } catch (error) {
        console.warn('Error fetching campaigns:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [page, pageSize, portfolioIds, adType]);

  const formatNumber = (num: number) => num?.toLocaleString('en-US') ?? '0';
  const formatCurrency = (num: number) => `$${(num ?? 0).toFixed(2)}`;
  const formatPercent = (num: number) => `${((num ?? 0) * 100).toFixed(2)}%`;

  const columns: Column<CampaignData>[] = [
    {
      key: 'shop',
      title: '店铺',
      render: () => 'siqiangshangwu'
    },
    {
      key: 'name',
      title: '广告活动',
      render: (_, row) => (
        <span 
          className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer font-medium"
          onClick={() => navigate('/ads/management/campaign/' + row.id)}
        >
          {row.name}
        </span>
      )
    },
    {
      key: 'active',
      title: '有效',
      render: (_, row) => (
        <ToggleSwitch 
          checked={row.status === 'enabled'} 
          onChange={() => alert('Mock数据模式不可用')} 
        />
      )
    },
    {
      key: 'status',
      title: '服务状态',
      render: (_, row) => <StatusBadge status={row.status} />
    },
    {
      key: 'portfolio_name',
      title: '广告组合',
      render: (_, row) => row.portfolio_name || '-'
    },
    {
      key: 'ad_type',
      title: '广告类型',
      render: (_, row) => <AdTypeBadge type={row.ad_type} />
    },
    {
      key: 'daily_budget',
      title: '每日预算',
      render: (_, row) => formatCurrency(row.daily_budget)
    },
    {
      key: 'budget_remaining',
      title: '预算剩余',
      render: (_, row) => formatCurrency(row.budget_remaining)
    },
    {
      key: 'bidding_strategy',
      title: '竞价策略',
      render: (_, row) => {
        const strategyMap: Record<string, string> = {
          'fixed': '固定竞价',
          'dynamic_down': '动态竞价-降低',
          'dynamic_up_down': '动态竞价-上下'
        };
        return strategyMap[row.bidding_strategy] || row.bidding_strategy || '-';
      }
    },
    {
      key: 'impressions',
      title: '广告曝光量',
      render: (_, row) => formatNumber(row.impressions)
    },
    {
      key: 'clicks',
      title: '广告点击量',
      render: (_, row) => formatNumber(row.clicks)
    },
    {
      key: 'ctr',
      title: '广告点击率',
      render: (_, row) => formatPercent(row.ctr)
    },
    {
      key: 'ad_spend',
      title: '广告花费',
      render: (_, row) => formatCurrency(row.ad_spend)
    },
    {
      key: 'cpc',
      title: 'CPC',
      render: (_, row) => formatCurrency(row.cpc)
    },
    {
      key: 'ad_orders',
      title: '广告订单量',
      render: (_, row) => formatNumber(row.ad_orders)
    },
    {
      key: 'cvr',
      title: '广告转化率',
      render: (_, row) => formatPercent(row.cvr)
    },
    {
      key: 'acos',
      title: 'ACoS',
      render: (_, row) => formatPercent(row.acos)
    },
    {
      key: 'start_date',
      title: '开始日期',
      render: (_, row) => row.start_date || '-'
    },
    {
      key: 'actions',
      title: '操作',
      render: (_, row) => (
        <button 
          onClick={() => navigate('/ads/management/campaign/' + row.id)}
          className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
        >
          查看
        </button>
      )
    }
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <DataTable
        columns={columns}
        data={data}
        rowKey="id"
        loading={loading}
        summaryRow={summaryRow}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: onPageChange,
        }}
      />
    </div>
  );
}

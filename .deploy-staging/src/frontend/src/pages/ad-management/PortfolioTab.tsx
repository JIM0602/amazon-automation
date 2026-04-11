import { useState, useEffect } from 'react';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';
import api from '../../api/client';

interface PortfolioData {
  id: string;
  name: string;
  status: string;
  budget: number;
  budget_type: string;
  start_date: string;
  end_date: string | null;
  campaign_count: number;
  impressions: number;
  clicks: number;
  ctr: number;
  ad_spend: number;
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

export default function PortfolioTab({ portfolioIds, page, pageSize, onPageChange }: TabProps) {
  const [data, setData] = useState<PortfolioData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<PortfolioData>>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = {
          page,
          page_size: pageSize,
        };
        if (portfolioIds && portfolioIds.length > 0) {
          params.portfolio_ids = portfolioIds.join(',');
        }
        
        const response = await api.get('/ads/portfolios', { params });
        const result = response.data;
        
        setData(result.items || []);
        setTotal(result.total_count || 0);
        if (result.summary_row) {
          setSummaryRow(result.summary_row);
        }
      } catch (error) {
        console.warn('Error fetching portfolios:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [page, pageSize, portfolioIds]);

  const formatNumber = (num: number) => num?.toLocaleString('en-US') ?? '0';
  const formatCurrency = (num: number) => `$${(num ?? 0).toFixed(2)}`;
  const formatPercent = (num: number) => `${((num ?? 0) * 100).toFixed(2)}%`;

  const columns: Column<PortfolioData>[] = [
    {
      key: 'shop',
      title: '店铺',
      render: () => 'siqiangshangwu'
    },
    {
      key: 'name',
      title: '广告组合',
      render: (_, row) => <span className="font-medium">{row.name}</span>
    },
    {
      key: 'status',
      title: '服务状态',
      render: (_, row) => <StatusBadge status={row.status} />
    },
    {
      key: 'budget',
      title: '预算',
      render: (_, row) => formatCurrency(row.budget)
    },
    {
      key: 'budget_type',
      title: '预算上限类型',
      render: (_, row) => {
        const typeMap: Record<string, string> = { 'daily': '每日', 'monthly': '每月' };
        return typeMap[row.budget_type] || row.budget_type;
      }
    },
    {
      key: 'start_date',
      title: '预算开始日期',
      render: (_, row) => row.start_date || '-'
    },
    {
      key: 'end_date',
      title: '预算结束日期',
      render: (_, row) => row.end_date || '-'
    },
    {
      key: 'campaign_count',
      title: '广告活动数量',
      render: (_, row) => formatNumber(row.campaign_count)
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
      key: 'actions',
      title: '操作',
      render: () => (
        <button 
          onClick={() => alert('Mock数据模式不可用')}
          className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
        >
          编辑
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

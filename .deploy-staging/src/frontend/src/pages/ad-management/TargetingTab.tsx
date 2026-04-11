import { useState, useEffect } from 'react';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';
import api from '../../api/client';

interface TargetingData {
  id: string;
  store: string;
  keyword: string;
  is_active: boolean;
  service_status: string;
  match_type: string;
  ad_group_name: string;
  campaign_name: string;
  portfolio_name: string;
  bid: number;
  suggested_bid: number;
  [key: string]: unknown;
}

const ToggleSwitch = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => (
  <label className="relative inline-flex items-center cursor-pointer" onClick={(e) => { e.stopPropagation(); onChange(); }}>
    <input type="checkbox" className="sr-only peer" checked={checked} readOnly />
    <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-blue-500"></div>
  </label>
);

const MatchTypeBadge = ({ type }: { type: string }) => {
  const colors: Record<string, string> = {
    '精确': 'bg-red-500/20 text-red-400 border border-red-500/30',
    '词组': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    '广泛': 'bg-green-500/20 text-green-400 border border-green-500/30',
  };
  const colorClass = colors[type] || 'bg-gray-500/20 text-gray-400 border border-gray-500/30';
  return <span className={`px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>{type}</span>;
};

export default function TargetingTab({ portfolioIds, adType, timeRange, searchQuery, page, pageSize, onPageChange }: TabProps) {
  const [data, setData] = useState<TargetingData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<TargetingData>>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = {
          page,
          page_size: pageSize,
          ad_type: adType,
          time_range: timeRange,
          search: searchQuery,
        };
        if (portfolioIds && portfolioIds.length > 0) {
          params.portfolio_ids = portfolioIds.join(',');
        }
        
        const response = await api.get('/ads/targeting', { params });
        const result = response.data;
        
        setData(result.items || []);
        setTotal(result.total_count || 0);
        if (result.summary_row) {
          setSummaryRow(result.summary_row);
        }
      } catch (error) {
        // Ignored in output as instructed
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [page, pageSize, portfolioIds, adType, timeRange, searchQuery]);

  const formatCurrency = (num: number | undefined) => `$${(num ?? 0).toFixed(2)}`;

  const columns: Column<TargetingData>[] = [
    {
      key: 'store',
      title: '店铺',
      render: (_, row) => row.store || '-'
    },
    {
      key: 'keyword',
      title: '关键词',
      render: (_, row) => <span className="font-medium">{row.keyword || '-'}</span>
    },
    {
      key: 'is_active',
      title: '有效',
      render: (_, row) => (
        <ToggleSwitch 
          checked={row.is_active} 
          onChange={() => alert('Mock数据模式，操作不可用')} 
        />
      )
    },
    {
      key: 'service_status',
      title: '服务状态',
      render: (_, row) => row.service_status || '-'
    },
    {
      key: 'match_type',
      title: '匹配类型',
      render: (_, row) => <MatchTypeBadge type={row.match_type || '-'} />
    },
    {
      key: 'ad_group_name',
      title: '广告组',
      render: (_, row) => row.ad_group_name || '-'
    },
    {
      key: 'campaign_name',
      title: '广告活动',
      render: (_, row) => row.campaign_name || '-'
    },
    {
      key: 'portfolio_name',
      title: '广告组合',
      render: (_, row) => row.portfolio_name || '-'
    },
    {
      key: 'bid',
      title: '竞价',
      render: (_, row) => formatCurrency(row.bid)
    },
    {
      key: 'suggested_bid',
      title: '建议竞价',
      render: (_, row) => formatCurrency(row.suggested_bid)
    },
    {
      key: 'actions',
      title: '操作',
      render: () => (
        <button 
          onClick={() => alert('Mock数据模式，操作不可用')}
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
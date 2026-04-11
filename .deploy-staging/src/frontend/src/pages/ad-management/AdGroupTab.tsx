import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';

interface AdGroupData {
  id: string;
  store: string;
  ad_group_name: string;
  is_active: boolean;
  ad_product_count: number;
  service_status: string;
  campaign_name: string;
  portfolio_name: string;
  default_bid: number;
  tags: string;
  creator: string;
  impressions: number;
  [key: string]: unknown;
}

const ToggleSwitch = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => {
  return (
    <label className="relative inline-flex items-center cursor-pointer" onClick={(e) => { e.stopPropagation(); onChange(); }}>
      <input type="checkbox" className="sr-only peer" checked={checked} readOnly />
      <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-blue-500"></div>
    </label>
  );
};

export default function AdGroupTab({ portfolioIds, adType, timeRange, page, pageSize, onPageChange }: TabProps) {
  const navigate = useNavigate();
  const [data, setData] = useState<AdGroupData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<AdGroupData>>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const queryParams = new URLSearchParams({
          page: page.toString(),
          page_size: pageSize.toString(),
          ad_type: adType,
        });

        if (portfolioIds && portfolioIds.length > 0) {
          queryParams.append('portfolio_id', portfolioIds[0]);
        }
        if (timeRange) {
          queryParams.append('time_range', timeRange);
        }

        const response = await fetch(`/api/ads/ad_groups?${queryParams.toString()}`, {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        const result = await response.json();
        
        setData(result.items || []);
        setTotal(result.total_count || 0);
        if (result.summary_row) {
          setSummaryRow(result.summary_row);
        }
      } catch (error) {
        // Silently handle error or you can alert
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [page, pageSize, portfolioIds, adType, timeRange]);

  const formatNumber = (num: number) => num?.toLocaleString('en-US') ?? '0';
  const formatCurrency = (num: number) => `$${(num ?? 0).toFixed(2)}`;

  const columns: Column<AdGroupData>[] = [
    {
      key: 'store',
      title: '店铺',
      render: (_, row) => row.store || 'siqiangshangwu'
    },
    {
      key: 'ad_group_name',
      title: '广告组',
      render: (_, row) => (
        <span 
          className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer font-medium underline"
          onClick={() => navigate('/ads/management/ad-group/' + row.id)}
        >
          {row.ad_group_name}
        </span>
      )
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
      key: 'ad_product_count',
      title: '广告产品数',
      render: (_, row) => formatNumber(row.ad_product_count)
    },
    {
      key: 'service_status',
      title: '服务状态',
      render: (_, row) => row.service_status || '-'
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
      key: 'default_bid',
      title: '默认竞价',
      render: (_, row) => formatCurrency(row.default_bid)
    },
    {
      key: 'tags',
      title: '标签',
      render: (_, row) => row.tags || '-'
    },
    {
      key: 'creator',
      title: '创建人',
      render: (_, row) => row.creator || '-'
    },
    {
      key: 'impressions',
      title: '广告曝光量',
      render: (_, row) => formatNumber(row.impressions)
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

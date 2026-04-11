import { useState, useEffect } from 'react';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';
import api from '../../api/client';

interface NegativeTargetingData {
  id: string;
  store: string;
  negative_keyword: string;
  status: string;
  match_type: string;
  ad_group_name: string;
  campaign_name: string;
  portfolio_name: string;
  creator: string;
  impressions: number;
  clicks: number;
  ad_spend: number;
  ad_orders: number;
  ad_sales: number;
  [key: string]: unknown;
}

export default function NegativeTargetingTab({ portfolioIds, adType, timeRange, searchQuery, page, pageSize, onPageChange }: TabProps) {
  const [data, setData] = useState<NegativeTargetingData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<NegativeTargetingData>>();
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
        
        const response = await api.get('/ads/negative_targeting', { params });
        const result = response.data;
        
        setData(result.items || []);
        setTotal(result.total_count || 0);
        if (result.summary_row) {
          setSummaryRow(result.summary_row);
        }
      } catch (error) {
        // Ignored
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [page, pageSize, portfolioIds, adType, timeRange, searchQuery]);

  const formatCurrency = (num: number | undefined) => `$${(num ?? 0).toFixed(2)}`;
  const formatNumber = (num: number | undefined) => num?.toLocaleString('en-US') ?? '0';

  const columns: Column<NegativeTargetingData>[] = [
    {
      key: 'store',
      title: '店铺',
      render: (_, row) => row.store || '-'
    },
    {
      key: 'negative_keyword',
      title: '否定关键词',
      render: (_, row) => row.negative_keyword || '-'
    },
    {
      key: 'status',
      title: '否定状态',
      render: (_, row) => row.status || '-'
    },
    {
      key: 'match_type',
      title: '匹配类型',
      render: (_, row) => row.match_type || '-'
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
      key: 'clicks',
      title: '广告点击量',
      render: (_, row) => formatNumber(row.clicks)
    },
    {
      key: 'ad_spend',
      title: '广告花费',
      render: (_, row) => formatCurrency(row.ad_spend)
    },
    {
      key: 'ad_orders',
      title: '广告订单量',
      render: (_, row) => formatNumber(row.ad_orders)
    },
    {
      key: 'ad_sales',
      title: '广告销售',
      render: (_, row) => formatCurrency(row.ad_sales)
    },
    {
      key: 'actions',
      title: '操作',
      render: () => (
        <button 
          onClick={() => alert('Mock数据模式，操作不可用')}
          className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 transition-colors"
        >
          删除
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
import { useState, useEffect } from 'react';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';
import api from '../../api/client';

interface AdLogData {
  id: string;
  store: string;
  operation_time: string;
  operation_time_beijing: string;
  portfolio_name: string;
  ad_type: string;
  campaign_name: string;
  ad_group_name: string;
  target_object: string;
  object_detail: string;
  operation_type: string;
  operation_content: string;
  [key: string]: unknown;
}

const AdTypeBadge = ({ type }: { type: string }) => {
  const colors: Record<string, string> = {
    'SP': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    'SB': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    'SD': 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  };
  const colorClass = colors[type] || 'bg-gray-500/20 text-gray-400 border border-gray-500/30';
  return <span className={`px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>{type || '-'}</span>;
};

export default function AdLogTab({ portfolioIds, adType, timeRange, searchQuery, page, pageSize, onPageChange }: TabProps) {
  const [data, setData] = useState<AdLogData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<AdLogData>>();
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
        
        const response = await api.get('/ads/logs', { params });
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

  const columns: Column<AdLogData>[] = [
    {
      key: 'store',
      title: '店铺',
      render: (_, row) => row.store || '-'
    },
    {
      key: 'operation_time',
      title: '操作时间',
      render: (_, row) => (
        <div className="flex flex-col whitespace-nowrap">
          <span>{row.operation_time || '-'}</span>
          {row.operation_time_beijing && (
            <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              (北京：{row.operation_time_beijing})
            </span>
          )}
        </div>
      )
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
      key: 'campaign_name',
      title: '广告活动',
      render: (_, row) => row.campaign_name || '-'
    },
    {
      key: 'ad_group_name',
      title: '广告组',
      render: (_, row) => row.ad_group_name || '-'
    },
    {
      key: 'target_object',
      title: '操作对象',
      render: (_, row) => row.target_object || '-'
    },
    {
      key: 'object_detail',
      title: '对象详情',
      render: (_, row) => (
        <div className="max-w-[200px] truncate" title={row.object_detail}>
          {row.object_detail || '-'}
        </div>
      )
    },
    {
      key: 'operation_type',
      title: '操作类型',
      render: (_, row) => row.operation_type || '-'
    },
    {
      key: 'operation_content',
      title: '操作内容',
      render: (_, row) => (
        <div className="max-w-[300px] break-words" title={row.operation_content}>
          {row.operation_content || '-'}
        </div>
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
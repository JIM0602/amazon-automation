import { useState, useEffect } from 'react';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';
import api from '../../api/client';

interface SearchTermData {
  id: string;
  store: string;
  search_term: string;
  targeting: string;
  match_type: string;
  suggested_bid: number;
  suggested_bid_range: string;
  source_bid: number;
  aba_rank: number;
  rank_weekly_change: number;
  ad_group_name: string;
  campaign_name: string;
  [key: string]: unknown;
}

const TrendChange = ({ percent }: { percent: number }) => {
  if (percent === 0 || !percent) {
    return <span>-</span>;
  }
  const isPositive = percent > 0;
  const color = isPositive ? 'text-green-500' : 'text-red-500';
  const arrow = isPositive ? '↑' : '↓';
  return (
    <span className={color}>
      {arrow} {Math.abs(percent)}%
    </span>
  );
};

export default function SearchTermTab({ portfolioIds, adType, timeRange, searchQuery, page, pageSize, onPageChange }: TabProps) {
  const [data, setData] = useState<SearchTermData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<SearchTermData>>();
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
        
        const response = await api.get('/ads/search_terms', { params });
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

  const columns: Column<SearchTermData>[] = [
    {
      key: 'store',
      title: '店铺',
      render: (_, row) => row.store || '-'
    },
    {
      key: 'search_term',
      title: '用户搜索词',
      render: (_, row) => <span className="font-bold">{row.search_term || '-'}</span>
    },
    {
      key: 'targeting',
      title: '投放',
      render: (_, row) => row.targeting || '-'
    },
    {
      key: 'match_type',
      title: '匹配类型',
      render: (_, row) => row.match_type || '-'
    },
    {
      key: 'suggested_bid',
      title: '建议竞价/范围',
      render: (_, row) => {
        const bidStr = formatCurrency(row.suggested_bid);
        if (row.suggested_bid_range) {
          return `${bidStr} / ${row.suggested_bid_range}`;
        }
        return bidStr;
      }
    },
    {
      key: 'source_bid',
      title: '源竞价',
      render: (_, row) => formatCurrency(row.source_bid)
    },
    {
      key: 'aba_rank',
      title: 'ABA搜索词排名',
      render: (_, row) => row.aba_rank?.toLocaleString('en-US') || '-'
    },
    {
      key: 'rank_weekly_change',
      title: '排名周变化率',
      render: (_, row) => <TrendChange percent={row.rank_weekly_change} />
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
      key: 'actions',
      title: '操作',
      render: () => (
        <button 
          onClick={() => alert('Mock数据模式，操作不可用')}
          className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
        >
          添加为否定
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
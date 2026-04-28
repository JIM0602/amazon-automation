import { useState, useEffect } from 'react';
import type { TabProps } from './TabContent';
import { DataTable } from '../../components/DataTable';
import type { Column } from '../../types/table';

interface AdProductData {
  id: string;
  store: string;
  product_image: string;
  asin: string;
  product_title: string;
  is_active: boolean;
  service_status: string;
  fba_available: number;
  price: number;
  rating_count: number;
  star_rating: number;
  ad_group_name: string;
  campaign_name: string;
  portfolio_name: string;
  tags: string;
  salesperson: string;
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

export default function AdProductTab({ portfolioIds, adType, timeRange, page, pageSize, onPageChange }: TabProps) {
  const [data, setData] = useState<AdProductData[]>([]);
  const [total, setTotal] = useState(0);
  const [summaryRow, setSummaryRow] = useState<Partial<AdProductData>>();
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

        const response = await fetch(`/api/ads/ad_products?${queryParams.toString()}`, {
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

  const renderStars = (rating: number) => {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
      if (rating >= i) {
        stars.push(<span key={i} className="text-yellow-400">★</span>);
      } else if (rating >= i - 0.5) {
        stars.push(<span key={i} className="text-yellow-400">★</span>);
      } else {
        stars.push(<span key={i} className="text-gray-300 dark:text-gray-600">☆</span>);
      }
    }
    return <div className="flex text-sm items-center">{stars} <span className="ml-1 text-xs text-gray-500">{rating}</span></div>;
  };

  const columns: Column<AdProductData>[] = [
    {
      key: 'store',
      title: '店铺',
      render: (_, row) => row.store || 'siqiangshangwu'
    },
    {
      key: 'product_info',
      title: '产品信息',
      render: (_, row) => (
        <div className="flex items-center space-x-3 w-[250px]">
          <div className="flex-shrink-0 w-[50px] h-[50px] bg-gray-100 rounded overflow-hidden">
            {row.product_image ? (
              <img src={row.product_image} alt={row.product_title} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">无图</div>
            )}
          </div>
          <div className="flex flex-col flex-1 min-w-0">
            <span className="text-xs text-blue-500 font-medium">{row.asin}</span>
            <span className="text-xs text-gray-700 dark:text-gray-300 truncate" title={row.product_title}>
              {row.product_title || '-'}
            </span>
          </div>
        </div>
      )
    },
    {
      key: 'is_active',
      title: '有效',
      render: (_, row) => (
        <ToggleSwitch 
          checked={row.is_active} 
          onChange={() => alert('请使用广告管理主表中的操作按钮')}
        />
      )
    },
    {
      key: 'service_status',
      title: '服务状态',
      render: (_, row) => row.service_status || '-'
    },
    {
      key: 'fba_available',
      title: 'FBA可售',
      render: (_, row) => formatNumber(row.fba_available)
    },
    {
      key: 'price',
      title: '价格',
      render: (_, row) => formatCurrency(row.price)
    },
    {
      key: 'rating_count',
      title: '评分数',
      render: (_, row) => formatNumber(row.rating_count)
    },
    {
      key: 'star_rating',
      title: '星级',
      render: (_, row) => renderStars(row.star_rating || 0)
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
      key: 'tags',
      title: '标签',
      render: (_, row) => row.tags || '-'
    },
    {
      key: 'salesperson',
      title: '业务员',
      render: (_, row) => row.salesperson || '-'
    },
    {
      key: 'actions',
      title: '操作',
      render: () => (
        <button 
          onClick={() => alert('请使用广告管理主表中的操作按钮')}
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

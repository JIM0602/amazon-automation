import { useState, useEffect } from 'react';
import { DataTable } from '../components/DataTable';
import { Column } from '../types/table';
import api from '../api/client';
import { formatSiteTime } from '../utils/timezone';
import { Search, Calendar, ChevronDown, ChevronUp } from 'lucide-react';

interface ReturnItem {
  order_id: string;
  after_sale_tags: string[];
  return_time: string | null;
  order_time: string | null;
  site_return_time: string | null;
  store: string;
  site: string;
  image_url: string;
  asin: string;
  msku: string;
  product_title: string;
  product_name: string;
  sku: string;
  parent_asin: string;
  buyer_notes: string;
  return_quantity: number;
  warehouse_id: string;
  inventory_property: string;
  return_reason: string;
  status: string;
  lpn_number: string;
  notes: string;
  [key: string]: unknown;
}

interface ReturnSummary {
  total_return_quantity?: number;
  return_quantity?: number;
  [key: string]: unknown;
}

export default function ReturnsPage() {
  const [returns, setReturns] = useState<ReturnItem[]>([]);
  const [summary, setSummary] = useState<ReturnSummary>({});
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [reason, setReason] = useState('');
  const [timeRange, setTimeRange] = useState('');
  const [toastMsg, setToastMsg] = useState('');

  const timeRangeOptions = [
    { value: '', label: '全部时间' },
    { value: 'site_today', label: '站点今天' },
    { value: 'last_24h', label: '最近24小时' },
    { value: 'this_week', label: '本周' },
    { value: 'this_month', label: '本月' },
    { value: 'this_year', label: '本年' },
  ];
  const [expandedNotes, setExpandedNotes] = useState<Record<string, boolean>>({});

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3000);
  };

  const fetchReturns = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (search) params.append('search', search);
      if (status) params.append('status', status);
      if (reason) params.append('reason', reason);
      if (timeRange) params.append('time_range', timeRange);

      const response = await api.get(`/returns?${params.toString()}`);
      if (response.data) {
        setReturns(response.data.items || []);
        setTotal(response.data.total_count || 0);
        
        const summaryData = response.data.summary_row || {};
        setSummary({
          return_quantity: summaryData.total_return_quantity,
          ...summaryData
        });
      }
    } catch (error) {
      showToast('获取退货列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReturns();
  }, [page, pageSize, search, status, reason, timeRange]);

  const handleMockAction = () => {
    showToast('Mock数据模式不可用');
  };

  const toggleNote = (orderId: string) => {
    setExpandedNotes(prev => ({
      ...prev,
      [orderId]: !prev[orderId]
    }));
  };

  const getReasonText = (reasonCode: string) => {
    const reasonMap: Record<string, string> = {
      'DEFECTIVE': '产品缺陷',
      'UNWANTED_ITEM': '不想要了',
      'CUSTOMER_CHANGED_MIND': '买错了',
      'WRONG_ITEM': '发错货',
      'DAMAGED': '包裹破损',
      'OTHER': '其他原因'
    };
    return reasonMap[reasonCode] || reasonCode || '-';
  };

  const getStatusColor = (statusText: string) => {
    switch (statusText?.toLowerCase()) {
      case 'received': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'pending': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'refunded': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'closed': return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const columns: Column<ReturnItem>[] = [
    {
      key: 'order_id',
      title: '订单号',
      render: (val) => <span className="text-blue-600 dark:text-blue-400 font-medium">{val as string}</span>,
    },
    {
      key: 'after_sale_tags',
      title: '售后问题标签',
      render: (val) => {
        const tags = (val as string[]) || [];
        return (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag, idx) => (
              <span key={idx} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300">
                {tag}
              </span>
            ))}
            {tags.length === 0 && '-'}
          </div>
        );
      },
    },
    {
      key: 'return_time',
      title: '退货时间',
      render: (val) => val ? formatSiteTime(new Date(val as string)) : '-',
    },
    {
      key: 'order_time',
      title: '订购时间',
      render: (val) => val ? formatSiteTime(new Date(val as string)) : '-',
    },
    {
      key: 'site_return_time',
      title: '退货站点时间',
      render: (val) => val ? formatSiteTime(new Date(val as string)) : '-',
    },
    {
      key: 'store_site',
      title: '店铺/站点',
      render: (_, row) => (
        <div className="flex flex-col text-xs">
          <span className="font-medium dark:text-white">{row.store || '-'}</span>
          <span className="text-gray-500 dark:text-gray-400">{row.site || '-'}</span>
        </div>
      ),
    },
    {
      key: 'product_info',
      title: '商品信息',
      render: (_, row) => (
        <div className="flex items-center space-x-2 min-w-[180px]">
          {row.image_url ? (
             <img src={row.image_url} alt="product" className="w-10 h-10 rounded object-cover border border-gray-200 dark:border-gray-700" />
          ) : (
             <div className="w-10 h-10 bg-gray-100 dark:bg-gray-800 rounded flex items-center justify-center text-[10px] text-gray-400">No Img</div>
          )}
          <div className="flex flex-col text-xs">
            <span className="font-medium text-gray-900 dark:text-white truncate max-w-[120px]" title={row.product_title}>{row.product_title || '-'}</span>
            <span className="text-gray-500 dark:text-gray-400 truncate max-w-[120px]" title={row.asin}>{row.asin || '-'}</span>
            <span className="text-gray-500 dark:text-gray-400 truncate max-w-[120px]" title={row.msku}>{row.msku || '-'}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'product_name',
      title: '品名/SKU',
      render: (_, row) => (
        <div className="flex flex-col text-xs min-w-[120px]">
          <span className="font-medium text-gray-900 dark:text-white truncate max-w-[150px]" title={row.product_name}>{row.product_name || '-'}</span>
          <span className="text-gray-500 dark:text-gray-400 truncate max-w-[150px]" title={row.sku}>{row.sku || '-'}</span>
        </div>
      ),
    },
    {
      key: 'parent_asin',
      title: '父ASIN',
      render: (val) => (val as string) || '-',
    },
    {
      key: 'buyer_notes',
      title: '买家备注',
      render: (val, row) => {
        const text = (val as string) || '';
        if (!text) return '-';
        const isExpanded = expandedNotes[row.order_id];
        const isLong = text.length > 30;
        
        return (
          <div className="text-xs max-w-[150px]">
            <div className={`text-gray-700 dark:text-gray-300 ${!isExpanded ? 'truncate' : 'break-words'}`} title={text}>
              {text}
            </div>
            {isLong && (
              <button 
                onClick={() => toggleNote(row.order_id)}
                className="mt-1 flex items-center text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-[10px]"
              >
                {isExpanded ? (
                  <><ChevronUp className="w-3 h-3 mr-0.5"/>收起</>
                ) : (
                  <><ChevronDown className="w-3 h-3 mr-0.5"/>展开</>
                )}
              </button>
            )}
          </div>
        );
      },
    },
    {
      key: 'return_quantity',
      title: '退货量',
      render: (val) => val != null ? val as number : '-',
    },
    {
      key: 'warehouse_id',
      title: '发货仓库编号',
      render: (val) => (val as string) || '-',
    },
    {
      key: 'inventory_property',
      title: '库存属性',
      render: (val) => (val as string) || '-',
    },
    {
      key: 'return_reason',
      title: '退货原因',
      render: (val) => getReasonText(val as string),
    },
    {
      key: 'status',
      title: '退货状态',
      render: (val) => (
        <span className={`px-2 py-1 rounded-full text-[10px] font-medium whitespace-nowrap ${getStatusColor(val as string)}`}>
          {val as string || '-'}
        </span>
      ),
    },
    {
      key: 'lpn_number',
      title: 'LPN编号',
      render: (val) => (val as string) || '-',
    },
    {
      key: 'notes',
      title: '备注',
      render: (val) => (val as string) || '-',
    },
    {
      key: 'actions',
      title: '操作',
      render: () => (
        <button 
          onClick={handleMockAction} 
          className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 whitespace-nowrap font-medium"
        >
          查看详情
        </button>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">退货订单</h1>
        <div className="flex items-center space-x-2">
          <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded dark:bg-blue-900 dark:text-blue-300 border border-blue-200 dark:border-blue-800">Mock数据</span>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6 border border-gray-100 dark:border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Calendar className="h-4 w-4 text-gray-400" />
            </div>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="block w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              {timeRangeOptions.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          
          <div className="relative">
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="">全部退货原因</option>
              <option value="DEFECTIVE">产品缺陷</option>
              <option value="UNWANTED_ITEM">不想要了</option>
              <option value="CUSTOMER_CHANGED_MIND">买错了</option>
              <option value="WRONG_ITEM">发错货</option>
              <option value="DAMAGED">包裹破损</option>
              <option value="OTHER">其他原因</option>
            </select>
          </div>

          <div className="relative">
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="">全部状态</option>
              <option value="Pending">Pending (待处理)</option>
              <option value="Received">Received (已收件)</option>
              <option value="Refunded">Refunded (已退款)</option>
              <option value="Closed">Closed (已关闭)</option>
            </select>
          </div>

          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="搜索 订单号 / LPN / ASIN"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-100 dark:border-gray-700">
        <DataTable
          columns={columns}
          data={returns}
          loading={loading}
          rowKey="order_id"
          summaryRow={summary}
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

      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-gray-900/90 text-white px-4 py-2.5 rounded shadow-xl z-50 transition-opacity flex items-center space-x-2 text-sm">
          <span>{toastMsg}</span>
        </div>
      )}
    </div>
  );
}

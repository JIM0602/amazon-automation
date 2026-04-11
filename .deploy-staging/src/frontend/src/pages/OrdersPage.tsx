import { useState, useEffect } from 'react';
import { DataTable } from '../components/DataTable';
import { Column } from '../types/table';
import api from '../api/client';
import { formatSiteTime } from '../utils/timezone';
import { Search, Calendar } from 'lucide-react';

interface OrderItem {
  order_id: string;
  order_time: string;
  payment_time: string | null;
  refund_time: string | null;
  status: string;
  sales_revenue: number;
  image_url: string;
  asin: string;
  msku: string;
  product_name: string;
  sku: string;
  quantity: number;
  refund_quantity: number;
  promo_code: string | null;
  product_amount: number;
  order_profit: number;
  profit_rate: number;
  [key: string]: unknown;
}

interface OrderSummary {
  sales_revenue?: number;
  total_orders?: number;
  [key: string]: unknown;
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [summary, setSummary] = useState<OrderSummary>({});
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [timeRange, setTimeRange] = useState('');
  const [toastMsg, setToastMsg] = useState('');

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3000);
  };

  // Modal state
  const [selectedOrder, setSelectedOrder] = useState<OrderItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (search) params.append('search', search);
      if (status) params.append('status', status);
      if (timeRange) params.append('time_range', timeRange);

      const response = await api.get(`/orders?${params.toString()}`);
      if (response.data) {
        setOrders(response.data.items || []);
        setTotal(response.data.total_count || 0);
        setSummary(response.data.summary_row || {});
      }
    } catch (error) {
      showToast('获取订单列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [page, pageSize, search, status, timeRange]);

  const fetchOrderDetails = async (id: string) => {
    try {
      const response = await api.get(`/orders/${id}`);
      if (response.data) {
        setSelectedOrder(response.data);
        setIsModalOpen(true);
      }
    } catch (error) {
      showToast('获取订单详情失败');
    }
  };

  const handleMockAction = () => {
    showToast('Mock数据模式不可用');
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'shipped': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'pending': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'cancelled': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const columns: Column<OrderItem>[] = [
    {
      key: 'order_id',
      title: '订单号',
      render: (val, row) => (
        <button 
          onClick={() => fetchOrderDetails(row.order_id)}
          className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
        >
          {val as string}
        </button>
      ),
    },
    {
      key: 'order_time',
      title: '订购时间',
      render: (val) => val ? formatSiteTime(new Date(val as string)) : '-',
    },
    {
      key: 'payment_time',
      title: '付款时间',
      render: (val) => val ? formatSiteTime(new Date(val as string)) : '-',
    },
    {
      key: 'refund_time',
      title: '退款时间',
      render: (val) => val ? formatSiteTime(new Date(val as string)) : '-',
    },
    {
      key: 'status',
      title: '订单状态',
      render: (val) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(val as string)}`}>
          {val as string}
        </span>
      ),
    },
    {
      key: 'sales_revenue',
      title: '销售收益',
      render: (val) => val != null ? `$${Number(val).toFixed(2)}` : '-',
    },
    {
      key: 'product_info',
      title: '商品/ASIN/MSKU',
      render: (_, row) => (
        <div className="flex items-center space-x-3 min-w-[200px]">
          {row.image_url ? (
             <img src={row.image_url} alt="product" className="w-10 h-10 rounded object-cover border border-gray-200 dark:border-gray-700" />
          ) : (
             <div className="w-10 h-10 bg-gray-100 dark:bg-gray-800 rounded flex items-center justify-center text-xs text-gray-400">No Img</div>
          )}
          <div className="flex flex-col text-xs">
            <span className="font-medium text-gray-900 dark:text-white truncate max-w-[150px]" title={row.asin}>{row.asin}</span>
            <span className="text-gray-500 dark:text-gray-400 truncate max-w-[150px]" title={row.msku}>{row.msku}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'product_name',
      title: '品名/SKU',
      render: (_, row) => (
        <div className="flex flex-col text-xs min-w-[150px]">
          <span className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]" title={row.product_name}>{row.product_name}</span>
          <span className="text-gray-500 dark:text-gray-400 truncate max-w-[200px]" title={row.sku}>{row.sku}</span>
        </div>
      ),
    },
    {
      key: 'quantity',
      title: '销量',
    },
    {
      key: 'refund_quantity',
      title: '退款量',
    },
    {
      key: 'promo_code',
      title: '促销编码',
      render: (val) => (val as string) || '-',
    },
    {
      key: 'product_amount',
      title: '产品金额',
      render: (val) => val != null ? `$${Number(val).toFixed(2)}` : '-',
    },
    {
      key: 'profit_info',
      title: '订单利润/利润率',
      render: (_, row) => (
        <div className="flex flex-col text-xs">
          <span className={`font-medium ${row.order_profit >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            ${Number(row.order_profit || 0).toFixed(2)}
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            {(Number(row.profit_rate || 0) * 100).toFixed(2)}%
          </span>
        </div>
      ),
    },
    {
      key: 'actions',
      title: '操作',
      render: () => (
        <div className="flex flex-wrap gap-2 min-w-[180px]">
          <button onClick={handleMockAction} className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">录入费用</button>
          <button onClick={handleMockAction} className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">标记跟评</button>
          <button onClick={handleMockAction} className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">上传发票</button>
          <button onClick={handleMockAction} className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">同步订单</button>
          <button onClick={handleMockAction} className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">导入成本</button>
          <button onClick={handleMockAction} className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">联系买家</button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">全部订单</h1>
        <div className="flex items-center space-x-2">
          <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded dark:bg-blue-900 dark:text-blue-300">Mock数据</span>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Calendar className="h-5 w-5 text-gray-400" />
            </div>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="">全部时间</option>
              <option value="today">今天</option>
              <option value="7days">过去7天</option>
              <option value="30days">过去30天</option>
            </select>
          </div>
          
          <div className="relative">
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="">全部状态</option>
              <option value="shipped">已发货</option>
              <option value="pending">待发货</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>

          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="搜索 ASIN / 订单号"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <DataTable
          columns={columns}
          data={orders}
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

      {isModalOpen && selectedOrder && (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={() => setIsModalOpen(false)}></div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              <div className="px-4 pt-5 pb-4 sm:p-6 sm:pb-4 max-h-[80vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-5 border-b pb-4 dark:border-gray-700">
                  <h3 className="text-xl leading-6 font-medium text-gray-900 dark:text-white" id="modal-title">
                    订单详情 - {selectedOrder.order_id}
                  </h3>
                  <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                    <span className="sr-only">Close</span>
                    <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                
                <div className="space-y-6">
                  {/* 基本信息区 */}
                  <div>
                    <h4 className="text-md font-semibold text-gray-800 dark:text-gray-200 mb-3">基本信息</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div><span className="text-gray-500 block">订单号</span><span className="font-medium dark:text-white">{selectedOrder.order_id}</span></div>
                      <div><span className="text-gray-500 block">状态</span><span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(selectedOrder.status)}`}>{selectedOrder.status}</span></div>
                      <div><span className="text-gray-500 block">店铺</span><span className="dark:text-white">{String(selectedOrder.shop_name || 'Mock Store')}</span></div>
                      <div><span className="text-gray-500 block">订购时间</span><span className="dark:text-white">{selectedOrder.order_time ? formatSiteTime(new Date(selectedOrder.order_time)) : '-'}</span></div>
                      <div><span className="text-gray-500 block">发货时间</span><span className="dark:text-white">{String(selectedOrder.ship_time || '-')}</span></div>
                      <div><span className="text-gray-500 block">配送方式</span><span className="dark:text-white">{String(selectedOrder.fulfillment_channel || 'FBA')}</span></div>
                      <div><span className="text-gray-500 block">预计最晚送达</span><span className="dark:text-white">{String(selectedOrder.estimated_delivery || '-')}</span></div>
                      <div><span className="text-gray-500 block">物流商</span><span className="dark:text-white">{String(selectedOrder.carrier || '-')}</span></div>
                      <div><span className="text-gray-500 block">运单号</span><span className="dark:text-white">{String(selectedOrder.tracking_number || '-')}</span></div>
                      <div><span className="text-gray-500 block">买家姓名</span><span className="dark:text-white">{String(selectedOrder.buyer_name || '-')}</span></div>
                      <div><span className="text-gray-500 block">买家邮箱</span><span className="dark:text-white">{String(selectedOrder.buyer_email || '-')}</span></div>
                      <div><span className="text-gray-500 block">税号</span><span className="dark:text-white">{String(selectedOrder.tax_id || '-')}</span></div>
                    </div>
                  </div>

                  {/* 收货信息区 */}
                  <div>
                    <h4 className="text-md font-semibold text-gray-800 dark:text-gray-200 mb-3">收货信息</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm bg-gray-50 dark:bg-gray-900 p-4 rounded-md border border-gray-100 dark:border-gray-700">
                      <div><span className="text-gray-500 block">收件人</span><span className="dark:text-white">{String(selectedOrder.recipient_name || '-')}</span></div>
                      <div><span className="text-gray-500 block">电话</span><span className="dark:text-white">{String(selectedOrder.phone || '-')}</span></div>
                      <div><span className="text-gray-500 block">邮编</span><span className="dark:text-white">{String(selectedOrder.postal_code || '-')}</span></div>
                      <div><span className="text-gray-500 block">收件地区</span><span className="dark:text-white">{String(selectedOrder.country || '')} {String(selectedOrder.state || '')} {String(selectedOrder.city || '')}</span></div>
                      <div className="col-span-2"><span className="text-gray-500 block">收件地址</span><span className="dark:text-white">{String(selectedOrder.address_line1 || '-')} {String(selectedOrder.address_line2 || '')}</span></div>
                      <div><span className="text-gray-500 block">IOSS税号</span><span className="dark:text-white">{String(selectedOrder.ioss_number || '-')}</span></div>
                    </div>
                  </div>

                  {/* 产品信息表格 */}
                  <div>
                    <h4 className="text-md font-semibold text-gray-800 dark:text-gray-200 mb-3">产品信息</h4>
                    <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-md">
                      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800">
                          <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">MSKU / FNSKU</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">ASIN / 产品标题</th>
                            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400">商品折扣</th>
                            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400">产品金额</th>
                            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400">销量</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                          <tr>
                            <td className="px-4 py-3 text-sm dark:text-white">
                              <div>{selectedOrder.msku}</div>
                              <div className="text-gray-500 text-xs">{String(selectedOrder.fnsku || '-')}</div>
                            </td>
                            <td className="px-4 py-3 text-sm dark:text-white">
                              <div>{selectedOrder.asin}</div>
                              <div className="text-gray-500 text-xs truncate max-w-xs">{selectedOrder.product_name}</div>
                            </td>
                            <td className="px-4 py-3 text-sm text-right text-red-500">-${Number(selectedOrder.item_discount || 0).toFixed(2)}</td>
                            <td className="px-4 py-3 text-sm text-right dark:text-white">${Number(selectedOrder.product_amount || 0).toFixed(2)}</td>
                            <td className="px-4 py-3 text-sm text-right dark:text-white">{selectedOrder.quantity}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* 费用明细区 */}
                  <div>
                    <h4 className="text-md font-semibold text-gray-800 dark:text-gray-200 mb-3">费用明细</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-y-4 gap-x-6 text-sm bg-blue-50/50 dark:bg-blue-900/20 p-4 rounded-md border border-blue-100 dark:border-blue-800">
                      <div><span className="text-gray-500 block">产品金额</span><span className="font-medium text-gray-900 dark:text-white">${Number(selectedOrder.product_amount || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">促销折扣</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.promo_discount || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">礼品包装费</span><span className="font-medium text-gray-900 dark:text-white">${Number(selectedOrder.gift_wrap_fee || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">买家运费</span><span className="font-medium text-gray-900 dark:text-white">${Number(selectedOrder.shipping_fee || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">税费</span><span className="font-medium text-gray-900 dark:text-white">${Number(selectedOrder.tax_amount || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">销售收益</span><span className="font-medium text-green-600 dark:text-green-400">${Number(selectedOrder.sales_revenue || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">商城征税</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.marketplace_tax || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">FBA运费</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.fba_fee || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">销售佣金</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.commission_fee || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">订单其他费</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.other_fee || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">亚马逊回款</span><span className="font-medium text-green-600 dark:text-green-400">${Number(selectedOrder.amazon_payout || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">采购成本</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.cogs || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">头程费用</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.freight_cost || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-500 block">测评费用</span><span className="font-medium text-red-600 dark:text-red-400">-${Number(selectedOrder.review_cost || 0).toFixed(2)}</span></div>
                      <div className="bg-white dark:bg-gray-800 p-2 -m-2 rounded shadow-sm border border-gray-100 dark:border-gray-700">
                        <span className="text-gray-500 block">订单利润</span>
                        <span className={`font-bold text-lg ${Number(selectedOrder.order_profit) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          ${Number(selectedOrder.order_profit || 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="bg-white dark:bg-gray-800 p-2 -m-2 rounded shadow-sm border border-gray-100 dark:border-gray-700">
                        <span className="text-gray-500 block">订单利润率</span>
                        <span className={`font-bold text-lg ${Number(selectedOrder.profit_rate) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {(Number(selectedOrder.profit_rate || 0) * 100).toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm dark:focus:ring-offset-gray-800"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50 transition-opacity">
          {toastMsg}
        </div>
      )}
    </div>
  );
}

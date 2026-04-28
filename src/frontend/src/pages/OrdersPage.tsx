import { useEffect, useMemo, useState } from 'react';
import type React from 'react';
import { Download, FileText, MoreHorizontal, RefreshCw, Search, Upload, X } from 'lucide-react';
import api from '../api/client';
import { DataTable } from '../components/DataTable';
import type { Column } from '../types/table';
import { formatSiteTime } from '../utils/timezone';

interface OrderItem {
  order_id: string;
  order_time: string;
  payment_time: string | null;
  refund_time: string | null;
  status: string;
  site: string;
  shop: string;
  store: string;
  owner: string;
  fulfillment: string;
  currency: string;
  order_type: string;
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
  product_amount?: number;
  order_profit?: number;
  quantity?: number;
  refund_quantity?: number;
  [key: string]: unknown;
}

interface OrderDetailResponse {
  basic_info: {
    order_id: string;
    status: string;
    store: string;
    shop?: string;
    site?: string;
    owner?: string;
    currency?: string;
    order_type?: string;
    order_time: string;
    payment_time?: string | null;
    refund_time?: string | null;
    ship_time: string | null;
    shipping_method: string;
    estimated_delivery: string | null;
    logistics_provider: string | null;
    tracking_number: string | null;
    buyer_name: string | null;
    buyer_email: string | null;
    buyer_tax_id: string | null;
  };
  buyer_info?: {
    buyer_name: string | null;
    buyer_email: string | null;
    buyer_tax_id: string | null;
  };
  fulfillment_info?: {
    shipping_method: string | null;
    ship_time: string | null;
    estimated_delivery: string | null;
    logistics_provider: string | null;
    tracking_number: string | null;
  };
  shipping_info: {
    recipient_name: string | null;
    recipient_phone: string | null;
    recipient_zip: string | null;
    recipient_region: string | null;
    recipient_address: string | null;
    ioss_tax_id: string | null;
  };
  products: Array<{
    msku: string;
    fnsku: string | null;
    asin: string;
    title: string;
    item_discount: number;
    unit_price: number;
    quantity: number;
  }>;
  fee_details: {
    product_amount?: number;
    promo_discount?: number;
    gift_wrap_fee?: number;
    buyer_shipping_fee?: number;
    tax?: number;
    sales_revenue?: number;
    marketplace_tax?: number;
    fba_shipping_fee?: number;
    sales_commission?: number;
    other_order_fees?: number;
    amazon_payout?: number;
    cogs?: number;
    first_mile_fee?: number;
    review_cost?: number;
    order_profit?: number;
    order_profit_rate?: number;
    [key: string]: unknown;
  };
}

type OrderDetail = OrderDetailResponse & {
  order_id: string;
  status: string;
  store: string;
  order_time: string;
};

const platformTabs = ['Amazon', '全部平台'];
const yearTabs = ['今年', '2025', '2024', '历史订单'];

const timeRangeOptions = [
  { value: '', label: '全部时间' },
  { value: 'site_today', label: '站点今天' },
  { value: 'last_24h', label: '最近24小时' },
  { value: 'this_week', label: '本周' },
  { value: 'this_month', label: '本月' },
  { value: 'this_year', label: '本年' },
];

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'Pending', label: 'Pending 待处理' },
  { value: 'Shipped', label: 'Shipped 已发货' },
  { value: 'Delivered', label: 'Delivered 已送达' },
  { value: 'Cancelled', label: 'Cancelled 已取消' },
  { value: 'Refunded', label: 'Refunded 已退款' },
];

const searchTypeOptions = [
  { value: '', label: '全部字段' },
  { value: 'order_id', label: '订单号' },
  { value: 'asin', label: 'ASIN' },
  { value: 'msku', label: 'MSKU' },
  { value: 'buyer', label: '买家' },
  { value: 'product_name', label: '品名' },
];

function money(value: unknown) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? `$${n.toFixed(2)}` : '-';
}

function percent(value: unknown) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? `${(n * 100).toFixed(2)}%` : '-';
}

function fmtTime(value: unknown) {
  return value ? formatSiteTime(new Date(String(value))) : '-';
}

function statusClass(status: string) {
  const normalized = status?.toLowerCase();
  if (normalized === 'shipped' || normalized === 'delivered') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (normalized === 'pending') return 'bg-amber-50 text-amber-700 border-amber-200';
  if (normalized === 'cancelled' || normalized === 'refunded') return 'bg-rose-50 text-rose-700 border-rose-200';
  return 'bg-gray-50 text-gray-700 border-gray-200';
}

function normalizeOrderDetail(response: OrderDetailResponse): OrderDetail {
  return {
    ...response,
    order_id: response.basic_info.order_id,
    status: response.basic_info.status,
    store: response.basic_info.store,
    order_time: response.basic_info.order_time,
  };
}

function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-gray-600">
      <span className="shrink-0">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-8 min-w-[118px] rounded border border-gray-300 bg-white px-2 text-xs text-gray-800 outline-none focus:border-blue-500"
      >
        {children}
      </select>
    </label>
  );
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [summary, setSummary] = useState<OrderSummary>({});
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [searchType, setSearchType] = useState('');
  const [status, setStatus] = useState('');
  const [timeRange, setTimeRange] = useState('');
  const [site, setSite] = useState('');
  const [shop, setShop] = useState('');
  const [owner, setOwner] = useState('');
  const [fulfillment, setFulfillment] = useState('');
  const [currency, setCurrency] = useState('');
  const [orderType, setOrderType] = useState('');
  const [timeField, setTimeField] = useState('order_time');
  const [toastMsg, setToastMsg] = useState('');
  const [selectedOrder, setSelectedOrder] = useState<OrderDetail | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    window.setTimeout(() => setToastMsg(''), 2600);
  };

  const buildParams = () => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (search) params.append('search', search);
    if (searchType) params.append('search_type', searchType);
    if (status) params.append('status', status);
    if (timeRange) params.append('time_range', timeRange);
    if (timeField) params.append('time_field', timeField);
    if (site) params.append('site', site);
    if (shop) params.append('shop', shop);
    if (owner) params.append('owner', owner);
    if (fulfillment) params.append('fulfillment', fulfillment);
    if (currency) params.append('currency', currency);
    if (orderType) params.append('order_type', orderType);
    return params;
  };

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/orders?${buildParams().toString()}`);
      setOrders(response.data?.items || []);
      setTotal(response.data?.total_count || 0);
      setSummary(response.data?.summary_row || {});
    } catch {
      showToast('获取订单列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [page, pageSize, search, searchType, status, timeRange, timeField, site, shop, owner, fulfillment, currency, orderType]);

  const fetchOrderDetails = async (id: string) => {
    try {
      const response = await api.get<OrderDetailResponse>(`/orders/${id}`);
      setSelectedOrder(normalizeOrderDetail(response.data));
    } catch {
      showToast('获取订单详情失败');
    }
  };

  const resetFilters = () => {
    setSearch('');
    setSearchType('');
    setStatus('');
    setTimeRange('');
    setSite('');
    setShop('');
    setOwner('');
    setFulfillment('');
    setCurrency('');
    setOrderType('');
    setTimeField('order_time');
    setPage(1);
  };

  const disabledAction = (label: string) => () => showToast(`${label}为批量工具占位，当前 Phase 1.1 暂不执行写操作`);

  const columns = useMemo<Column<OrderItem>[]>(() => [
    {
      key: 'order_id',
      title: '订单号',
      width: 178,
      sortable: true,
      render: (val, row) => (
        <button className="text-left text-xs font-medium text-blue-600 hover:underline" onClick={() => fetchOrderDetails(row.order_id)}>
          {String(val)}
        </button>
      ),
    },
    { key: 'order_time', title: '订购时间', width: 148, sortable: true, render: fmtTime },
    { key: 'payment_time', title: '付款时间', width: 148, render: fmtTime },
    { key: 'refund_time', title: '退款时间', width: 148, render: fmtTime },
    {
      key: 'status',
      title: '订单状态',
      width: 112,
      render: (val) => <span className={`rounded border px-2 py-0.5 text-[11px] ${statusClass(String(val))}`}>{String(val || '-')}</span>,
    },
    {
      key: 'store_site',
      title: '店铺/站点',
      width: 132,
      render: (_, row) => <div className="text-xs"><div className="font-medium">{row.store || row.shop || '-'}</div><div className="text-gray-500">{row.site || '-'}</div></div>,
    },
    { key: 'owner', title: '业务员', width: 86, render: (val) => String(val || '-') },
    { key: 'fulfillment', title: '履约方式', width: 88, render: (val) => String(val || '-') },
    { key: 'order_type', title: '订单类型', width: 96, render: (val) => String(val || '-') },
    { key: 'sales_revenue', title: '销售收入', width: 112, sortable: true, align: 'right', render: money },
    {
      key: 'product_info',
      title: '商品/ASIN/MSKU',
      width: 250,
      render: (_, row) => (
        <div className="flex min-w-[220px] items-center gap-2">
          {row.image_url ? <img src={row.image_url} alt="" className="h-10 w-10 rounded border border-gray-200 object-cover" /> : <div className="h-10 w-10 rounded border bg-gray-50" />}
          <div className="min-w-0 text-xs">
            <div className="truncate font-medium text-gray-900" title={row.product_name}>{row.product_name || '-'}</div>
            <div className="text-gray-500">ASIN: {row.asin || '-'}</div>
            <div className="text-gray-500">MSKU: {row.msku || '-'}</div>
          </div>
        </div>
      ),
    },
    { key: 'quantity', title: '销量', width: 76, align: 'right', sortable: true },
    { key: 'refund_quantity', title: '退款量', width: 82, align: 'right' },
    { key: 'currency', title: '币种', width: 72, render: (val) => String(val || '-') },
    { key: 'promo_code', title: '促销编码', width: 112, render: (val) => String(val || '-') },
    { key: 'product_amount', title: '产品金额', width: 108, align: 'right', render: money },
    {
      key: 'profit_info',
      title: '订单利润/利润率',
      width: 132,
      align: 'right',
      render: (_, row) => (
        <div className="text-right text-xs">
          <div className={Number(row.order_profit) >= 0 ? 'font-medium text-emerald-600' : 'font-medium text-rose-600'}>{money(row.order_profit)}</div>
          <div className="text-gray-500">{percent(row.profit_rate)}</div>
        </div>
      ),
    },
    {
      key: 'actions',
      title: '操作',
      width: 142,
      render: (_, row) => (
        <div className="flex min-w-[130px] items-center gap-2 text-xs">
          <button className="text-blue-600 hover:underline" onClick={() => fetchOrderDetails(row.order_id)}>详情</button>
          <button className="text-blue-600 hover:underline" onClick={disabledAction('录入费用')}>录入费用</button>
          <button className="text-blue-600 hover:underline" onClick={disabledAction('更多操作')}>更多</button>
        </div>
      ),
    },
  ], []);

  const summaryRow = {
    ...summary,
    order_id: `合计 ${summary.total_orders ?? total} 单`,
    sales_revenue: money(summary.sales_revenue),
    product_amount: money(summary.product_amount),
    order_profit: money(summary.order_profit),
  } as unknown as Partial<OrderItem>;

  return (
    <div className="min-h-[calc(100vh-64px)] bg-[#eef0f5] p-3 text-gray-900">
      <div className="overflow-hidden rounded-md border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 bg-white px-3 pt-2">
          <div className="flex items-center gap-5 text-sm">
            {platformTabs.map((tab, index) => (
              <button key={tab} className={`border-b-2 px-1 pb-2 ${index === 0 ? 'border-blue-600 font-medium text-blue-600' : 'border-transparent text-gray-600'}`}>
                {tab}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 py-2">
            {yearTabs.map((tab, index) => (
              <button key={tab} className={`h-7 rounded border px-3 text-xs ${index === 0 ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-300 bg-white text-gray-600'}`}>
                {tab}
              </button>
            ))}
            <span className="mx-1 h-5 w-px bg-gray-200" />
            <FilterSelect label="业务员" value={owner} onChange={(value) => { setOwner(value); setPage(1); }}>
              <option value="">全部业务员</option>
              <option value="Alice">Alice</option>
              <option value="Bob">Bob</option>
              <option value="Cindy">Cindy</option>
              <option value="David">David</option>
            </FilterSelect>
            <FilterSelect label="站点" value={site} onChange={(value) => { setSite(value); setPage(1); }}>
              <option value="">全部站点</option>
              <option value="US">美国站</option>
              <option value="EU">欧洲站</option>
              <option value="JP">日本站</option>
            </FilterSelect>
            <FilterSelect label="店铺" value={shop} onChange={(value) => { setShop(value); setPage(1); }}>
              <option value="">全部店铺</option>
              <option value="PUDIWIND">PUDIWIND</option>
            </FilterSelect>
            <FilterSelect label="状态" value={status} onChange={(value) => { setStatus(value); setPage(1); }}>
              {statusOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </FilterSelect>
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 py-2">
            <FilterSelect label="履约" value={fulfillment} onChange={(value) => { setFulfillment(value); setPage(1); }}>
              <option value="">全部履约</option>
              <option value="FBA">FBA</option>
              <option value="FBM">FBM</option>
              <option value="SFP">SFP</option>
            </FilterSelect>
            <FilterSelect label="时间" value={timeField} onChange={(value) => { setTimeField(value); setPage(1); }}>
              <option value="order_time">订购时间</option>
              <option value="payment_time">付款时间</option>
              <option value="refund_time">退款时间</option>
            </FilterSelect>
            <select value={timeRange} onChange={(event) => { setTimeRange(event.target.value); setPage(1); }} className="h-8 rounded border border-gray-300 bg-white px-2 text-xs outline-none focus:border-blue-500">
              {timeRangeOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </select>
            <FilterSelect label="币种" value={currency} onChange={(value) => { setCurrency(value); setPage(1); }}>
              <option value="">全部币种</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="JPY">JPY</option>
            </FilterSelect>
            <FilterSelect label="订单类型" value={orderType} onChange={(value) => { setOrderType(value); setPage(1); }}>
              <option value="">全部类型</option>
              <option value="Normal">Normal</option>
              <option value="Replacement">Replacement</option>
            </FilterSelect>
            <select value={searchType} onChange={(event) => setSearchType(event.target.value)} className="h-8 rounded border border-gray-300 bg-white px-2 text-xs outline-none focus:border-blue-500">
              {searchTypeOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </select>
            <div className="flex h-8 min-w-[300px] items-center rounded border border-gray-300 bg-white px-2">
              <Search className="mr-2 h-4 w-4 text-gray-400" />
              <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="搜索订单号 / ASIN / MSKU / 买家" className="min-w-0 flex-1 text-xs outline-none" />
            </div>
            <button className="h-8 rounded border border-gray-300 px-3 text-xs text-gray-700" onClick={resetFilters}>重置</button>
            <button className="h-8 rounded bg-blue-600 px-3 text-xs text-white" onClick={fetchOrders}>查询</button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-[#f7f8fa] px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('录入费用')}><FileText className="h-4 w-4" />录入费用</button>
            <button className="h-8 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('标记测评')}>标记测评</button>
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('上传发票')}><Upload className="h-4 w-4" />上传发票</button>
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={fetchOrders}><RefreshCw className="h-4 w-4" />同步订单</button>
            <button className="h-8 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('导入成本')}>导入成本</button>
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-2 text-xs text-gray-700" onClick={disabledAction('更多操作')}><MoreHorizontal className="h-4 w-4" />更多</button>
          </div>
          <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('导出订单')}><Download className="h-4 w-4" />导出</button>
        </div>

        <div className="h-[calc(100vh-250px)] min-h-[480px]">
          <DataTable
            columns={columns}
            data={orders}
            loading={loading}
            rowKey="order_id"
            summaryRow={summaryRow}
            className="h-full"
            stickyHeaderOffset={0}
            pagination={{
              current: page,
              pageSize,
              total,
              onChange: (p, s) => {
                setPage(p);
                setPageSize(s);
              },
            }}
          />
        </div>
      </div>

      {selectedOrder && (
        <div className="fixed inset-0 z-50 bg-black/35" role="dialog" aria-modal="true">
          <div className="absolute right-0 top-0 flex h-full w-full max-w-5xl flex-col bg-white shadow-2xl">
            <div className="flex h-12 items-center justify-between border-b border-gray-200 px-4">
              <div className="text-sm font-semibold">订单详情 - {selectedOrder.order_id}</div>
              <button className="rounded p-1 text-gray-500 hover:bg-gray-100" onClick={() => setSelectedOrder(null)}><X className="h-5 w-5" /></button>
            </div>
            <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_300px] overflow-hidden">
              <div className="min-h-0 space-y-4 overflow-auto p-4 text-xs">
                <section className="rounded border border-gray-200">
                  <div className="border-b bg-gray-50 px-3 py-2 font-medium">订单基础信息</div>
                  <div className="grid grid-cols-4 gap-x-4 gap-y-3 p-3">
                    <Info label="订单号" value={selectedOrder.basic_info.order_id} />
                    <Info label="状态" value={selectedOrder.basic_info.status} />
                    <Info label="店铺" value={selectedOrder.basic_info.store} />
                    <Info label="站点" value={selectedOrder.basic_info.site || '-'} />
                    <Info label="业务员" value={selectedOrder.basic_info.owner || '-'} />
                    <Info label="币种" value={selectedOrder.basic_info.currency || '-'} />
                    <Info label="订单类型" value={selectedOrder.basic_info.order_type || '-'} />
                    <Info label="订购时间" value={fmtTime(selectedOrder.basic_info.order_time)} />
                    <Info label="付款时间" value={fmtTime(selectedOrder.basic_info.payment_time)} />
                    <Info label="退款时间" value={fmtTime(selectedOrder.basic_info.refund_time)} />
                  </div>
                </section>
                <section className="rounded border border-gray-200">
                  <div className="border-b bg-gray-50 px-3 py-2 font-medium">买家信息</div>
                  <div className="grid grid-cols-3 gap-x-4 gap-y-3 p-3">
                    <Info label="买家姓名" value={selectedOrder.buyer_info?.buyer_name || selectedOrder.basic_info.buyer_name || '-'} />
                    <Info label="买家邮箱" value={selectedOrder.buyer_info?.buyer_email || selectedOrder.basic_info.buyer_email || '-'} />
                    <Info label="税号" value={selectedOrder.buyer_info?.buyer_tax_id || selectedOrder.basic_info.buyer_tax_id || '-'} />
                  </div>
                </section>
                <section className="rounded border border-gray-200">
                  <div className="border-b bg-gray-50 px-3 py-2 font-medium">物流/履约信息</div>
                  <div className="grid grid-cols-3 gap-x-4 gap-y-3 p-3">
                    <Info label="履约方式" value={selectedOrder.fulfillment_info?.shipping_method || selectedOrder.basic_info.shipping_method} />
                    <Info label="发货时间" value={fmtTime(selectedOrder.fulfillment_info?.ship_time || selectedOrder.basic_info.ship_time)} />
                    <Info label="预计送达" value={fmtTime(selectedOrder.fulfillment_info?.estimated_delivery || selectedOrder.basic_info.estimated_delivery)} />
                    <Info label="物流商" value={selectedOrder.fulfillment_info?.logistics_provider || selectedOrder.basic_info.logistics_provider || '-'} />
                    <Info label="运单号" value={selectedOrder.fulfillment_info?.tracking_number || selectedOrder.basic_info.tracking_number || '-'} />
                    <Info label="收件人" value={selectedOrder.shipping_info.recipient_name || '-'} />
                    <Info label="电话" value={selectedOrder.shipping_info.recipient_phone || '-'} />
                    <Info label="邮编" value={selectedOrder.shipping_info.recipient_zip || '-'} />
                    <Info label="地区" value={selectedOrder.shipping_info.recipient_region || '-'} />
                    <Info label="地址" value={selectedOrder.shipping_info.recipient_address || '-'} wide />
                    <Info label="IOSS税号" value={selectedOrder.shipping_info.ioss_tax_id || '-'} />
                  </div>
                </section>
                <section className="rounded border border-gray-200">
                  <div className="border-b bg-gray-50 px-3 py-2 font-medium">商品多行</div>
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 text-gray-500">
                      <tr>
                        <th className="px-3 py-2 text-left">MSKU / FNSKU</th>
                        <th className="px-3 py-2 text-left">ASIN / 标题</th>
                        <th className="px-3 py-2 text-right">商品折扣</th>
                        <th className="px-3 py-2 text-right">单价</th>
                        <th className="px-3 py-2 text-right">销量</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedOrder.products.map((product) => (
                        <tr key={`${product.asin}-${product.msku}`} className="border-t">
                          <td className="px-3 py-2"><div>{product.msku}</div><div className="text-gray-500">{product.fnsku || '-'}</div></td>
                          <td className="px-3 py-2"><div>{product.asin}</div><div className="max-w-xl truncate text-gray-500">{product.title}</div></td>
                          <td className="px-3 py-2 text-right text-rose-600">-{money(product.item_discount)}</td>
                          <td className="px-3 py-2 text-right">{money(product.unit_price)}</td>
                          <td className="px-3 py-2 text-right">{product.quantity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              </div>
              <aside className="min-h-0 overflow-auto border-l border-gray-200 bg-[#fafafa] p-4 text-xs">
                <div className="mb-3 text-sm font-semibold">费用字段</div>
                <Fee label="产品金额" value={selectedOrder.fee_details.product_amount} positive />
                <Fee label="促销折扣" value={selectedOrder.fee_details.promo_discount} />
                <Fee label="礼品包装费" value={selectedOrder.fee_details.gift_wrap_fee} positive />
                <Fee label="买家运费" value={selectedOrder.fee_details.buyer_shipping_fee} positive />
                <Fee label="税费" value={selectedOrder.fee_details.tax} positive />
                <Fee label="销售收入" value={selectedOrder.fee_details.sales_revenue} positive strong />
                <Fee label="商城征税" value={selectedOrder.fee_details.marketplace_tax} />
                <Fee label="FBA运费" value={selectedOrder.fee_details.fba_shipping_fee} />
                <Fee label="销售佣金" value={selectedOrder.fee_details.sales_commission} />
                <Fee label="订单其他费" value={selectedOrder.fee_details.other_order_fees} />
                <Fee label="亚马逊回款" value={selectedOrder.fee_details.amazon_payout} positive strong />
                <Fee label="采购成本" value={selectedOrder.fee_details.cogs} />
                <Fee label="头程费用" value={selectedOrder.fee_details.first_mile_fee} />
                <Fee label="测评费用" value={selectedOrder.fee_details.review_cost} />
                <div className="mt-4 rounded border border-blue-200 bg-blue-50 p-3">
                  <div className="flex justify-between font-semibold text-blue-900"><span>订单利润</span><span>{money(selectedOrder.fee_details.order_profit)}</span></div>
                  <div className="mt-1 flex justify-between text-blue-700"><span>订单利润率</span><span>{percent(selectedOrder.fee_details.order_profit_rate)}</span></div>
                </div>
              </aside>
            </div>
          </div>
        </div>
      )}

      {toastMsg && <div className="fixed bottom-4 right-4 z-50 rounded bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">{toastMsg}</div>}
    </div>
  );
}

function Info({ label, value, wide = false }: { label: string; value: React.ReactNode; wide?: boolean }) {
  return (
    <div className={wide ? 'col-span-2' : ''}>
      <div className="mb-1 text-gray-500">{label}</div>
      <div className="break-words text-gray-900">{value}</div>
    </div>
  );
}

function Fee({ label, value, positive = false, strong = false }: { label: string; value: unknown; positive?: boolean; strong?: boolean }) {
  const amount = Number(value ?? 0);
  const text = positive || amount === 0 ? money(amount) : `-${money(Math.abs(amount))}`;
  return (
    <div className={`flex justify-between border-b border-gray-200 py-2 ${strong ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
      <span>{label}</span>
      <span className={positive ? 'text-emerald-600' : 'text-rose-600'}>{text}</span>
    </div>
  );
}

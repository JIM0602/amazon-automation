import { useEffect, useMemo, useState } from 'react';
import type React from 'react';
import { Download, HelpCircle, RefreshCw, Search, Settings, SlidersHorizontal } from 'lucide-react';
import api from '../api/client';
import { DataTable } from '../components/DataTable';
import type { Column } from '../types/table';
import { formatSiteTime } from '../utils/timezone';

type ReturnDimension = 'parent_asin' | 'asin' | 'msku' | 'order';

interface ReturnAnalysisRow {
  id: string;
  order_id?: string;
  after_sale_tags?: string[];
  return_time?: string | null;
  order_time?: string | null;
  site_return_time?: string | null;
  store?: string;
  site?: string;
  image_url?: string;
  asin?: string;
  msku?: string;
  product_title?: string;
  product_name?: string;
  sku?: string;
  parent_asin?: string;
  buyer_notes?: string;
  return_quantity?: number;
  refund_quantity?: number;
  sales_quantity?: number;
  warehouse_id?: string;
  inventory_property?: string;
  disposition?: string;
  return_reason?: string;
  status?: string;
  lpn_number?: string | null;
  notes?: string;
  owner?: string;
  return_order_count?: number;
  return_rate?: number;
  refund_rate?: number;
  return_quantity_mom?: number;
  main_return_reason?: string;
  [key: string]: unknown;
}

interface ReturnSummary {
  total_return_orders?: number;
  total_return_quantity?: number;
  total_refund_quantity?: number;
  total_sales_quantity?: number;
  return_rate?: number;
  refund_rate?: number;
  [key: string]: unknown;
}

const dimensions: Array<{ value: ReturnDimension; label: string }> = [
  { value: 'parent_asin', label: '父ASIN' },
  { value: 'asin', label: 'ASIN' },
  { value: 'msku', label: 'MSKU' },
  { value: 'order', label: '订单号' },
];

const timeRangeOptions = [
  { value: '', label: '全部时间' },
  { value: 'site_today', label: '站点今天' },
  { value: 'last_24h', label: '最近24小时' },
  { value: 'this_week', label: '本周' },
  { value: 'this_month', label: '本月' },
  { value: 'this_year', label: '本年' },
];

const reasonOptions = [
  { value: '', label: '全部退货原因' },
  { value: 'DEFECTIVE', label: '产品缺陷' },
  { value: 'UNWANTED_ITEM', label: '不想要了' },
  { value: 'CUSTOMER_CHANGED_MIND', label: '买错/改变主意' },
  { value: 'WRONG_ITEM', label: '发错货' },
  { value: 'DAMAGED_BY_FC', label: '仓库损坏' },
  { value: 'NOT_AS_DESCRIBED', label: '与描述不符' },
];

const statusOptions = [
  { value: '', label: '全部处理状态' },
  { value: 'Pending', label: 'Pending 待处理' },
  { value: 'Received', label: 'Received 已收件' },
  { value: 'Refunded', label: 'Refunded 已退款' },
  { value: 'Closed', label: 'Closed 已关闭' },
];

const dispositionOptions = [
  { value: '', label: '全部库存属性' },
  { value: '可售', label: '可售' },
  { value: '不可售', label: '不可售' },
  { value: 'customer', label: 'Customer damaged' },
  { value: 'warehouse', label: 'Warehouse damaged' },
];

const searchTypeOptions = [
  { value: '', label: '全部字段' },
  { value: 'order_id', label: '订单号' },
  { value: 'asin', label: 'ASIN' },
  { value: 'parent_asin', label: '父ASIN' },
  { value: 'msku', label: 'MSKU' },
  { value: 'product_name', label: '品名' },
];

function fmtTime(value: unknown) {
  return value ? formatSiteTime(new Date(String(value))) : '-';
}

function percent(value: unknown) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? `${(n * 100).toFixed(2)}%` : '-';
}

function reasonText(reasonCode: string | undefined) {
  return reasonOptions.find((item) => item.value === reasonCode)?.label ?? reasonCode ?? '-';
}

function statusClass(status: string | undefined) {
  const normalized = status?.toLowerCase();
  if (normalized === 'received') return 'bg-blue-50 text-blue-700 border-blue-200';
  if (normalized === 'pending') return 'bg-amber-50 text-amber-700 border-amber-200';
  if (normalized === 'refunded') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (normalized === 'closed') return 'bg-gray-50 text-gray-700 border-gray-200';
  return 'bg-gray-50 text-gray-700 border-gray-200';
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

function SummaryCard({ label, value, tone = 'neutral' }: { label: string; value: React.ReactNode; tone?: 'neutral' | 'blue' | 'green' | 'orange' }) {
  const toneClass = {
    neutral: 'text-gray-900',
    blue: 'text-blue-700',
    green: 'text-emerald-700',
    orange: 'text-amber-700',
  }[tone];
  return (
    <div className="min-w-[138px] border-r border-gray-200 px-4 py-2 last:border-r-0">
      <div className="text-[11px] text-gray-500">{label}</div>
      <div className={`mt-1 text-base font-semibold ${toneClass}`}>{value}</div>
    </div>
  );
}

export default function ReturnsPage() {
  const [rows, setRows] = useState<ReturnAnalysisRow[]>([]);
  const [summary, setSummary] = useState<ReturnSummary>({});
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [dimension, setDimension] = useState<ReturnDimension>('order');
  const [site, setSite] = useState('');
  const [shop, setShop] = useState('');
  const [owner, setOwner] = useState('');
  const [tag, setTag] = useState('');
  const [timeRange, setTimeRange] = useState('');
  const [searchType, setSearchType] = useState('');
  const [search, setSearch] = useState('');
  const [reason, setReason] = useState('');
  const [status, setStatus] = useState('');
  const [disposition, setDisposition] = useState('');
  const [toastMsg, setToastMsg] = useState('');

  const showToast = (msg: string) => {
    setToastMsg(msg);
    window.setTimeout(() => setToastMsg(''), 2600);
  };

  const buildParams = () => {
    const params = new URLSearchParams({
      dimension,
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (site) params.append('site', site);
    if (shop) params.append('shop', shop);
    if (owner) params.append('owner', owner);
    if (tag) params.append('tag', tag);
    if (timeRange) params.append('time_range', timeRange);
    if (searchType) params.append('search_type', searchType);
    if (search) params.append('search', search);
    if (reason) params.append('reason', reason);
    if (status) params.append('status', status);
    if (disposition) params.append('disposition', disposition);
    return params;
  };

  const fetchReturns = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/returns/analysis?${buildParams().toString()}`);
      setRows(response.data?.items || []);
      setTotal(response.data?.total_count || 0);
      setSummary(response.data?.summary_row || {});
    } catch {
      showToast('获取退货分析失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReturns();
  }, [dimension, page, pageSize, site, shop, owner, tag, timeRange, searchType, search, reason, status, disposition]);

  const resetFilters = () => {
    setSite('');
    setShop('');
    setOwner('');
    setTag('');
    setTimeRange('');
    setSearchType('');
    setSearch('');
    setReason('');
    setStatus('');
    setDisposition('');
    setPage(1);
  };

  const disabledAction = (label: string) => () => showToast(`${label}为占位入口，当前 Phase 1.1 暂不执行写操作`);

  const orderColumns = useMemo<Column<ReturnAnalysisRow>[]>(() => [
    {
      key: 'order_id',
      title: '订单号',
      width: 176,
      sortable: true,
      render: (val) => <span className="text-xs font-medium text-blue-600">{String(val || '-')}</span>,
    },
    {
      key: 'after_sale_tags',
      title: '退货标记',
      width: 132,
      render: (val) => {
        const tags = (val as string[]) || [];
        return tags.length ? (
          <div className="flex flex-wrap gap-1">
            {tags.map((item) => <span key={item} className="rounded border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[10px] text-rose-700">{item}</span>)}
          </div>
        ) : '-';
      },
    },
    { key: 'return_time', title: '退货时间', width: 148, sortable: true, render: fmtTime },
    { key: 'order_time', title: '订购时间', width: 148, render: fmtTime },
    { key: 'site_return_time', title: '站点退货时间', width: 148, render: fmtTime },
    {
      key: 'store_site',
      title: '店铺/站点',
      width: 132,
      render: (_, row) => <div className="text-xs"><div className="font-medium">{row.store || '-'}</div><div className="text-gray-500">{row.site || '-'}</div></div>,
    },
    {
      key: 'product_info',
      title: '商品信息',
      width: 260,
      render: (_, row) => (
        <div className="flex min-w-[230px] items-center gap-2">
          {row.image_url ? <img src={row.image_url} alt="" className="h-10 w-10 rounded border border-gray-200 object-cover" /> : <div className="h-10 w-10 rounded border bg-gray-50" />}
          <div className="min-w-0 text-xs">
            <div className="truncate font-medium text-gray-900" title={row.product_title}>{row.product_title || row.product_name || '-'}</div>
            <div className="text-gray-500">ASIN: {row.asin || '-'}</div>
            <div className="text-gray-500">MSKU: {row.msku || '-'}</div>
          </div>
        </div>
      ),
    },
    { key: 'parent_asin', title: '父ASIN', width: 120, render: (val) => String(val || '-') },
    { key: 'buyer_notes', title: '买家备注', width: 180, render: (val) => <div className="max-w-[160px] truncate text-xs" title={String(val || '')}>{String(val || '-')}</div> },
    { key: 'return_quantity', title: '退货量', width: 78, align: 'right', sortable: true },
    { key: 'warehouse_id', title: '仓库编号', width: 112, render: (val) => String(val || '-') },
    { key: 'disposition', title: '库存属性', width: 120, render: (val) => String(val || '-') },
    { key: 'return_reason', title: '退货原因', width: 130, render: (val) => reasonText(String(val || '')) },
    {
      key: 'status',
      title: '处理状态',
      width: 110,
      render: (val) => <span className={`rounded border px-2 py-0.5 text-[11px] ${statusClass(String(val))}`}>{String(val || '-')}</span>,
    },
    { key: 'lpn_number', title: 'LPN编号', width: 128, render: (val) => String(val || '-') },
    { key: 'notes', title: '备注', width: 160, render: (val) => <div className="max-w-[140px] truncate text-xs" title={String(val || '')}>{String(val || '-')}</div> },
  ], []);

  const groupColumns = useMemo<Column<ReturnAnalysisRow>[]>(() => [
    {
      key: 'dimension_value',
      title: dimensions.find((item) => item.value === dimension)?.label || '维度',
      width: 160,
      sortable: true,
      render: (val) => <span className="text-xs font-semibold text-gray-900">{String(val || '-')}</span>,
    },
    {
      key: 'product_info',
      title: '商品信息',
      width: 280,
      render: (_, row) => (
        <div className="flex min-w-[240px] items-center gap-2">
          {row.image_url ? <img src={row.image_url} alt="" className="h-10 w-10 rounded border border-gray-200 object-cover" /> : <div className="h-10 w-10 rounded border bg-gray-50" />}
          <div className="min-w-0 text-xs">
            <div className="truncate font-medium text-gray-900" title={row.product_title}>{row.product_title || '-'}</div>
            <div className="text-gray-500">父ASIN: {row.parent_asin || '-'}</div>
            <div className="text-gray-500">ASIN/MSKU: {row.asin || '-'} / {row.msku || '-'}</div>
          </div>
        </div>
      ),
    },
    { key: 'store', title: '店铺', width: 120, render: (val) => String(val || '-') },
    { key: 'site', title: '站点', width: 78, render: (val) => String(val || '-') },
    { key: 'owner', title: '业务员', width: 88, render: (val) => String(val || '-') },
    { key: 'return_order_count', title: '退货订单数', width: 104, align: 'right', sortable: true },
    { key: 'return_quantity', title: '退货量', width: 84, align: 'right', sortable: true },
    { key: 'refund_quantity', title: '退款量', width: 84, align: 'right' },
    { key: 'sales_quantity', title: '销量', width: 84, align: 'right' },
    { key: 'return_rate', title: '退货率', width: 92, align: 'right', sortable: true, render: percent },
    { key: 'refund_rate', title: '退款率', width: 92, align: 'right', render: percent },
    { key: 'return_quantity_mom', title: '退货量环比', width: 104, align: 'right', render: (val) => Number(val || 0) === 0 ? '-' : String(val) },
    { key: 'main_return_reason', title: '主要原因', width: 130, render: (val) => reasonText(String(val || '')) },
  ], [dimension]);

  const columns = dimension === 'order' ? orderColumns : groupColumns;

  const summaryRow = {
    order_id: `合计 ${total} 条`,
    dimension_value: `合计 ${total} 条`,
    return_order_count: summary.total_return_orders,
    return_quantity: summary.total_return_quantity,
    refund_quantity: summary.total_refund_quantity,
    sales_quantity: summary.total_sales_quantity,
    return_rate: summary.return_rate,
    refund_rate: summary.refund_rate,
  } as Partial<ReturnAnalysisRow>;

  return (
    <div className="min-h-[calc(100vh-64px)] bg-[#eef0f5] p-3 text-gray-900">
      <div className="overflow-hidden rounded-md border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 bg-white px-3 pt-2">
          <div className="flex items-center gap-5 text-sm">
            {dimensions.map((item) => (
              <button
                key={item.value}
                onClick={() => { setDimension(item.value); setPage(1); }}
                className={`border-b-2 px-1 pb-2 ${dimension === item.value ? 'border-blue-600 font-medium text-blue-600' : 'border-transparent text-gray-600'}`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 py-2">
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
            <FilterSelect label="业务员" value={owner} onChange={(value) => { setOwner(value); setPage(1); }}>
              <option value="">全部业务员</option>
              <option value="-">未分配</option>
            </FilterSelect>
            <FilterSelect label="退货标记" value={tag} onChange={(value) => { setTag(value); setPage(1); }}>
              <option value="">全部标记</option>
              <option value="FBA">FBA退货</option>
            </FilterSelect>
            <FilterSelect label="退货原因" value={reason} onChange={(value) => { setReason(value); setPage(1); }}>
              {reasonOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </FilterSelect>
            <FilterSelect label="处理状态" value={status} onChange={(value) => { setStatus(value); setPage(1); }}>
              {statusOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </FilterSelect>
            <FilterSelect label="库存属性" value={disposition} onChange={(value) => { setDisposition(value); setPage(1); }}>
              {dispositionOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </FilterSelect>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 py-2">
            <select value={timeRange} onChange={(event) => { setTimeRange(event.target.value); setPage(1); }} className="h-8 rounded border border-gray-300 bg-white px-2 text-xs outline-none focus:border-blue-500">
              {timeRangeOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </select>
            <select value={searchType} onChange={(event) => setSearchType(event.target.value)} className="h-8 rounded border border-gray-300 bg-white px-2 text-xs outline-none focus:border-blue-500">
              {searchTypeOptions.map((option) => <option key={option.value || 'all'} value={option.value}>{option.label}</option>)}
            </select>
            <div className="flex h-8 min-w-[320px] items-center rounded border border-gray-300 bg-white px-2">
              <Search className="mr-2 h-4 w-4 text-gray-400" />
              <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="搜索订单号 / LPN / ASIN / MSKU / 品名" className="min-w-0 flex-1 text-xs outline-none" />
            </div>
            <button className="h-8 rounded border border-gray-300 px-3 text-xs text-gray-700" onClick={resetFilters}>重置</button>
            <button className="h-8 rounded bg-blue-600 px-3 text-xs text-white" onClick={fetchReturns}>查询</button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-[#f7f8fa] px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('获取退货处理指标')}><RefreshCw className="h-4 w-4" />获取退货处理指标</button>
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('退货标记提醒')}><Settings className="h-4 w-4" />退货标记提醒</button>
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('自定义列')}><SlidersHorizontal className="h-4 w-4" />自定义列</button>
            <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('使用帮助')}><HelpCircle className="h-4 w-4" />使用帮助</button>
          </div>
          <button className="inline-flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-xs text-gray-700" onClick={disabledAction('导出退货分析')}><Download className="h-4 w-4" />导出</button>
        </div>

        <div className="flex flex-wrap border-b border-gray-200 bg-white">
          <SummaryCard label="退货订单数" value={summary.total_return_orders ?? 0} tone="blue" />
          <SummaryCard label="退货量" value={summary.total_return_quantity ?? 0} tone="orange" />
          <SummaryCard label="退款量" value={summary.total_refund_quantity ?? 0} />
          <SummaryCard label="销量" value={summary.total_sales_quantity ?? 0} />
          <SummaryCard label="退货率" value={percent(summary.return_rate)} tone="orange" />
          <SummaryCard label="退款率" value={percent(summary.refund_rate)} tone="green" />
        </div>

        <div className="h-[calc(100vh-292px)] min-h-[480px]">
          <DataTable
            columns={columns}
            data={rows}
            loading={loading}
            rowKey="id"
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

      {toastMsg && <div className="fixed bottom-4 right-4 z-50 rounded bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">{toastMsg}</div>}
    </div>
  );
}

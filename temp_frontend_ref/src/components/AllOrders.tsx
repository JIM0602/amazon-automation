import { useState } from 'react';
import { 
  Search, Filter, Download, RefreshCw, ChevronLeft, ChevronRight, 
  ExternalLink, MoreHorizontal, Calendar, DollarSign, ShoppingCart, RotateCcw
} from 'lucide-react';
import { cn } from '../lib/utils';

const orders = [
  { id: '114-0281014-2837027', time: '2026-04-02 23:57:35', payTime: '2026-04-03 23:29:27', refundTime: '-', status: 'Shipped', revenue: 'US$6.49', image: 'https://picsum.photos/seed/o1/50/50', sku: 'Basicdogleash-DL0402', sales: 2, refundQty: 0, promo: 'PLM-5fd39060-...', amount: 'US$11.98', profit: 'US$-10.89', margin: '-181.73%' },
  { id: '113-8440676-2527420', time: '2026-04-02 22:04:58', payTime: '2026-04-03 23:30:20', refundTime: '-', status: 'Shipped', revenue: 'US$3.25', image: 'https://picsum.photos/seed/o2/50/50', sku: 'Basicdogleash-DL0402', sales: 1, refundQty: 0, promo: 'PLM-5fd39060-...', amount: 'US$5.99', profit: 'US$-5.43', margin: '-180.56%' },
  { id: '113-0927773-8471409', time: '2026-04-02 20:17:18', payTime: '2026-04-03 23:41:08', refundTime: '-', status: 'Shipped', revenue: 'US$6.56', image: 'https://picsum.photos/seed/o3/50/50', sku: 'Basicdogleash-DL0402', sales: 2, refundQty: 0, promo: 'PLM-5fd39060-...', amount: 'US$11.98', profit: 'US$-10.82', margin: '-181.70%' },
  { id: '112-4001208-8193056', time: '2026-04-02 19:41:31', payTime: '2026-04-03 00:54:46', refundTime: '-', status: 'Shipped', revenue: 'US$3.20', image: 'https://picsum.photos/seed/o4/50/50', sku: 'Basicdogleash-DL0402', sales: 1, refundQty: 0, promo: 'PLM-5fd39060-...', amount: 'US$5.99', profit: 'US$-5.49', margin: '-183.54%' },
];

export default function AllOrders() {
  const [pageSize, setPageSize] = useState(200);

  return (
    <div className="h-full flex flex-col bg-[var(--bg-main)]">
      <div className="p-4 border-b border-[var(--border-color)] bg-[var(--bg-card)] space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg p-1">
            <button className="px-3 py-1 bg-white dark:bg-slate-800 text-brand-600 rounded-md text-xs font-bold shadow-sm">2025年至今</button>
            <button className="px-3 py-1 text-slate-500 text-xs font-bold">历史订单</button>
          </div>
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>业务员</option>
          </select>
          <div className="flex items-center gap-1 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <span>美</span>
            <X size={12} className="text-slate-400" />
          </div>
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>全部店铺</option>
          </select>
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>全部状态</option>
          </select>
          <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <Calendar size={14} className="text-slate-400" />
            <span>2026-03-27 ~ 2026-04-02</span>
          </div>
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input 
              type="text" 
              placeholder="双击可批量搜索内容" 
              className="w-full pl-9 pr-4 py-1.5 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg text-xs"
            />
          </div>
          <button className="p-2 bg-brand-600 text-white rounded-lg hover:bg-brand-500 transition-colors">
            <Search size={14} />
          </button>
          <button className="p-2 border border-[var(--border-color)] rounded-lg hover:bg-slate-50 transition-colors">
            <RefreshCw size={14} className="text-slate-500" />
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button className="px-4 py-1.5 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded-lg text-xs font-bold border border-brand-200 dark:border-brand-800">录入费用</button>
            <button className="px-4 py-1.5 border border-[var(--border-color)] rounded-lg text-xs font-bold text-slate-500">同步订单</button>
            <button className="px-4 py-1.5 border border-[var(--border-color)] rounded-lg text-xs font-bold text-slate-500">导入成本</button>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
              <span>订单利润为负</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
              <span>采购成本或运费为0</span>
            </label>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto custom-scrollbar">
        <table className="erp-table min-w-[1800px]">
          <thead>
            <tr>
              <th className="w-10"><input type="checkbox" className="rounded border-slate-300" /></th>
              <th>订单号</th>
              <th>订购时间</th>
              <th>付款时间</th>
              <th>退款时间</th>
              <th>订单状态</th>
              <th className="text-right">销售收益</th>
              <th>图片/ASIN/MSKU</th>
              <th>品名/SKU</th>
              <th className="text-right">销量</th>
              <th className="text-right">退款量</th>
              <th>促销编码</th>
              <th className="text-right">产品金额</th>
              <th className="text-right">订单利润/利润率</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td className="w-10"><input type="checkbox" className="rounded border-slate-300" /></td>
                <td>
                  <div className="flex flex-col">
                    <span className="text-brand-600 dark:text-brand-400 font-medium hover:underline cursor-pointer">{order.id}</span>
                    <div className="flex gap-1 mt-1">
                      <span className="px-1 bg-orange-100 text-orange-600 rounded text-[9px] font-bold">a 促销</span>
                    </div>
                  </div>
                </td>
                <td className="font-mono text-slate-500">{order.time}</td>
                <td className="font-mono text-slate-500">{order.payTime}</td>
                <td className="font-mono text-slate-500">{order.refundTime}</td>
                <td>
                  <span className={cn(
                    "px-2 py-0.5 rounded-full text-[10px] font-bold",
                    order.status === 'Shipped' ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-500"
                  )}>
                    {order.status}
                  </span>
                </td>
                <td className="text-right font-mono font-bold">{order.revenue}</td>
                <td>
                  <div className="flex items-center gap-2">
                    <img src={order.image} alt="product" className="w-8 h-8 rounded border border-[var(--border-color)]" referrerPolicy="no-referrer" />
                    <div className="flex flex-col text-[10px]">
                      <span className="text-slate-400">ASIN: <span className="text-brand-600">B0F295GR54</span></span>
                      <span className="text-slate-400">MSKU: D</span>
                    </div>
                  </div>
                </td>
                <td>
                  <div className="flex flex-col">
                    <span className="text-slate-600 truncate max-w-[150px]">Basicdogleash-...</span>
                    <span className="font-bold text-slate-900 dark:text-slate-200">{order.sku}</span>
                  </div>
                </td>
                <td className="text-right font-mono">{order.sales}</td>
                <td className="text-right font-mono">{order.refundQty}</td>
                <td className="text-slate-500 truncate max-w-[100px]">{order.promo}</td>
                <td className="text-right font-mono font-bold">{order.amount}</td>
                <td className="text-right">
                  <div className="flex flex-col">
                    <span className="font-mono font-bold text-rose-600">{order.profit}</span>
                    <span className="text-[10px] text-rose-500">{order.margin}</span>
                  </div>
                </td>
                <td>
                  <div className="flex items-center gap-2">
                    <button className="text-brand-600 hover:underline">联系买家</button>
                    <button className="p-1 text-slate-400 hover:text-slate-600"><MoreHorizontal size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-3 border-t border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-4">
          <span>已选 0 条</span>
          <div className="flex items-center gap-2">
            <span>共 111 条</span>
            <div className="flex items-center gap-1">
              <button className="p-1 border border-[var(--border-color)] rounded hover:bg-slate-50"><ChevronLeft size={14} /></button>
              <button className="w-6 h-6 bg-brand-600 text-white rounded flex items-center justify-center font-bold">1</button>
              <button className="p-1 border border-[var(--border-color)] rounded hover:bg-slate-50"><ChevronRight size={14} /></button>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <select 
            value={pageSize} 
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded px-2 py-1"
          >
            <option value={20}>20条/页</option>
            <option value={50}>50条/页</option>
            <option value={100}>100条/页</option>
            <option value={200}>200条/页</option>
          </select>
          <div className="flex items-center gap-1">
            <span>前往</span>
            <input type="text" defaultValue="1" className="w-8 border border-[var(--border-color)] rounded px-1 text-center" />
            <span>页</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function X({ size, className }: { size: number, className?: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
    </svg>
  );
}

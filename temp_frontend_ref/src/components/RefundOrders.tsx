import { useState } from 'react';
import { 
  Search, Filter, Download, RefreshCw, ChevronLeft, ChevronRight, 
  MoreHorizontal, Calendar, RotateCcw, Package, Warehouse
} from 'lucide-react';
import { cn } from '../lib/utils';

const refunds = [
  { id: '114-0281014-2837027', orderTime: '2026-04-02 23:57:35', refundTime: '2026-04-05 10:12:44', image: 'https://picsum.photos/seed/r1/50/50', sku: 'Basicdogleash-DL0402', note: '买家备注: 尺寸不合适，需要退货', qty: 1, warehouse: 'FBA-US-001', inventory: 'Sellable', reason: 'Defective', status: 'Completed', lpn: 'LPN001234567' },
  { id: '113-8440676-2527420', orderTime: '2026-04-02 22:04:58', refundTime: '2026-04-04 15:30:20', image: 'https://picsum.photos/seed/r2/50/50', sku: 'Basicdogleash-DL0402', note: '-', qty: 1, warehouse: 'FBA-US-002', inventory: 'Unsellable', reason: 'Customer Damaged', status: 'Pending', lpn: 'LPN001234568' },
];

export default function RefundOrders() {
  const [pageSize, setPageSize] = useState(200);

  return (
    <div className="h-full flex flex-col bg-[var(--bg-main)]">
      <div className="p-4 border-b border-[var(--border-color)] bg-[var(--bg-card)] space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg p-1">
            <button className="px-3 py-1 bg-white dark:bg-slate-800 text-brand-600 rounded-md text-xs font-bold shadow-sm">2025年至今</button>
            <button className="px-3 py-1 text-slate-500 text-xs font-bold">历史退货</button>
          </div>
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>业务员</option>
          </select>
          <select className="bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <option>全部店铺</option>
          </select>
          <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-900 border border-[var(--border-color)] rounded-lg px-3 py-1.5 text-xs">
            <Calendar size={14} className="text-slate-400" />
            <span>2026-03-27 ~ 2026-04-02</span>
          </div>
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input 
              type="text" 
              placeholder="搜索订单号/SKU/LPN..." 
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
            <button className="px-4 py-1.5 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded-lg text-xs font-bold border border-brand-200 dark:border-brand-800 flex items-center gap-2">
              <RotateCcw size={14} />
              同步退货数据
            </button>
            <button className="px-4 py-1.5 border border-[var(--border-color)] rounded-lg text-xs font-bold text-slate-500 flex items-center gap-2">
              <Download size={14} />
              导出报表
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto custom-scrollbar">
        <table className="erp-table min-w-[1600px]">
          <thead>
            <tr>
              <th className="w-10"><input type="checkbox" className="rounded border-slate-300" /></th>
              <th>订单号</th>
              <th>订购时间</th>
              <th>退货时间</th>
              <th>主图</th>
              <th>SKU</th>
              <th>买家备注</th>
              <th className="text-right">退货量</th>
              <th>发货仓库编号</th>
              <th>库存属性</th>
              <th>退货原因</th>
              <th>退货状态</th>
              <th>LPN编号</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {refunds.map((refund) => (
              <tr key={refund.id}>
                <td className="w-10"><input type="checkbox" className="rounded border-slate-300" /></td>
                <td>
                  <span className="text-brand-600 dark:text-brand-400 font-medium hover:underline cursor-pointer">{refund.id}</span>
                </td>
                <td className="font-mono text-slate-500">{refund.orderTime}</td>
                <td className="font-mono text-slate-500">{refund.refundTime}</td>
                <td>
                  <img src={refund.image} alt="product" className="w-8 h-8 rounded border border-[var(--border-color)]" referrerPolicy="no-referrer" />
                </td>
                <td className="font-bold text-slate-900 dark:text-slate-200">{refund.sku}</td>
                <td className="text-slate-500 max-w-[200px] truncate">{refund.note}</td>
                <td className="text-right font-mono font-bold text-rose-600">{refund.qty}</td>
                <td>
                  <div className="flex items-center gap-1.5 text-slate-600">
                    <Warehouse size={12} className="text-slate-400" />
                    {refund.warehouse}
                  </div>
                </td>
                <td>
                  <span className={cn(
                    "px-2 py-0.5 rounded-full text-[10px] font-bold",
                    refund.inventory === 'Sellable' ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"
                  )}>
                    {refund.inventory}
                  </span>
                </td>
                <td className="text-slate-600">{refund.reason}</td>
                <td>
                  <span className={cn(
                    "px-2 py-0.5 rounded-full text-[10px] font-bold",
                    refund.status === 'Completed' ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                  )}>
                    {refund.status}
                  </span>
                </td>
                <td className="font-mono text-slate-500">{refund.lpn}</td>
                <td>
                  <button className="p-1 text-slate-400 hover:text-slate-600"><MoreHorizontal size={14} /></button>
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
            <span>共 42 条</span>
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

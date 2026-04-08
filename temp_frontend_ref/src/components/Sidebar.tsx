import { 
  LayoutDashboard, 
  MessageSquare, 
  Grid2X2, 
  TrendingUp, 
  Settings, 
  LogOut,
  ShieldCheck,
  Mail,
  ShoppingCart,
  RotateCcw,
  BarChart3,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { useState } from 'react';
import { TabType } from '../types';
import { cn } from '../lib/utils';

interface SidebarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const [expandedMenus, setExpandedMenus] = useState<string[]>(['ads', 'orders']);

  const toggleMenu = (id: string) => {
    setExpandedMenus(prev => 
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    );
  };

  const menuItems = [
    { id: 'dashboard', label: '数据大盘', icon: LayoutDashboard },
    { id: 'message-center', label: '消息中心', icon: Mail },
    { id: 'ai-supervisor', label: 'AI主管', icon: MessageSquare },
    { id: 'more-functions', label: '更多功能', icon: Grid2X2 },
    { 
      id: 'ads', 
      label: '广告系统', 
      icon: TrendingUp,
      subItems: [
        { id: 'ad-dashboard', label: '广告数据大盘' },
        { id: 'ad-management', label: '广告管理系统' },
      ]
    },
    { 
      id: 'orders', 
      label: '订单管理', 
      icon: ShoppingCart,
      subItems: [
        { id: 'all-orders', label: '全部订单' },
        { id: 'refund-orders', label: '退货订单' },
      ]
    },
    { id: 'system-management', label: '系统管理', icon: Settings },
  ];

  return (
    <div className="w-64 h-screen bg-[var(--bg-card)] border-r border-[var(--border-color)] flex flex-col sticky top-0 z-40">
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
          <ShieldCheck size={24} />
        </div>
        <div>
          <h2 className="font-bold text-[var(--text-main)] leading-tight">亚马逊AI运营</h2>
          <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Automation System</p>
        </div>
      </div>

      <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto custom-scrollbar">
        {menuItems.map((item) => (
          <div key={item.id}>
            {item.subItems ? (
              <>
                <button
                  onClick={() => toggleMenu(item.id)}
                  className={cn(
                    "w-full flex items-center justify-between px-4 py-2.5 rounded-xl transition-all duration-200 group text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-[var(--text-main)]",
                    expandedMenus.includes(item.id) && "text-[var(--text-main)]"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <item.icon size={18} className="text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300" />
                    <span className="text-sm font-medium">{item.label}</span>
                  </div>
                  {expandedMenus.includes(item.id) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
                {expandedMenus.includes(item.id) && (
                  <div className="mt-1 ml-9 space-y-1">
                    {item.subItems.map(sub => (
                      <button
                        key={sub.id}
                        onClick={() => setActiveTab(sub.id as TabType)}
                        className={cn(
                          "w-full text-left px-4 py-2 rounded-lg text-xs transition-all",
                          activeTab === sub.id 
                            ? "bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 font-semibold" 
                            : "text-slate-500 hover:text-[var(--text-main)] hover:bg-slate-50 dark:hover:bg-slate-800/50"
                        )}
                      >
                        {sub.label}
                      </button>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <button
                onClick={() => setActiveTab(item.id as TabType)}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 group",
                  activeTab === item.id 
                    ? "bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 font-semibold" 
                    : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-[var(--text-main)]"
                )}
              >
                <item.icon size={18} className={cn(
                  "transition-colors",
                  activeTab === item.id ? "text-brand-600 dark:text-brand-400" : "text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300"
                )} />
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            )}
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-[var(--border-color)]">
        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-2xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center text-brand-600 dark:text-brand-400">
            <BarChart3 size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-[var(--text-main)] truncate">Siqiang Business</p>
            <p className="text-[10px] text-slate-500 truncate">siqiangshangwu.com</p>
          </div>
        </div>
      </div>
    </div>
  );
}

import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard, Bot, BarChart3, Target,
  ShoppingCart, RotateCcw, MessageSquare,
  CheckCircle, Settings, DollarSign, ChevronLeft, ChevronRight
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (c: boolean) => void;
}

export default function Sidebar({ collapsed, setCollapsed }: SidebarProps) {
  const { role } = useAuth();

  const navItems = [
    { path: '/', label: '数据大盘', icon: LayoutDashboard },
    { path: '/agents', label: 'AI主管', icon: Bot },
    { path: '/ads', label: '广告数据大盘', icon: BarChart3 },
    { path: '/ads/manage', label: '广告管理', icon: Target },
    { path: '/orders', label: '全部订单', icon: ShoppingCart },
    { path: '/refunds', label: '退货订单', icon: RotateCcw },
    { path: '/messages', label: '消息中心', icon: MessageSquare },
    { path: '/approvals', label: '审批中心', icon: CheckCircle },
  ];

  if (role === 'boss') {
    navItems.push({ path: '/system', label: '系统管理', icon: Settings });
    navItems.push({ path: '/system/costs', label: '费用监控', icon: DollarSign });
  }

  return (
    <aside className={`relative transition-all duration-300 flex flex-col glass border-r border-y-0 border-l-0 ${collapsed ? 'w-16' : 'w-64'} h-full shrink-0 z-20`}>
      <div className="flex items-center justify-center h-16 border-b border-[var(--color-glass-border)] overflow-hidden shrink-0">
        {collapsed ? (
          <span className="text-xl font-bold text-[var(--color-accent)]">P</span>
        ) : (
          <div className="flex flex-col items-center">
            <span className="text-xl font-bold text-white tracking-wider">
              PUDIWIND <span className="text-[var(--color-accent)]">AI</span>
            </span>
            <span className="text-[10px] text-gray-400">Amazon Automation</span>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-4 flex flex-col gap-1 px-2 custom-scrollbar">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `
              flex items-center px-3 py-3 rounded-lg transition-colors
              ${isActive ? 'bg-[var(--color-accent)] text-white' : 'text-gray-400 hover:bg-[var(--color-surface-hover)] hover:text-white'}
              ${collapsed ? 'justify-center' : ''}
            `}
            title={collapsed ? item.label : undefined}
          >
            <item.icon size={20} className="shrink-0" />
            {!collapsed && <span className="ml-3 truncate font-medium">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-2 border-t border-[var(--color-glass-border)] shrink-0">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-lg text-gray-400 hover:text-white hover:bg-[var(--color-surface-hover)] transition-colors"
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>
    </aside>
  );
}

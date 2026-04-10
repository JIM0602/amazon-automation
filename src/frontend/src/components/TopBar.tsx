import { useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Bell, LogOut } from 'lucide-react';

export default function TopBar() {
  const { user, role, logout } = useAuth();
  const location = useLocation();

  const getPageTitle = (path: string) => {
    if (path === '/') return '数据大盘';
    if (path.startsWith('/agents')) return 'AI主管';
    if (path.startsWith('/ads/manage')) return '广告管理';
    if (path.startsWith('/ads')) return '广告数据大盘';
    if (path.startsWith('/orders')) return '全部订单';
    if (path.startsWith('/refunds')) return '退货订单';
    if (path.startsWith('/messages')) return '消息中心';
    if (path.startsWith('/approvals')) return '审批中心';
    if (path.startsWith('/system')) return '系统管理';
    return 'Pudiwind AI';
  };

  return (
    <header className="h-16 shrink-0 glass border-b border-t-0 border-x-0 border-[var(--color-glass-border)] px-6 flex items-center justify-between z-10">
      <div className="text-lg font-medium text-white tracking-wide">
        {getPageTitle(location.pathname)}
      </div>

      <div className="flex items-center space-x-6">
        <button className="relative text-gray-400 hover:text-white transition-colors" title="Notifications">
          <Bell size={20} />
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold h-4 w-4 rounded-full flex items-center justify-center">
            3
          </span>
        </button>

        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-[var(--color-primary)] border border-[var(--color-glass-border)] text-white flex items-center justify-center font-bold">
            {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-white leading-tight">{user?.username || 'User'}</span>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">{role || 'Unknown'}</span>
          </div>
        </div>

        <div className="h-6 w-px bg-[var(--color-glass-border)]"></div>

        <button
          onClick={logout}
          className="flex items-center text-gray-400 hover:text-white transition-colors"
          title="Logout"
        >
          <LogOut size={20} />
        </button>
      </div>
    </header>
  );
}

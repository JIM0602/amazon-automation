import { useState, useEffect, useRef } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { Bell, LogOut, Sun, Moon, CheckCircle, BookOpen, AlertTriangle } from 'lucide-react';
import { useNotifications, Notification } from '../hooks/useNotifications';

// helper for time ago
function timeAgo(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return `${diffInSeconds}秒前`;
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}分钟前`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}小时前`;
  return `${Math.floor(diffInSeconds / 86400)}天前`;
}

export default function TopBar() {
  const { user, role, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const { totalCount, notifications, loading, refresh } = useNotifications();
  const [showPanel, setShowPanel] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        panelRef.current && 
        !panelRef.current.contains(event.target as Node) &&
        bellRef.current &&
        !bellRef.current.contains(event.target as Node)
      ) {
        setShowPanel(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleBellClick = () => {
    if (!showPanel) {
      refresh();
    }
    setShowPanel(!showPanel);
  };

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

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'approval': return <CheckCircle size={16} className="text-green-500" />;
      case 'kb_review': return <BookOpen size={16} className="text-blue-500" />;
      case 'agent_failure': return <AlertTriangle size={16} className="text-red-500" />;
      default: return <Bell size={16} className="text-gray-500" />;
    }
  };

  return (
    <header className="h-16 shrink-0 glass border-b border-t-0 border-x-0 border-[var(--color-glass-border)] px-6 flex items-center justify-between z-10">
      <div className="text-lg font-medium text-white tracking-wide">
        {getPageTitle(location.pathname)}
      </div>

      <div className="flex items-center space-x-6">
        <button 
          onClick={toggleTheme}
          className="relative text-gray-400 hover:text-white transition-colors" 
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>

        <div className="relative flex items-center">
          <button 
            ref={bellRef}
            onClick={handleBellClick}
            className="relative text-gray-400 hover:text-white transition-colors flex items-center justify-center" 
            title="Notifications"
          >
            <Bell size={20} />
            {totalCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold h-4 w-4 rounded-full flex items-center justify-center">
                {totalCount > 99 ? '99+' : totalCount}
              </span>
            )}
          </button>

          {showPanel && (
            <div 
              ref={panelRef}
              className="absolute right-0 top-full mt-4 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 overflow-hidden flex flex-col"
            >
              <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800/50">
                <span className="font-semibold text-gray-700 dark:text-gray-200">通知</span>
                <span className="text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">
                  共 {totalCount} 条
                </span>
              </div>
              
              <div className="max-h-96 overflow-y-auto">
                {loading ? (
                  <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">加载中...</div>
                ) : notifications.length === 0 ? (
                  <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">暂无通知</div>
                ) : (
                  <ul className="divide-y divide-gray-100 dark:divide-gray-700/50">
                    {notifications.map((notif) => (
                      <li key={notif.id} className={`p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${!notif.is_read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''}`}>
                        <div className="flex gap-3">
                          <div className="mt-0.5 shrink-0">
                            {getNotificationIcon(notif.type)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                              {notif.title}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                              {notif.message}
                            </p>
                            <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1.5">
                              {timeAgo(notif.created_at)}
                            </p>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="p-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-center">
                <Link 
                  to="/approvals" 
                  className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium hover:underline inline-block w-full py-1"
                  onClick={() => setShowPanel(false)}
                >
                  查看全部
                </Link>
              </div>
            </div>
          )}
        </div>

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

import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard, Bot, Grid3x3, BarChart3, Target,
  ShoppingCart, CheckCircle, Settings, ChevronLeft, ChevronRight,
  ChevronDown, ChevronUp, Users, Key, CalendarClock, DollarSign,
  List, RotateCcw
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (c: boolean) => void;
}

export default function Sidebar({ collapsed, setCollapsed }: SidebarProps) {
  const { role } = useAuth();
  const location = useLocation();

  const getInitialExpanded = (id: string, defaultExp: boolean) => {
    const saved = localStorage.getItem(`sidebar-expand-${id}`);
    return saved !== null ? saved === 'true' : defaultExp;
  };

  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const state: Record<string, boolean> = {};
    state['ads_manage'] = getInitialExpanded('ads_manage', false);
    state['system'] = getInitialExpanded('system', false);
    return state;
  });

  const toggleExpand = (id: string) => {
    setExpanded(prev => {
      const next = { ...prev, [id]: !prev[id] };
      localStorage.setItem(`sidebar-expand-${id}`, String(next[id]));
      return next;
    });
  };

  const handleParentClick = (id: string) => {
    if (collapsed) {
      setCollapsed(false);
      setExpanded(prev => {
        const next = { ...prev, [id]: true };
        localStorage.setItem(`sidebar-expand-${id}`, 'true');
        return next;
      });
    } else {
      toggleExpand(id);
    }
  };

  const navConfig = [
    { id: 'dashboard', path: '/', label: '数据大盘', icon: LayoutDashboard },
    { id: 'ai_manager', path: '/agents/core_management', label: 'AI主管', icon: Bot },
    { id: 'more_agents', path: '/agents', label: '更多功能', icon: Grid3x3 },
    { id: 'ads_dashboard', path: '/ads', label: '广告数据大盘', icon: BarChart3 },
    {
      id: 'ads_manage',
      label: '广告管理',
      icon: Target,
      subItems: [
        { path: '/ads/manage', label: '广告列表', icon: List },
        { path: '/ads/agent', label: '广告优化Agent', icon: Bot },
      ]
    },
    { id: 'orders', path: '/orders', label: '全部订单', icon: ShoppingCart },
    { id: 'returns', path: '/returns', label: '退货订单', icon: RotateCcw },
    { id: 'approvals', path: '/approvals', label: '审批中心', icon: CheckCircle },
    ...(role === 'boss' ? [{
      id: 'system',
      label: '系统管理',
      icon: Settings,
      subItems: [
        { path: '/system/users', label: '用户管理', icon: Users },
        { path: '/system/agents', label: 'Agent配置', icon: Bot },
        { path: '/system/api-keys', label: 'API密钥', icon: Key },
        { path: '/system/schedules', label: '计划任务', icon: CalendarClock },
        { path: '/system/costs', label: '费用监控', icon: DollarSign },
      ]
    }] : [])
  ];

  const isItemActive = (path?: string) => {
    if (!path) return false;
    return location.pathname === path;
  };

  const isParentActive = (subItems?: {path: string}[]) => {
    if (!subItems) return false;
    return subItems.some(sub => isItemActive(sub.path));
  };

  return (
    <aside className={`relative transition-all duration-300 flex flex-col glass border-r border-y-0 border-l-0 ${collapsed ? 'w-16' : 'w-64'} h-full shrink-0 z-20`}>
      <div className="flex items-center justify-center h-16 border-b border-[var(--color-glass-border)] overflow-hidden shrink-0">
        {collapsed ? (
          <span className="text-xl font-bold text-[var(--color-accent)]">P</span>
        ) : (
          <div className="flex flex-col items-center">
            <span className="text-xl font-bold text-gray-900 dark:text-white tracking-wider">
              PUDIWIND <span className="text-[var(--color-accent)]">AI</span>
            </span>
            <span className="text-[10px] text-gray-500 dark:text-gray-400">Amazon Automation</span>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-4 flex flex-col gap-1 px-2 custom-scrollbar">
        {navConfig.filter(item => item.id !== 'system_config').map((item) => {
          const exactActive = isItemActive(item.path);
          const childActive = isParentActive(item.subItems);
          
          return (
            <div key={item.id} className="flex flex-col">
              {item.path && !item.subItems ? (
                <NavLink
                  to={item.path}
                  className={`
                    flex items-center px-3 py-3 rounded-lg transition-colors
                    ${exactActive ? 'bg-[var(--color-accent)] text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-[var(--color-surface-hover)] hover:text-gray-900 dark:hover:text-white'}
                    ${collapsed ? 'justify-center' : ''}
                  `}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon size={20} className="shrink-0" />
                  {!collapsed && <span className="ml-3 truncate font-medium">{item.label}</span>}
                </NavLink>
              ) : (
                <button
                  onClick={() => handleParentClick(item.id)}
                  className={`
                    flex items-center px-3 py-3 rounded-lg transition-colors w-full
                    ${(childActive && collapsed) ? 'bg-[var(--color-accent)] text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-[var(--color-surface-hover)] hover:text-gray-900 dark:hover:text-white'}
                    ${collapsed ? 'justify-center' : 'justify-between'}
                  `}
                  title={collapsed ? item.label : undefined}
                >
                  <div className="flex items-center overflow-hidden">
                    <item.icon size={20} className="shrink-0" />
                    {!collapsed && <span className="ml-3 truncate font-medium">{item.label}</span>}
                  </div>
                  {!collapsed && (
                    <span className="shrink-0 ml-2">
                      {expanded[item.id] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </span>
                  )}
                </button>
              )}

              {/* Submenus */}
              {!collapsed && item.subItems && expanded[item.id] && (
                <div className="flex flex-col mt-1 ml-4 pl-4 border-l border-[var(--color-glass-border)] gap-1">
                  {item.subItems.map(sub => {
                    const subActive = isItemActive(sub.path);
                    return (
                      <NavLink
                        key={sub.path}
                        to={sub.path}
                        className={`
                          flex items-center px-3 py-2 rounded-lg transition-colors text-sm
                          ${subActive ? 'bg-[var(--color-accent)] text-white font-medium' : 'text-gray-500 dark:text-gray-400 hover:bg-[var(--color-surface-hover)] hover:text-gray-900 dark:hover:text-white'}
                        `}
                      >
                        {sub.icon && <sub.icon size={16} className="shrink-0 mr-3" />}
                        <span className="truncate">{sub.label}</span>
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="p-2 border-t border-[var(--color-glass-border)] shrink-0">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-[var(--color-surface-hover)] transition-colors"
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>
    </aside>
  );
}

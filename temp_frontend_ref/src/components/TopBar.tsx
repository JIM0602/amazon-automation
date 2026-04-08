import { Sun, Moon, Mail, LogOut, User } from 'lucide-react';
import { TabType } from '../types';

interface TopBarProps {
  isDark: boolean;
  toggleTheme: () => void;
  setActiveTab: (tab: TabType) => void;
  onLogout: () => void;
  username: string;
}

export default function TopBar({ isDark, toggleTheme, setActiveTab, onLogout, username }: TopBarProps) {
  return (
    <header className="h-14 bg-[var(--bg-card)] border-b border-[var(--border-color)] flex items-center justify-end px-6 gap-4 sticky top-0 z-30">
      <button
        onClick={toggleTheme}
        className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
        title={isDark ? "切换到浅色模式" : "切换到深色模式"}
      >
        {isDark ? <Sun size={20} /> : <Moon size={20} />}
      </button>

      <button
        onClick={() => setActiveTab('message-center')}
        className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors relative"
        title="消息中心"
      >
        <Mail size={20} />
        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full border-2 border-[var(--bg-card)]" />
      </button>

      <div className="h-6 w-px bg-[var(--border-color)] mx-2" />

      <div className="flex items-center gap-3">
        <div className="flex flex-col items-end">
          <span className="text-sm font-semibold text-[var(--text-main)]">{username}</span>
          <span className="text-[10px] text-slate-500">管理员</span>
        </div>
        <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center text-brand-600 dark:text-brand-400">
          <User size={18} />
        </div>
      </div>

      <button
        onClick={onLogout}
        className="ml-2 p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg transition-all"
        title="退出登录"
      >
        <LogOut size={20} />
      </button>
    </header>
  );
}

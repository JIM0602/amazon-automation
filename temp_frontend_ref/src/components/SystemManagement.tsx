import { 
  Server, 
  Cpu, 
  Database, 
  Activity, 
  UserPlus, 
  FileSearch, 
  Shield,
  RefreshCw,
  CheckCircle2
} from 'lucide-react';
import { motion } from 'motion/react';

const serverStats = [
  { label: 'CPU 使用率', value: '12%', status: 'normal', icon: Cpu },
  { label: '内存占用', value: '1.4GB / 4GB', status: 'normal', icon: Activity },
  { label: '数据库延迟', value: '24ms', status: 'excellent', icon: Database },
  { label: '系统运行时间', value: '14天 6小时', status: 'normal', icon: Server },
];

const logs = [
  { id: 1, time: '2026-04-03 07:45:12', user: 'Admin', action: '登录系统', ip: '183.14.22.105' },
  { id: 2, time: '2026-04-03 07:30:05', user: 'System', action: '自动同步店铺数据', ip: 'Local' },
  { id: 3, time: '2026-04-03 07:15:44', user: 'Operator_A', action: '修改广告预算 (ASIN: B08X...)', ip: '112.95.1.44' },
  { id: 4, time: '2026-04-03 06:50:21', user: 'Admin', action: '创建新账号: Operator_C', ip: '183.14.22.105' },
];

export default function SystemManagement() {
  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">系统管理</h1>
          <p className="text-slate-500">监控服务器状态及管理访问权限</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors shadow-sm">
          <RefreshCw size={16} />
          刷新状态
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {serverStats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-slate-50 text-slate-600 rounded-lg">
                <stat.icon size={20} />
              </div>
              <span className="text-sm font-medium text-slate-500">{stat.label}</span>
            </div>
            <div className="flex items-end justify-between">
              <span className="text-2xl font-bold text-slate-900">{stat.value}</span>
              <div className="flex items-center gap-1 text-emerald-600 text-xs font-bold">
                <CheckCircle2 size={14} />
                运行正常
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 flex items-center gap-2">
                <FileSearch size={20} className="text-slate-400" />
                系统操作日志
              </h3>
              <button className="text-sm text-brand-600 font-semibold hover:underline">查看全部</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50">
                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">时间</th>
                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">操作人</th>
                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">动作</th>
                    <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">IP地址</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {logs.map((log) => (
                    <tr key={log.id} className="text-sm hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 font-mono text-slate-500">{log.time}</td>
                      <td className="px-6 py-4 font-medium text-slate-900">{log.user}</td>
                      <td className="px-6 py-4 text-slate-600">{log.action}</td>
                      <td className="px-6 py-4 text-slate-400">{log.ip}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-900 mb-6 flex items-center gap-2">
              <Shield size={20} className="text-slate-400" />
              权限管理
            </h3>
            <div className="space-y-4">
              <button className="w-full flex items-center justify-between p-4 bg-brand-50 text-brand-600 rounded-2xl hover:bg-brand-100 transition-all group">
                <div className="flex items-center gap-3">
                  <UserPlus size={20} />
                  <span className="font-bold">创建子账号</span>
                </div>
                <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </button>
              <button className="w-full flex items-center justify-between p-4 border border-slate-200 text-slate-600 rounded-2xl hover:bg-slate-50 transition-all group">
                <div className="flex items-center gap-3">
                  <Shield size={20} />
                  <span className="font-bold">修改安全策略</span>
                </div>
                <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>

          <div className="bg-slate-900 p-6 rounded-3xl text-white relative overflow-hidden">
            <div className="relative z-10">
              <h3 className="font-bold mb-2">系统版本</h3>
              <p className="text-slate-400 text-sm mb-4">v2.4.0-stable</p>
              <div className="flex items-center gap-2 text-xs text-emerald-400 font-bold">
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                已是最新版本
              </div>
            </div>
            <Server size={80} className="text-white/5 absolute -right-4 -bottom-4 rotate-12" />
          </div>
        </div>
      </div>
    </div>
  );
}

function ChevronRight({ size, className }: { size: number, className?: string }) {
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
      <path d="m9 18 6-6-6-6"/>
    </svg>
  );
}

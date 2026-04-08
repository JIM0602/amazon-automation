import { useState } from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { 
  TrendingUp, 
  ShoppingBag, 
  ClipboardList, 
  DollarSign, 
  Percent,
  Calendar
} from 'lucide-react';
import { motion } from 'motion/react';

const data = [
  { name: '04-01', sales: 4000, orders: 240, spend: 1200 },
  { name: '04-02', sales: 3000, orders: 198, spend: 1100 },
  { name: '04-03', sales: 2000, orders: 150, spend: 900 },
  { name: '04-04', sales: 2780, orders: 210, spend: 1050 },
  { name: '04-05', sales: 1890, orders: 140, spend: 850 },
  { name: '04-06', sales: 2390, orders: 180, spend: 950 },
  { name: '04-07', sales: 3490, orders: 260, spend: 1150 },
];

const stats = [
  { title: '总销售额', value: '¥24,590', change: 12.5, icon: DollarSign, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  { title: '总销量', value: '1,284', change: 8.2, icon: ShoppingBag, color: 'text-blue-600', bg: 'bg-blue-50' },
  { title: '订单量', value: '856', change: -2.4, icon: ClipboardList, color: 'text-purple-600', bg: 'bg-purple-50' },
  { title: '广告花费', value: '¥4,200', change: 15.1, icon: TrendingUp, color: 'text-orange-600', bg: 'bg-orange-50' },
  { title: 'ACOS', value: '17.1%', change: -1.2, icon: Percent, color: 'text-rose-600', bg: 'bg-rose-50' },
];

export default function Dashboard() {
  const [timeRange, setTimeRange] = useState('7d');

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">数据概览</h1>
          <p className="text-slate-500">实时监控店铺核心运营指标</p>
        </div>
        <div className="flex bg-white border border-slate-200 rounded-xl p-1 shadow-sm">
          {['24h', '7d', '30d', '90d'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                timeRange === range 
                  ? 'bg-slate-900 text-white shadow-md' 
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-2 rounded-xl ${stat.bg} ${stat.color}`}>
                <stat.icon size={20} />
              </div>
              <span className={`text-xs font-bold px-2 py-1 rounded-full ${
                stat.change >= 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
              }`}>
                {stat.change >= 0 ? '+' : ''}{stat.change}%
              </span>
            </div>
            <h3 className="text-slate-500 text-sm font-medium">{stat.title}</h3>
            <p className="text-2xl font-bold text-slate-900 mt-1">{stat.value}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-slate-900">销售趋势</h3>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Calendar size={14} />
              <span>最近7天数据</span>
            </div>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#64748b'}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#64748b'}} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Area type="monotone" dataKey="sales" stroke="#0ea5e9" strokeWidth={2} fillOpacity={1} fill="url(#colorSales)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-slate-900">广告花费 vs 订单量</h3>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Calendar size={14} />
              <span>最近7天对比</span>
            </div>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#64748b'}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#64748b'}} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Line type="monotone" dataKey="spend" stroke="#f59e0b" strokeWidth={2} dot={{r: 4}} activeDot={{r: 6}} />
                <Line type="monotone" dataKey="orders" stroke="#8b5cf6" strokeWidth={2} dot={{r: 4}} activeDot={{r: 6}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

import { motion } from 'motion/react';
import { 
  Search, Target, PackageSearch, FileText, ArrowRight, Zap, BarChart3, 
  Users, LayoutGrid, Image as ImageIcon, Upload, ShieldCheck
} from 'lucide-react';
import { TabType, Agent } from '../types';

export const agents: Agent[] = [
  { 
    id: 'brand-path', 
    name: '品牌路径规划Agent', 
    description: '规划品牌成长路线，从0到1构建品牌影响力。', 
    icon: Target, 
    color: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
    tags: ['品牌建设', '长期规划']
  },
  { 
    id: 'selection', 
    name: '选品Agent', 
    description: '基于大数据算法推荐高潜力、低竞争的爆款产品。', 
    icon: PackageSearch, 
    color: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400',
    tags: ['大数据', '爆款挖掘']
  },
  { 
    id: 'whitepaper', 
    name: '产品白皮书生成Agent', 
    description: '一键生成专业的产品说明、卖点分析及白皮书。', 
    icon: FileText, 
    color: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400',
    tags: ['内容创作', '卖点提炼']
  },
  { 
    id: 'competitor', 
    name: '竞品调研Agent', 
    description: '深度分析类目趋势、竞争对手动态及市场容量。', 
    icon: Search, 
    color: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
    tags: ['趋势分析', '竞品监控']
  },
  { 
    id: 'user-persona', 
    name: '用户画像分析Agent', 
    description: '分析VOC（客户之声），提取痛点进行产品改良。', 
    icon: Users, 
    color: 'bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400',
    tags: ['VOC', '产品改良']
  },
  { 
    id: 'listing-plan', 
    name: '产品listing规划Agent', 
    description: '挖掘高转化长尾词，优化Listing埋词策略。', 
    icon: LayoutGrid, 
    color: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400',
    tags: ['SEO', '流量优化']
  },
  { 
    id: 'listing-image', 
    name: '产品listing图片生成Agent', 
    description: 'AI生成高质量产品主图、场景图及A+页面素材。', 
    icon: ImageIcon, 
    color: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400',
    tags: ['视觉设计', 'AI生图']
  },
  { 
    id: 'listing-upload', 
    name: '产品上架及调整Agent', 
    description: '自动化批量上架产品，并根据反馈实时调整Listing。', 
    icon: Upload, 
    color: 'bg-cyan-50 dark:bg-cyan-900/20 text-cyan-600 dark:text-cyan-400',
    tags: ['自动化', '上架优化']
  },
  { 
    id: 'monitoring', 
    name: '产品监控及发货Agent', 
    description: '实时监控库存状态，智能预测补货并管理FBA发货。', 
    icon: ShieldCheck, 
    color: 'bg-slate-50 dark:bg-slate-900/20 text-slate-600 dark:text-slate-400',
    tags: ['库存管理', 'FBA补货']
  },
];

interface MoreFunctionsProps {
  onSelectAgent: (agent: Agent) => void;
}

export default function MoreFunctions({ onSelectAgent }: MoreFunctionsProps) {
  return (
    <div className="p-8 space-y-8 overflow-y-auto h-full custom-scrollbar">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-main)]">AI Agent 矩阵</h1>
        <p className="text-slate-500">多维度AI助手，全方位赋能亚马逊运营流程</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent, i) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ y: -5 }}
            onClick={() => onSelectAgent(agent)}
            className="group bg-[var(--bg-card)] p-6 rounded-3xl border border-[var(--border-color)] shadow-sm hover:shadow-xl hover:border-brand-200 transition-all cursor-pointer"
          >
            <div className="flex items-start justify-between mb-6">
              <div className={`p-3 rounded-2xl ${agent.color}`}>
                <agent.icon size={24} />
              </div>
              <div className="flex gap-1">
                {agent.tags.map(tag => (
                  <span key={tag} className="text-[10px] font-bold px-2 py-1 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-full uppercase tracking-wider">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            
            <h3 className="text-lg font-bold text-[var(--text-main)] mb-2 group-hover:text-brand-600 transition-colors">
              {agent.name}
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              {agent.description}
            </p>

            <div className="flex items-center text-brand-600 text-sm font-semibold gap-1 group-hover:gap-2 transition-all">
              立即开启
              <ArrowRight size={16} />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

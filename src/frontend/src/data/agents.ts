import {
  Bot,
  Target,
  PackageSearch,
  Search,
  FileText,
  LayoutGrid,
  Image as ImageIcon,
  Upload,
  ShieldCheck,
  Users,
  Database,
  Eye,
  type LucideIcon,
} from 'lucide-react'
import type { AgentType } from '../types'

export type AgentCategory = '分析' | '内容' | '运营' | '监控'

export interface AgentCardInfo {
  type: AgentType
  name: string
  description: string
  icon: LucideIcon
  category: AgentCategory
  tags: string[]
  bossOnly: boolean
  color: string
  hasFileSidebar: boolean
}

export const AGENTS: AgentCardInfo[] = [
  { type: 'core_management', name: '运营主管Agent', description: '统筹所有运营任务，生成日报周报，制定运营计划。', icon: Bot, category: '运营', tags: ['任务管理', '报告生成'], bossOnly: false, color: 'bg-blue-500/20 text-blue-400', hasFileSidebar: false },
  { type: 'brand_planning', name: '品牌路径规划Agent', description: '规划品牌成长路线，从0到1构建品牌影响力。', icon: Target, category: '分析', tags: ['品牌建设', '长期规划'], bossOnly: true, color: 'bg-purple-500/20 text-purple-400', hasFileSidebar: true },
  { type: 'selection', name: '选品Agent', description: '基于大数据算法推荐高潜力、低竞争的爆款产品。', icon: PackageSearch, category: '分析', tags: ['大数据', '爆款挖掘'], bossOnly: false, color: 'bg-orange-500/20 text-orange-400', hasFileSidebar: false },
  { type: 'competitor', name: '竞品调研Agent', description: '深度分析类目趋势、竞争对手动态及市场容量。', icon: Search, category: '分析', tags: ['趋势分析', '竞品监控'], bossOnly: false, color: 'bg-cyan-500/20 text-cyan-400', hasFileSidebar: true },
  { type: 'whitepaper', name: '产品白皮书Agent', description: '一键生成专业的产品说明、卖点分析及白皮书。', icon: FileText, category: '内容', tags: ['内容创作', '卖点提炼'], bossOnly: false, color: 'bg-emerald-500/20 text-emerald-400', hasFileSidebar: true },
  { type: 'listing', name: 'Listing规划Agent', description: '挖掘高转化长尾词，优化Listing埋词策略。', icon: LayoutGrid, category: '内容', tags: ['SEO', '流量优化'], bossOnly: false, color: 'bg-amber-500/20 text-amber-400', hasFileSidebar: true },
  { type: 'image_generation', name: 'Listing图片Agent', description: 'AI生成高质量产品主图、场景图及A+页面素材。', icon: ImageIcon, category: '内容', tags: ['视觉设计', 'AI生图'], bossOnly: false, color: 'bg-indigo-500/20 text-indigo-400', hasFileSidebar: false },
  { type: 'product_listing', name: '产品上架Agent', description: '自动化批量上架产品，并根据反馈实时调整Listing。', icon: Upload, category: '运营', tags: ['自动化', '上架'], bossOnly: false, color: 'bg-teal-500/20 text-teal-400', hasFileSidebar: false },
  { type: 'inventory', name: '库存监控Agent', description: '实时监控库存状态，智能预测补货并管理FBA发货。', icon: ShieldCheck, category: '运营', tags: ['库存管理', 'FBA补货'], bossOnly: false, color: 'bg-slate-500/20 text-slate-400', hasFileSidebar: true },
  { type: 'persona', name: '用户画像Agent', description: '分析VOC（客户之声），提取痛点进行产品改良。', icon: Users, category: '分析', tags: ['VOC', '产品改良'], bossOnly: false, color: 'bg-pink-500/20 text-pink-400', hasFileSidebar: true },
  { type: 'keyword_library', name: '关键词库Agent', description: '整合多渠道关键词数据，构建产品核心词库。', icon: Database, category: '分析', tags: ['关键词', '数据整合'], bossOnly: false, color: 'bg-violet-500/20 text-violet-400', hasFileSidebar: true },
  { type: 'auditor', name: '审计Agent', description: '审核所有Agent输出质量，确保数据准确性和一致性。', icon: Eye, category: '监控', tags: ['质量审核', '合规'], bossOnly: true, color: 'bg-red-500/20 text-red-400', hasFileSidebar: true },
]

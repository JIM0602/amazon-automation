import { useState, useMemo } from 'react'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { AGENTS } from '../data/agents'
import {
  Search,
  ArrowRight,
  Bot,
} from 'lucide-react'

type Category = '全部' | '分析' | '内容' | '运营' | '监控'

const CATEGORIES: Category[] = ['全部', '分析', '内容', '运营', '监控']

export default function AgentCatalog() {
  const { role } = useAuth()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState<Category>('全部')

  const filteredAgents = useMemo(() => {
    return AGENTS.filter(agent => {
      // 1. RBAC check
      if (agent.bossOnly && role !== 'boss') {
        return false
      }
      
      // 2. Category check
      if (activeCategory !== '全部' && agent.category !== activeCategory) {
        return false
      }

      // 3. Search check
      if (search.trim()) {
        const query = search.toLowerCase()
        if (
          !agent.name.toLowerCase().includes(query) && 
          !agent.description.toLowerCase().includes(query)
        ) {
          return false
        }
      }

      return true
    })
  }, [role, search, activeCategory])

  return (
    <div className="flex-1 p-8 text-gray-900 dark:text-white min-h-full">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight mb-2">更多功能</h1>
          <p className="text-gray-500 dark:text-gray-400 text-lg">除 AI 主管外的其他专业 Agent 入口</p>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div className="flex flex-wrap items-center gap-2">
            {CATEGORIES.map(category => (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  activeCategory === category
                    ? 'bg-[var(--color-accent)] text-white shadow-lg shadow-[var(--color-accent)]/20'
                    : 'bg-gray-100 text-gray-500 hover:text-gray-900 hover:bg-gray-200 border border-gray-200 dark:bg-[rgba(255,255,255,0.05)] dark:text-gray-400 dark:hover:text-white dark:hover:bg-[rgba(255,255,255,0.1)] dark:border-[rgba(255,255,255,0.05)]'
                }`}
              >
                {category}
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-72">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-500" />
            </div>
            <input
              type="text"
              placeholder="搜索 Agent 名称或描述..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-200 bg-white text-gray-700 placeholder-gray-400 dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(0,0,0,0.2)] dark:text-gray-300 dark:placeholder-gray-500 rounded-xl leading-5 focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)] focus:border-[var(--color-accent)] sm:text-sm transition-colors"
            />
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent, index) => {
            const Icon = agent.icon
            return (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
                whileHover={{ y: -4 }}
                key={agent.type}
                onClick={() => navigate(`/agents/${agent.type}`)}
                className="group cursor-pointer bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 dark:bg-[rgba(255,255,255,0.03)] dark:border-[rgba(255,255,255,0.08)] dark:hover:bg-[rgba(255,255,255,0.06)] dark:hover:border-[rgba(255,255,255,0.15)] backdrop-blur-xl rounded-2xl p-6 flex flex-col h-full transition-all duration-300 shadow-lg shadow-gray-200/50 dark:shadow-xl dark:shadow-black/20 relative overflow-hidden"
              >
                {/* Glossy gradient accent */}
                <div className="absolute -inset-x-2 -top-2 h-1/2 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-500" />
                
                <div className="flex items-start justify-between mb-4 relative z-10">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${agent.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 border border-gray-200 dark:bg-[rgba(255,255,255,0.05)] dark:text-gray-400 dark:border-[rgba(255,255,255,0.1)]">
                    {agent.category}
                  </span>
                </div>
                
                <div className="relative z-10 flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-[var(--color-accent)] transition-colors">
                    {agent.name}
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-6 line-clamp-3">
                    {agent.description}
                  </p>
                </div>
                
                <div className="mt-auto relative z-10">
                  <div className="flex flex-wrap gap-2 mb-6">
                    {agent.tags.map(tag => (
                      <span 
                        key={tag}
                        className="text-xs px-2 py-1 bg-gray-100 text-gray-600 border border-gray-200 dark:bg-black/30 dark:text-gray-300 dark:border-white/5 rounded-md"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  
                  <div className="flex items-center text-sm font-medium text-gray-500 dark:text-gray-400 group-hover:text-[var(--color-accent)] transition-colors">
                    <span>开始对话</span>
                    <ArrowRight className="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
        
        {filteredAgents.length === 0 && (
          <div className="text-center py-20 bg-gray-50 border border-gray-200 dark:bg-[rgba(255,255,255,0.02)] dark:border-[rgba(255,255,255,0.05)] rounded-2xl backdrop-blur-sm">
            <Bot className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300">没有找到匹配的 Agent</h3>
            <p className="text-gray-500 mt-1">请尝试更换搜索词或分类</p>
          </div>
        )}
      </div>
    </div>
  )
}

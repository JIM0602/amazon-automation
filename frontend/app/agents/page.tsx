"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface AgentParam {
  key: string;
  label: string;
  placeholder: string;
  required: boolean;
}

interface AgentDef {
  type: string;
  name: string;
  description: string;
  icon: string;
  params: AgentParam[];
}

const AGENTS: AgentDef[] = [
  {
    type: "selection",
    name: "选品分析 Agent",
    description: "分析亚马逊品类数据，筛选潜力产品",
    icon: "🔍",
    params: [
      { key: "category", label: "品类", placeholder: "pet_supplies", required: true },
      { key: "subcategory", label: "子品类", placeholder: "可选", required: false },
    ],
  },
  {
    type: "listing",
    name: "Listing 优化 Agent",
    description: "优化产品标题、描述、关键词",
    icon: "📝",
    params: [
      { key: "asin", label: "ASIN", placeholder: "B0XXXXXXXXX", required: true },
      { key: "product_name", label: "产品名称", placeholder: "产品名称", required: true },
      { key: "category", label: "品类", placeholder: "pet_supplies", required: true },
    ],
  },
  {
    type: "competitor",
    name: "竞品监控 Agent",
    description: "追踪竞争对手价格、排名、评论变化",
    icon: "📊",
    params: [
      { key: "target_asin", label: "目标ASIN", placeholder: "B0XXXXXXXXX", required: true },
      { key: "competitor_asins", label: "竞品ASIN(逗号分隔)", placeholder: "B0XXX,B0YYY", required: false },
    ],
  },
  {
    type: "persona",
    name: "用户画像 Agent",
    description: "分析目标用户群体特征和购买行为",
    icon: "👤",
    params: [
      { key: "category", label: "品类", placeholder: "pet_supplies", required: true },
      { key: "asin", label: "ASIN", placeholder: "B0XXXXXXXXX", required: false },
    ],
  },
  {
    type: "ad_monitor",
    name: "广告监控 Agent",
    description: "监控广告投放效果和预算消耗",
    icon: "📢",
    params: [],
  },
];

interface AgentRunStatus {
  run_id: string;
  agent_type: string;
  status: string;
  input_summary: string | null;
  output_summary: string | null;
  cost_usd: number | null;
  started_at: string;
  finished_at: string | null;
}

interface AgentRunList {
  runs: AgentRunStatus[];
  total: number;
}

interface AgentRunResponse {
  run_id: string;
  agent_type: string;
  status: string;
  message: string;
}

function AgentCard({ agent }: { agent: AgentDef }) {
  const [expanded, setExpanded] = useState(false);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [dryRun, setDryRun] = useState(true);
  const queryClient = useQueryClient();

  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const { data: runStatus, isFetching: isPolling } = useQuery<AgentRunStatus>({
    queryKey: ["agentRun", activeRunId],
    queryFn: () => apiFetch<AgentRunStatus>(`/api/agents/runs/${activeRunId}`),
    enabled: !!activeRunId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "pending" ? 3000 : false;
    },
  });

  const mutation = useMutation({
    mutationFn: async (payload: { dry_run: boolean; params: Record<string, any> }) => {
      return apiFetch<AgentRunResponse>(`/api/agents/${agent.type}/run`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: (data) => {
      setActiveRunId(data.run_id);
      queryClient.invalidateQueries({ queryKey: ["agentRunsList"] });
    },
    onError: (error) => {
      alert(`运行失败: ${error instanceof Error ? error.message : "未知错误"}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const processedParams: Record<string, string | string[]> = { ...formData };
    
    if (agent.type === "competitor" && typeof processedParams.competitor_asins === "string") {
      processedParams.competitor_asins = processedParams.competitor_asins
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }

    mutation.mutate({ dry_run: dryRun, params: processedParams });
  };

  const isRunning = mutation.isPending || (runStatus && (runStatus.status === "running" || runStatus.status === "pending"));

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex flex-col gap-4 shadow-lg">
      <div className="flex items-start justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          <div className="text-3xl bg-gray-700/50 p-2 rounded-lg">{agent.icon}</div>
          <div>
            <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
            <p className="text-sm text-gray-400">{agent.description}</p>
          </div>
        </div>
        <button className="text-gray-400 hover:text-white">
          {expanded ? "▲" : "▼"}
        </button>
      </div>

      {expanded && (
        <div className="mt-2 border-t border-gray-700 pt-4">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {agent.params.map((param) => (
              <div key={param.key} className="flex flex-col gap-1">
                <label className="text-sm text-gray-300">
                  {param.label} {param.required && <span className="text-red-500">*</span>}
                </label>
                <input
                  type="text"
                  placeholder={param.placeholder}
                  required={param.required}
                  value={formData[param.key] || ""}
                  onChange={(e) => setFormData({ ...formData, [param.key]: e.target.value })}
                  className="bg-gray-900 border border-gray-700 rounded-md p-2 text-sm text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  disabled={!!isRunning}
                />
              </div>
            ))}
            
            <div className="flex items-center gap-2 mt-2">
              <input
                type="checkbox"
                id={`dry_run_${agent.type}`}
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                disabled={!!isRunning}
                className="w-4 h-4 bg-gray-900 border-gray-700 rounded text-blue-500 focus:ring-blue-500"
              />
              <label htmlFor={`dry_run_${agent.type}`} className="text-sm text-gray-300 select-none">
                Dry Run (模拟运行)
              </label>
            </div>

            <button
              type="submit"
              disabled={!!isRunning}
              className={`mt-2 py-2 px-4 rounded-md font-medium text-sm transition-colors ${
                isRunning
                  ? "bg-gray-700 text-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              {isRunning ? "运行中..." : "运行"}
            </button>
          </form>

          {activeRunId && runStatus && (
            <div className="mt-4 p-3 rounded-md bg-gray-900 border border-gray-700 text-sm">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-gray-400">状态:</span>
                {runStatus.status === "running" || runStatus.status === "pending" ? (
                  <span className="flex items-center gap-1 text-blue-400">
                    <svg className="animate-spin h-4 w-4 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    运行中...
                  </span>
                ) : runStatus.status === "success" || runStatus.status === "completed" ? (
                  <span className="text-green-500 font-medium bg-green-500/10 px-2 py-0.5 rounded">完成</span>
                ) : (
                  <span className="text-red-500 font-medium bg-red-500/10 px-2 py-0.5 rounded">失败</span>
                )}
              </div>
              <div className="text-gray-400 text-xs mt-1">
                ID: {activeRunId}
              </div>
              {runStatus.finished_at && (
                <div className="text-gray-400 text-xs mt-1">
                  完成时间: {new Date(runStatus.finished_at).toLocaleString()}
                </div>
              )}
              {runStatus.status === "failed" && runStatus.output_summary && (
                <div className="text-red-400 text-xs mt-1">
                  错误信息: {runStatus.output_summary}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AgentsPage() {
  const { user } = useAuth();
  
  const { data: recentRuns } = useQuery<AgentRunList>({
    queryKey: ["agentRunsList"],
    queryFn: () => apiFetch<AgentRunList>("/api/agents/runs?limit=20"),
    refetchInterval: (query) => {
      const runs = query.state.data?.runs || [];
      const hasRunning = runs.some((r: AgentRunStatus) => r.status === "running" || r.status === "pending");
      return hasRunning ? 10000 : 30000;
    },
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">Agent 管理</h1>
        <p className="text-gray-400">配置并运行您的亚马逊自动化智能体</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {AGENTS.map((agent) => (
          <AgentCard key={agent.type} agent={agent} />
        ))}
      </div>

      <div className="mt-12 bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-lg">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">最近运行记录</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-400">
            <thead className="bg-gray-900/50 text-gray-300">
              <tr>
                <th className="px-4 py-3 font-medium">运行ID</th>
                <th className="px-4 py-3 font-medium">Agent类型</th>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">开始时间</th>
                <th className="px-4 py-3 font-medium">花费</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {(!recentRuns || recentRuns.runs.length === 0) ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    暂无运行记录
                  </td>
                </tr>
              ) : (
                recentRuns.runs.map((run) => (
                  <tr key={run.run_id} className="hover:bg-gray-700/30">
                    <td className="px-4 py-3 font-mono text-xs">{run.run_id.slice(0, 8)}...</td>
                    <td className="px-4 py-3">{AGENTS.find(a => a.type === run.agent_type)?.name || run.agent_type}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        run.status === "success" || run.status === "completed" ? "bg-green-500/10 text-green-500" :
                        run.status === "running" || run.status === "pending" ? "bg-blue-500/10 text-blue-400" :
                        "bg-red-500/10 text-red-500"
                      }`}>
                        {run.status === "success" || run.status === "completed" ? "完成" :
                         run.status === "running" || run.status === "pending" ? "运行中" : "失败"}
                      </span>
                    </td>
                    <td className="px-4 py-3">{new Date(run.started_at).toLocaleString()}</td>
                    <td className="px-4 py-3">{run.cost_usd ? `$${run.cost_usd.toFixed(4)}` : "-"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

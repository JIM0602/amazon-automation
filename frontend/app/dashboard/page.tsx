"use client";

import React from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface SystemStatus {
  stopped: boolean;
  reason: string;
  triggered_by: string;
  activated_at: string;
}

interface AgentRunStatus {
  run_id: string;
  agent_type: string;
  status: string; // "running" | "success" | "failed"
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

export default function DashboardPage() {
  const { user } = useAuth();

  const { 
    data: systemStatus, 
    isLoading: isLoadingStatus, 
    isError: isErrorStatus 
  } = useQuery({
    queryKey: ["systemStatus"],
    queryFn: () => apiFetch<SystemStatus>("/api/system/status"),
    refetchInterval: 30000,
  });

  const { 
    data: runsData, 
    isLoading: isLoadingRuns, 
    isError: isErrorRuns 
  } = useQuery({
    queryKey: ["agentRuns"],
    queryFn: () => apiFetch<AgentRunList>("/api/agents/runs?limit=5"),
    refetchInterval: 30000,
  });

  const totalRuns = runsData?.total || 0;
  const runningCount = runsData?.runs.filter(r => r.status === "running").length || 0;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("zh-CN");
  };

  const getDuration = (start: string, end: string | null) => {
    if (!end) return "运行中";
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return <span className="px-2 py-1 text-xs rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">运行中</span>;
      case "success":
        return <span className="px-2 py-1 text-xs rounded-full bg-green-500/20 text-green-400 border border-green-500/30">成功</span>;
      case "failed":
        return <span className="px-2 py-1 text-xs rounded-full bg-red-500/20 text-red-400 border border-red-500/30">失败</span>;
      default:
        return <span className="px-2 py-1 text-xs rounded-full bg-gray-500/20 text-gray-400 border border-gray-500/30">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            欢迎回来, {user?.username || "..."}
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            {user?.role === "boss" ? "管理员 (Boss)" : "操作员 (Operator)"}
          </p>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* System Status */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-medium text-gray-400 mb-2">系统状态</h2>
          {isLoadingStatus ? (
            <div className="h-8 flex items-center">
              <div className="animate-pulse bg-gray-800 h-6 w-24 rounded"></div>
            </div>
          ) : isErrorStatus ? (
            <div className="text-red-400 text-sm">无法加载状态</div>
          ) : (
            <div className="flex items-center mt-2">
              <div className={`w-3 h-3 rounded-full mr-3 ${systemStatus?.stopped ? 'bg-red-500' : 'bg-green-500'}`}></div>
              <span className={`text-xl font-semibold ${systemStatus?.stopped ? 'text-red-400' : 'text-green-400'}`}>
                {systemStatus?.stopped ? '已停机' : '运行中'}
              </span>
            </div>
          )}
          {systemStatus?.stopped && (
            <p className="text-xs text-red-400/80 mt-2 line-clamp-1" title={systemStatus.reason}>
              原因: {systemStatus.reason}
            </p>
          )}
        </div>

        {/* Total Runs */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-medium text-gray-400 mb-2">总任务数</h2>
          {isLoadingRuns ? (
            <div className="h-8 flex items-center">
              <div className="animate-pulse bg-gray-800 h-6 w-16 rounded"></div>
            </div>
          ) : (
            <div className="text-2xl font-semibold text-white mt-1">{totalRuns}</div>
          )}
        </div>

        {/* Running Agents */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-medium text-gray-400 mb-2">正在运行</h2>
          {isLoadingRuns ? (
            <div className="h-8 flex items-center">
              <div className="animate-pulse bg-gray-800 h-6 w-16 rounded"></div>
            </div>
          ) : (
            <div className="text-2xl font-semibold text-blue-400 mt-1">{runningCount}</div>
          )}
        </div>
      </div>

      {/* Recent Runs List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-800">
          <h2 className="text-lg font-medium text-white">近期 Agent 运行记录</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-950/50 text-gray-400 text-sm">
                <th className="px-6 py-3 font-medium">Agent 类型</th>
                <th className="px-6 py-3 font-medium">状态</th>
                <th className="px-6 py-3 font-medium">开始时间</th>
                <th className="px-6 py-3 font-medium text-right">耗时</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {isLoadingRuns ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-6 py-4"><div className="animate-pulse bg-gray-800 h-4 w-24 rounded"></div></td>
                    <td className="px-6 py-4"><div className="animate-pulse bg-gray-800 h-5 w-16 rounded-full"></div></td>
                    <td className="px-6 py-4"><div className="animate-pulse bg-gray-800 h-4 w-32 rounded"></div></td>
                    <td className="px-6 py-4"><div className="animate-pulse bg-gray-800 h-4 w-12 rounded ml-auto"></div></td>
                  </tr>
                ))
              ) : isErrorRuns ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-red-400 text-sm">
                    加载运行记录失败
                  </td>
                </tr>
              ) : runsData?.runs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-500 text-sm">
                    暂无运行记录
                  </td>
                </tr>
              ) : (
                runsData?.runs.map((run) => (
                  <tr key={run.run_id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-200">{run.agent_type}</div>
                      <div className="text-xs text-gray-500 font-mono mt-1" title={run.run_id}>
                        {run.run_id.substring(0, 8)}...
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(run.status)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-400">
                      {formatDate(run.started_at)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-400 text-right font-mono">
                      {getDuration(run.started_at, run.finished_at)}
                    </td>
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

"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface SystemStatus {
  stopped: boolean;
  reason: string;
  triggered_by: string;
  activated_at: string;
}

interface AuditLog {
  timestamp: string;
  action: string;
  actor: string;
  details: string;
  [key: string]: unknown;
}

export default function SystemPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [stopReason, setStopReason] = useState("");
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [showResumeConfirm, setShowResumeConfirm] = useState(false);

  const { data: systemStatus, isLoading: statusLoading } = useQuery<SystemStatus>({
    queryKey: ["systemStatus"],
    queryFn: () => apiFetch<SystemStatus>("/api/system/status"),
    refetchInterval: 15000,
  });

  const { data: auditLogs, isLoading: logsLoading } = useQuery<AuditLog[]>({
    queryKey: ["auditLogs"],
    queryFn: () => apiFetch<AuditLog[]>("/api/system/audit-logs?limit=50"),
  });

  const stopMutation = useMutation({
    mutationFn: async (payload: { reason: string; triggered_by: string }) => {
      return apiFetch("/api/system/stop", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
      queryClient.invalidateQueries({ queryKey: ["auditLogs"] });
      setShowStopConfirm(false);
      setStopReason("");
    },
    onError: (error) => {
      alert(`停机失败: ${error instanceof Error ? error.message : "未知错误"}`);
    },
  });

  const resumeMutation = useMutation({
    mutationFn: async (payload: { triggered_by: string }) => {
      return apiFetch("/api/system/resume", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
      queryClient.invalidateQueries({ queryKey: ["auditLogs"] });
      setShowResumeConfirm(false);
    },
    onError: (error) => {
      alert(`恢复失败: ${error instanceof Error ? error.message : "未知错误"}`);
    },
  });

  if (user?.role !== "boss") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h1 className="text-2xl font-bold text-red-500 mb-2">⚠️ 您没有权限访问此页面</h1>
        <p className="text-gray-400">仅管理员可访问系统管理功能</p>
      </div>
    );
  }

  const isStopped = systemStatus?.stopped;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">系统管理</h1>
        <p className="text-gray-400">系统状态监控与紧急控制台</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-lg">
          <h2 className="text-lg font-semibold text-white mb-4">系统状态</h2>
          
          {statusLoading ? (
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-4 py-1">
                <div className="h-4 bg-gray-700 rounded w-3/4"></div>
                <div className="h-4 bg-gray-700 rounded w-1/2"></div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <div className={`w-4 h-4 rounded-full ${isStopped ? 'bg-red-500 animate-pulse' : 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.7)]'}`}></div>
                <span className={`text-xl font-medium ${isStopped ? 'text-red-400' : 'text-green-400'}`}>
                  {isStopped ? '🔴 系统已停机' : '🟢 系统运行中'}
                </span>
              </div>
              
              {isStopped && systemStatus && (
                <div className="bg-red-900/20 border border-red-900/50 rounded-lg p-4 space-y-2">
                  <div className="text-sm">
                    <span className="text-gray-400">停机原因:</span>
                    <span className="ml-2 text-white">{systemStatus.reason}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-400">执行者:</span>
                    <span className="ml-2 text-white">{systemStatus.triggered_by}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-400">停机时间:</span>
                    <span className="ml-2 text-white">{new Date(systemStatus.activated_at).toLocaleString()}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-lg">
          <h2 className="text-lg font-semibold text-white mb-4">紧急控制</h2>
          
          {statusLoading ? (
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-4 py-1">
                <div className="h-10 bg-gray-700 rounded w-full"></div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {!isStopped ? (
                <div>
                  {!showStopConfirm ? (
                    <button
                      onClick={() => setShowStopConfirm(true)}
                      className="w-full py-3 px-4 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                    >
                      紧急停机
                    </button>
                  ) : (
                    <div className="space-y-3 bg-red-900/10 p-4 border border-red-900/30 rounded-lg">
                      <label className="block text-sm font-medium text-red-400">确认停机原因 (必填)</label>
                      <input
                        type="text"
                        value={stopReason}
                        onChange={(e) => setStopReason(e.target.value)}
                        placeholder="输入停机原因以记录日志..."
                        className="w-full bg-gray-900 border border-red-900/50 rounded-md p-2 text-sm text-white focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            if (!stopReason.trim()) {
                              alert("请输入停机原因");
                              return;
                            }
                            stopMutation.mutate({ reason: stopReason, triggered_by: user.username });
                          }}
                          disabled={stopMutation.isPending || !stopReason.trim()}
                          className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {stopMutation.isPending ? "停机中..." : "确认停机"}
                        </button>
                        <button
                          onClick={() => {
                            setShowStopConfirm(false);
                            setStopReason("");
                          }}
                          disabled={stopMutation.isPending}
                          className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md font-medium transition-colors"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  )}
                  <p className="mt-3 text-xs text-gray-400">警告：此操作将立即停止所有正在运行的自动化任务，并阻止新任务启动。</p>
                </div>
              ) : (
                <div>
                  {!showResumeConfirm ? (
                    <button
                      onClick={() => setShowResumeConfirm(true)}
                      className="w-full py-3 px-4 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
                    >
                      恢复系统
                    </button>
                  ) : (
                    <div className="space-y-3 bg-green-900/10 p-4 border border-green-900/30 rounded-lg">
                      <p className="text-sm font-medium text-green-400">确认要恢复系统运行吗？</p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => resumeMutation.mutate({ triggered_by: user.username })}
                          disabled={resumeMutation.isPending}
                          className="flex-1 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-medium transition-colors disabled:opacity-50"
                        >
                          {resumeMutation.isPending ? "恢复中..." : "确认恢复"}
                        </button>
                        <button
                          onClick={() => setShowResumeConfirm(false)}
                          disabled={resumeMutation.isPending}
                          className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md font-medium transition-colors"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  )}
                  <p className="mt-3 text-xs text-gray-400">恢复系统后，自动化任务将可以正常启动。</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-lg">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">系统审计日志</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-400">
            <thead className="bg-gray-900/50 text-gray-300">
              <tr>
                <th className="px-4 py-3 font-medium">时间</th>
                <th className="px-4 py-3 font-medium">操作</th>
                <th className="px-4 py-3 font-medium">执行者</th>
                <th className="px-4 py-3 font-medium">详情</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {logsLoading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                    <div className="flex justify-center items-center gap-2">
                      <svg className="animate-spin h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      加载日志中...
                    </div>
                  </td>
                </tr>
              ) : !auditLogs || auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                    暂无审计日志
                  </td>
                </tr>
              ) : (
                auditLogs.map((log, i) => (
                  <tr key={i} className="hover:bg-gray-700/30">
                    <td className="px-4 py-3 whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        log.action.includes("stop") ? "bg-red-500/10 text-red-500" :
                        log.action.includes("resume") ? "bg-green-500/10 text-green-500" :
                        "bg-blue-500/10 text-blue-400"
                      }`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3">{log.actor}</td>
                    <td className="px-4 py-3">{log.details}</td>
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

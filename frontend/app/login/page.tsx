"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useSearchParams } from "next/navigation";

function LoginForm() {
  const { login } = useAuth();
  const searchParams = useSearchParams();
  const redirectParams = searchParams.get("redirect");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (errorMsg) setErrorMsg("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username, password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setErrorMsg("请输入用户名和密码");
      return;
    }

    try {
      setLoading(true);
      setErrorMsg("");
      await login(username, password);
    } catch (err: any) {
      setErrorMsg(err.message || "登录失败，请检查用户名和密码");
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      {redirectParams && (
        <div className="p-3 bg-blue-900/30 border border-blue-800/50 rounded-lg text-blue-400 text-sm text-center">
          请先登录
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-red-900/30 border border-red-800/50 rounded-lg text-red-400 text-sm text-center">
          {errorMsg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300" htmlFor="username">
            用户名
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
            className="w-full px-4 py-3 bg-gray-950 border border-gray-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-white placeholder-gray-500 transition-colors"
            placeholder="输入用户名"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300" htmlFor="password">
            密码
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            className="w-full px-4 py-3 bg-gray-950 border border-gray-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-white placeholder-gray-500 transition-colors"
            placeholder="输入密码"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading || !username || !password}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center mt-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              登录中...
            </>
          ) : (
            "登录"
          )}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="px-8 pt-8 pb-6 border-b border-gray-800">
          <h1 className="text-2xl font-bold text-white text-center tracking-tight">
            PUDIWIND <span className="text-blue-500">AI</span>
          </h1>
          <p className="text-gray-400 mt-2 text-sm text-center">
            自动化运营控制台
          </p>
        </div>

        {/* Form Body with Suspense */}
        <Suspense fallback={
          <div className="p-8 flex justify-center">
            <svg className="animate-spin h-8 w-8 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        }>
          <LoginForm />
        </Suspense>

      </div>
    </div>
  );
}

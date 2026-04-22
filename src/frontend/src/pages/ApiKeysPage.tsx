import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, CheckCircle2, Key, RefreshCw } from 'lucide-react';
import api from '../api/client';

type ApiStatus = Record<string, boolean>;

const KEY_ITEMS = [
  { key: 'openai', label: 'OpenAI' },
  { key: 'openrouter', label: 'OpenRouter' },
  { key: 'anthropic', label: 'Anthropic' },
];

const formatTime = (value: string | null) => {
  if (!value) return '未验证';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN');
};

export default function ApiKeysPage() {
  const [status, setStatus] = useState<ApiStatus>({});
  const [lastVerifiedAt, setLastVerifiedAt] = useState<Record<string, string | null>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/system/api-status');
      const data = res.data as ApiStatus;
      setStatus(data);
      const now = new Date().toISOString();
      setLastVerifiedAt(prev => {
        const next = { ...prev };
        KEY_ITEMS.forEach(({ key }) => {
          if (key in data) {
            next[key] = now;
          }
        });
        return next;
      });
    } catch (err: unknown) {
      setError('无法获取 API 密钥状态，请检查权限或服务连接。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadStatus();
  }, []);

  const cards = useMemo(() => KEY_ITEMS.map(item => ({
    ...item,
    configured: Boolean(status[item.key]),
    verifiedAt: lastVerifiedAt[item.key] ?? null,
  })), [status, lastVerifiedAt]);

  return (
    <div className="min-h-full bg-[var(--color-bg)] p-4 sm:p-8 space-y-6 text-gray-900 dark:text-gray-100">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">API 密钥</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">仅展示服务器环境变量中的配置状态，不支持前端修改密钥值</p>
        </div>
        <button
          onClick={() => void loadStatus()}
          disabled={loading}
          className="flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl border border-[var(--color-glass-border)] bg-white/70 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-[var(--color-surface-hover)] disabled:opacity-50 dark:bg-white/5 dark:text-gray-200"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          刷新状态
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl glass border border-rose-500/30 bg-rose-500/10 text-rose-400 flex items-center gap-3">
          <AlertCircle size={20} />
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map(card => (
          <div key={card.key} className="space-y-4 rounded-2xl border border-[var(--color-glass-border)] bg-white/70 p-5 shadow-sm dark:bg-white/5">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 rounded-xl bg-[var(--color-surface)] text-[#3B82F6] shrink-0">
                  <Key size={18} />
                </div>
                <div className="min-w-0">
                  <div className="truncate font-semibold text-gray-900 dark:text-gray-100">{card.label}</div>
                  <div className="truncate text-xs text-gray-500 dark:text-gray-400">{card.key}</div>
                </div>
              </div>

              {card.configured ? (
                <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center gap-1.5 shrink-0">
                  <CheckCircle2 size={14} /> 已配置
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-lg bg-gray-500/10 border border-gray-500/20 text-gray-400 text-xs font-bold flex items-center gap-1.5 shrink-0">
                  <AlertCircle size={14} /> 未配置
                </span>
              )}
            </div>

            <div className="text-sm text-gray-600 dark:text-gray-400">
              最后验证时间：<span className="text-gray-900 dark:text-gray-200">{formatTime(card.verifiedAt)}</span>
            </div>

            <button
              onClick={() => void loadStatus()}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--color-glass-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-[var(--color-surface-hover)] dark:text-gray-200"
            >
              <RefreshCw size={16} />
              验证
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { DataTable } from '../../components/DataTable';
import api from '../../api/client';
import type { Column } from '../../types/table';
import { getListPayload, getObjectPayload } from './detail/detailData';

type TabKey = 'ad_groups' | 'targeting' | 'search_terms' | 'negative_targeting' | 'logs' | 'settings';
type StatusFilterValue = 'all' | 'enabled' | 'paused' | 'archived';
type ActionResult = 'idle' | 'success' | 'error';

interface BaseListRow {
  id: string;
  [key: string]: unknown;
}

interface CampaignInfo extends Record<string, unknown> {
  id: string;
  campaign_name: string;
  status: string;
  ad_type: string;
  daily_budget?: number;
  bidding_strategy?: string;
  start_date?: string;
}

interface ListState<T> {
  data: T[];
  total: number;
  summaryRow?: Partial<T>;
  loading: boolean;
  mockMode: boolean;
}

const TAB_ITEMS: Array<{ key: TabKey; label: string }> = [
  { key: 'ad_groups', label: '广告组' },
  { key: 'targeting', label: '投放' },
  { key: 'search_terms', label: '搜索词' },
  { key: 'negative_targeting', label: '否定投放' },
  { key: 'logs', label: '广告日志' },
  { key: 'settings', label: '活动设置' },
];

const statusMeta: Record<string, { label: string; className: string }> = {
  enabled: { label: '启用', className: 'bg-green-500/20 text-green-400' },
  paused: { label: '暂停', className: 'bg-yellow-500/20 text-yellow-400' },
  archived: { label: '已归档', className: 'bg-gray-500/20 text-gray-400' },
};

const adTypeMeta: Record<string, { label: string; className: string }> = {
  SP: { label: 'SP', className: 'bg-blue-500/20 text-blue-400 border border-blue-500/30' },
  SB: { label: 'SB', className: 'bg-purple-500/20 text-purple-400 border border-purple-500/30' },
  SD: { label: 'SD', className: 'bg-orange-500/20 text-orange-400 border border-orange-500/30' },
};

function formatNumber(value: number | undefined) {
  return value?.toLocaleString('en-US') ?? '0';
}

function formatCurrency(value: number | undefined) {
  return `$${(value ?? 0).toFixed(2)}`;
}

function formatPercent(value: number | undefined) {
  return `${(((value ?? 0) * 100)).toFixed(2)}%`;
}

function StatusBadge({ status }: { status: string }) {
  const meta = statusMeta[status] ?? { label: status || '-', className: 'bg-gray-500/20 text-gray-400' };
  return <span className={`rounded px-2 py-0.5 text-xs ${meta.className}`}>{meta.label}</span>;
}

function AdTypeBadge({ adType }: { adType: string }) {
  const meta = adTypeMeta[adType] ?? { label: adType || '-', className: 'bg-gray-500/20 text-gray-400 border border-gray-500/30' };
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${meta.className}`}>{meta.label}</span>;
}

function TabButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`border-b-2 px-1 py-3 text-sm font-medium transition-colors ${
        active
          ? 'border-blue-500 text-blue-500'
          : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
      }`}
    >
      {label}
    </button>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="text-xs uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">{label}</div>
      <div className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-100">{value}</div>
    </div>
  );
}

interface CampaignSettingsFormProps {
  campaign: CampaignInfo | null;
  budgetValue: string;
  saving: boolean;
  feedbackMessage: string | null;
  feedbackResult: ActionResult;
  onBudgetChange: (value: string) => void;
  onSave: () => void | Promise<void>;
}

function CampaignSettingsForm({
  campaign,
  budgetValue,
  saving,
  feedbackMessage,
  feedbackResult,
  onBudgetChange,
  onSave,
}: CampaignSettingsFormProps) {
  return (
    <div className="grid gap-4 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900 md:grid-cols-2">
      <ReadOnlyField label="活动名称" value={campaign?.campaign_name || '-'} />
      <div className="space-y-1">
        <div className="text-xs text-gray-500 dark:text-gray-400">日预算</div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            type="number"
            min="0"
            step="0.01"
            value={budgetValue}
            onChange={(event) => onBudgetChange(event.target.value)}
            disabled={!campaign || saving}
            placeholder="请输入日预算"
            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-100 sm:max-w-[220px]"
          />
          <button
            type="button"
            onClick={() => void onSave()}
            disabled={!campaign || saving}
            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-400"
          >
            {saving ? '保存中...' : '保存预算'}
          </button>
        </div>
        {feedbackMessage ? (
          <div className={`text-xs ${feedbackResult === 'error' ? 'text-red-500 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
            {feedbackMessage}
          </div>
        ) : null}
      </div>
      <ReadOnlyField label="竞价策略" value={campaign?.bidding_strategy || '-'} />
      <ReadOnlyField label="开始日期" value={campaign?.start_date || '-'} />
      <ReadOnlyField label="状态" value={campaign?.status || '-'} />
      <ReadOnlyField label="广告类型" value={campaign?.ad_type || '-'} />
    </div>
  );
}

export default function CampaignDetail() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const campaignId = params.id ?? '';
  const [activeTab, setActiveTab] = useState<TabKey>('ad_groups');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [reloadKey, setReloadKey] = useState(0);
  const [adGroupStatusFilter, setAdGroupStatusFilter] = useState<StatusFilterValue>('all');
  const [campaign, setCampaign] = useState<CampaignInfo | null>(null);
  const [campaignLoading, setCampaignLoading] = useState(true);
  const [campaignMockMode, setCampaignMockMode] = useState(false);
  const [budgetValue, setBudgetValue] = useState('');
  const [budgetSaving, setBudgetSaving] = useState(false);
  const [budgetFeedbackMessage, setBudgetFeedbackMessage] = useState<string | null>(null);
  const [budgetFeedbackResult, setBudgetFeedbackResult] = useState<ActionResult>('idle');
  const [listState, setListState] = useState<Record<Exclude<TabKey, 'settings'>, ListState<BaseListRow>>>(() => ({
    ad_groups: { data: [], total: 0, loading: false, mockMode: false },
    targeting: { data: [], total: 0, loading: false, mockMode: false },
    search_terms: { data: [], total: 0, loading: false, mockMode: false },
    negative_targeting: { data: [], total: 0, loading: false, mockMode: false },
    logs: { data: [], total: 0, loading: false, mockMode: false },
  }));

  const currentCampaignName = campaign?.campaign_name || (campaignId ? `Campaign ${campaignId}` : '广告活动详情');

  useEffect(() => {
    let alive = true;

    async function fetchCampaign() {
      if (!campaignId) {
        setCampaignLoading(false);
        setCampaignMockMode(true);
        return;
      }

      setCampaignLoading(true);
      setCampaignMockMode(false);
      try {
        const response = await api.get(`/ads/campaigns/${campaignId}/settings`);
        const payload = getObjectPayload<CampaignInfo>(response.data, ['data', 'campaign', 'item']);
        if (alive && payload) {
          const normalized = Object.assign({}, payload) as CampaignInfo;
          normalized.id = String(payload.id ?? campaignId);
          normalized.campaign_name = String(payload.campaign_name ?? payload.name ?? `Campaign ${campaignId}`);
          normalized.status = String(payload.status ?? 'unknown');
          normalized.ad_type = String(payload.ad_type ?? '');
          normalized.daily_budget = typeof payload.daily_budget === 'number' ? payload.daily_budget : undefined;
          normalized.bidding_strategy = typeof payload.bidding_strategy === 'string' ? payload.bidding_strategy : undefined;
          normalized.start_date = typeof payload.start_date === 'string' ? payload.start_date : undefined;
          setCampaign(normalized);
          setBudgetValue(typeof normalized.daily_budget === 'number' ? String(normalized.daily_budget) : '');
          setBudgetFeedbackMessage(null);
          setBudgetFeedbackResult('idle');
        }
      } catch {
        if (alive) {
          setCampaign({
            id: campaignId,
            campaign_name: `Campaign ${campaignId}`,
            status: 'unknown',
            ad_type: '',
          });
          setBudgetValue('');
          setBudgetFeedbackMessage(null);
          setBudgetFeedbackResult('idle');
          setCampaignMockMode(true);
        }
      } finally {
        if (alive) {
          setCampaignLoading(false);
        }
      }
    }

    fetchCampaign();
    return () => {
      alive = false;
    };
  }, [campaignId, reloadKey]);

  useEffect(() => {
    const listTab = activeTab === 'settings' ? null : activeTab;
    if (listTab === null) {
      return;
    }
    const tabKey = listTab as Exclude<TabKey, 'settings'>;

    let alive = true;
    const endpointMap: Record<Exclude<TabKey, 'settings'>, string> = {
      ad_groups: `/ads/campaigns/${campaignId}/ad_groups`,
      targeting: `/ads/campaigns/${campaignId}/targeting`,
      search_terms: `/ads/campaigns/${campaignId}/search_terms`,
      negative_targeting: `/ads/campaigns/${campaignId}/negative_targeting`,
      logs: `/ads/campaigns/${campaignId}/logs`,
    };

    async function fetchList() {
      if (!campaignId) {
        return;
      }

      setListState((current) => ({
        ...current,
        [tabKey]: { ...current[tabKey], loading: true, mockMode: false },
      }));

      try {
        const response = await api.get(endpointMap[tabKey], {
          params: { page, page_size: pageSize },
        });
        const parsed = getListPayload<BaseListRow>(response.data);
        if (alive) {
          setListState((current) => ({
            ...current,
            [tabKey]: {
              data: parsed.items,
              total: parsed.totalCount,
              summaryRow: parsed.summaryRow,
              loading: false,
              mockMode: false,
            },
          }));
        }
      } catch {
        if (alive) {
          setListState((current) => ({
            ...current,
            [tabKey]: {
              data: [],
              total: 0,
              summaryRow: undefined,
              loading: false,
              mockMode: true,
            },
          }));
        }
      }
    }

    fetchList();
    return () => {
      alive = false;
    };
  }, [activeTab, campaignId, page, pageSize, reloadKey]);

  useEffect(() => {
    setPage(1);
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'ad_groups') {
      setPage(1);
    }
  }, [activeTab, adGroupStatusFilter]);

  const handleRefresh = () => {
    setReloadKey((value) => value + 1);
  };

  const handleBudgetSave = async () => {
    if (!campaign) return;

    const trimmed = budgetValue.trim();
    if (!trimmed || Number.isNaN(Number(trimmed))) {
      setBudgetFeedbackMessage('请输入有效的预算金额。');
      setBudgetFeedbackResult('error');
      return;
    }

    setBudgetSaving(true);
    setBudgetFeedbackMessage(null);
    setBudgetFeedbackResult('idle');

    try {
      const response = await api.post('/ads/actions', {
        action_key: 'edit_budget',
        target_type: 'campaign',
        target_ids: [campaign.id],
        payload: {
          budgetMode: 'daily',
          budgetValue: trimmed,
        },
      });

      setCampaign((current) => current ? { ...current, daily_budget: Number(trimmed) } : current);
      setBudgetFeedbackMessage(response.data?.message ?? '预算保存成功。');
      setBudgetFeedbackResult('success');
      setReloadKey((value) => value + 1);
    } catch {
      setBudgetFeedbackMessage('预算保存失败，请稍后重试。');
      setBudgetFeedbackResult('error');
    } finally {
      setBudgetSaving(false);
    }
  };

  const adGroupsColumns = useMemo<Column<BaseListRow>[]>(() => [
    { key: 'ad_group_name', title: '广告组', render: (_, row) => String(row.ad_group_name ?? row.name ?? '-') },
    { key: 'status', title: '状态', render: (_, row) => <StatusBadge status={String(row.status ?? row.service_status ?? '')} /> },
    { key: 'default_bid', title: '默认竞价', render: (_, row) => formatCurrency(typeof row.default_bid === 'number' ? row.default_bid : undefined) },
    { key: 'impressions', title: '曝光量', render: (_, row) => formatNumber(typeof row.impressions === 'number' ? row.impressions : undefined) },
    { key: 'clicks', title: '点击量', render: (_, row) => formatNumber(typeof row.clicks === 'number' ? row.clicks : undefined) },
    { key: 'ad_orders', title: '订单量', render: (_, row) => formatNumber(typeof row.ad_orders === 'number' ? row.ad_orders : undefined) },
  ], []);

  const targetingColumns = useMemo<Column<BaseListRow>[]>(() => [
    { key: 'keyword', title: '关键词', render: (_, row) => String(row.keyword ?? '-') },
    { key: 'match_type', title: '匹配类型', render: (_, row) => String(row.match_type ?? '-') },
    { key: 'status', title: '状态', render: (_, row) => <StatusBadge status={String(row.status ?? row.service_status ?? '')} /> },
    { key: 'bid', title: '竞价', render: (_, row) => formatCurrency(typeof row.bid === 'number' ? row.bid : undefined) },
    { key: 'suggested_bid', title: '建议竞价', render: (_, row) => formatCurrency(typeof row.suggested_bid === 'number' ? row.suggested_bid : undefined) },
    { key: 'impressions', title: '曝光量', render: (_, row) => formatNumber(typeof row.impressions === 'number' ? row.impressions : undefined) },
  ], []);

  const searchTermColumns = useMemo<Column<BaseListRow>[]>(() => [
    { key: 'search_term', title: '搜索词', render: (_, row) => String(row.search_term ?? '-') },
    { key: 'targeting', title: '投放', render: (_, row) => String(row.targeting ?? '-') },
    { key: 'match_type', title: '匹配类型', render: (_, row) => String(row.match_type ?? '-') },
    { key: 'suggested_bid', title: '建议竞价', render: (_, row) => formatCurrency(typeof row.suggested_bid === 'number' ? row.suggested_bid : undefined) },
    { key: 'aba_rank', title: 'ABA排名', render: (_, row) => formatNumber(typeof row.aba_rank === 'number' ? row.aba_rank : undefined) },
    { key: 'rank_weekly_change', title: '周变化率', render: (_, row) => formatPercent(typeof row.rank_weekly_change === 'number' ? row.rank_weekly_change : undefined) },
  ], []);

  const negativeTargetingColumns = useMemo<Column<BaseListRow>[]>(() => [
    { key: 'negative_keyword', title: '否定关键词', render: (_, row) => String(row.negative_keyword ?? '-') },
    { key: 'match_type', title: '匹配类型', render: (_, row) => String(row.match_type ?? '-') },
    { key: 'status', title: '状态', render: (_, row) => String(row.status ?? '-') },
    { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
    { key: 'ad_group_name', title: '广告组', render: (_, row) => String(row.ad_group_name ?? '-') },
    { key: 'ad_spend', title: '花费', render: (_, row) => formatCurrency(typeof row.ad_spend === 'number' ? row.ad_spend : undefined) },
  ], []);

  const logColumns = useMemo<Column<BaseListRow>[]>(() => [
    { key: 'operation_time', title: '操作时间', render: (_, row) => String(row.operation_time ?? '-') },
    { key: 'portfolio_name', title: '广告组合', render: (_, row) => String(row.portfolio_name ?? '-') },
    { key: 'campaign_name', title: '广告活动', render: (_, row) => String(row.campaign_name ?? '-') },
    { key: 'ad_group_name', title: '广告组', render: (_, row) => String(row.ad_group_name ?? '-') },
    { key: 'operation_type', title: '操作类型', render: (_, row) => String(row.operation_type ?? '-') },
    { key: 'operation_content', title: '操作内容', render: (_, row) => String(row.operation_content ?? '-') },
  ], []);

  const activeListState = activeTab === 'settings' ? null : listState[activeTab as Exclude<TabKey, 'settings'>];
  const filteredActiveData = useMemo(() => {
    const items = activeListState?.data ?? [];
    if (activeTab !== 'ad_groups' || adGroupStatusFilter === 'all') {
      return items;
    }
    return items.filter((row) => String(row.status ?? row.service_status ?? '') === adGroupStatusFilter);
  }, [activeListState?.data, activeTab, adGroupStatusFilter]);

  return (
    <div className="mx-auto max-w-[1600px] p-6 text-gray-900 dark:text-gray-100">
      <div className="mb-4 flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={() => navigate(`/ads/manage${location.search}`)}
          className="inline-flex items-center gap-2 text-sm font-medium text-blue-500 hover:underline dark:text-blue-400"
        >
          ← 返回广告管理
        </button>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={campaignLoading || budgetSaving || (activeListState?.loading ?? false)}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          <RefreshCw size={16} className={campaignLoading || budgetSaving || (activeListState?.loading ?? false) ? 'animate-spin' : ''} />
          刷新
        </button>
      </div>

      <div className="mb-4 flex items-center gap-2 text-sm">
        <span
          className="cursor-pointer text-blue-500 hover:underline dark:text-blue-400"
          onClick={() => navigate(`/ads/manage${location.search}`)}
        >
          广告管理
        </span>
        <span className="text-gray-500 dark:text-gray-400">/</span>
        <span className="text-gray-700 dark:text-gray-200">广告活动</span>
        <span className="text-gray-500 dark:text-gray-400">/</span>
        <span className="font-medium text-gray-900 dark:text-gray-100">{currentCampaignName}</span>
      </div>

      <div className="mb-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{currentCampaignName}</h1>
              {campaign?.ad_type ? <AdTypeBadge adType={campaign.ad_type} /> : null}
              <StatusBadge status={campaign?.status || 'unknown'} />
            </div>
            <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {campaignLoading ? '加载中...' : campaignMockMode ? '未读取到活动详情' : '活动详情'}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[540px]">
            <InfoCard label="广告类型" value={campaign?.ad_type || '-'} />
            <InfoCard label="状态" value={campaign?.status || '-'} />
            <InfoCard label="日预算" value={campaign ? formatCurrency(campaign.daily_budget) : '-'} />
          </div>
        </div>
      </div>

      <div className="mb-6 border-b border-gray-200 dark:border-gray-800">
        <div className="flex gap-6 overflow-x-auto">
          {TAB_ITEMS.map((item) => (
            <TabButton
              key={item.key}
              active={activeTab === item.key}
              label={item.label}
              onClick={() => setActiveTab(item.key)}
            />
          ))}
        </div>
      </div>

      {activeTab === 'settings' ? (
        <div className="space-y-4">
          {campaignMockMode ? (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
              未读取到活动详情，请确认该活动已同步或稍后重试。
            </div>
          ) : null}
          <CampaignSettingsForm
            campaign={campaign}
            budgetValue={budgetValue}
            saving={budgetSaving}
            feedbackMessage={budgetFeedbackMessage}
            feedbackResult={budgetFeedbackResult}
            onBudgetChange={setBudgetValue}
            onSave={handleBudgetSave}
          />
        </div>
      ) : (
        <div className="space-y-4">
          {activeTab === 'ad_groups' ? (
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-900">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-200">广告组状态</span>
              <select
                value={adGroupStatusFilter}
                onChange={(event) => setAdGroupStatusFilter(event.target.value as StatusFilterValue)}
                className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-100"
              >
                <option value="all">全部状态</option>
                <option value="enabled">启用</option>
                <option value="paused">暂停</option>
                <option value="archived">已归档</option>
              </select>
            </div>
          ) : null}

          {activeListState?.mockMode ? (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
              接口暂未返回数据，请确认筛选条件或稍后重试。
            </div>
          ) : null}

          <DataTable
            columns={
              activeTab === 'ad_groups'
                ? adGroupsColumns
                : activeTab === 'targeting'
                  ? targetingColumns
                  : activeTab === 'search_terms'
                    ? searchTermColumns
                    : activeTab === 'negative_targeting'
                      ? negativeTargetingColumns
                      : logColumns
            }
            data={filteredActiveData}
            rowKey="id"
            loading={activeListState?.loading ?? false}
            summaryRow={activeListState?.summaryRow}
            emptyText={activeListState?.mockMode ? '接口暂未返回数据' : '暂无数据'}
            pagination={{
              current: page,
              pageSize,
              total: activeTab === 'ad_groups' && adGroupStatusFilter !== 'all' ? filteredActiveData.length : (activeListState?.total ?? 0),
              onChange: (nextPage) => setPage(nextPage),
            }}
          />
        </div>
      )}
    </div>
  );
}

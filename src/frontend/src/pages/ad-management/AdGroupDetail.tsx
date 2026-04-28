import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { DataTable } from '../../components/DataTable';
import api from '../../api/client';
import type { Column } from '../../types/table';
import { getListPayload, getObjectPayload } from './detail/detailData';

type TabKey = 'ad_products' | 'targeting' | 'search_terms' | 'negative_targeting' | 'tips' | 'settings' | 'logs';

interface BaseListRow {
  id: string;
  [key: string]: unknown;
}

interface AdGroupInfo extends Record<string, unknown> {
  id: string;
  ad_group_name: string;
  campaign_name: string;
  status: string;
  default_bid?: number;
}

interface ListState<T> {
  data: T[];
  total: number;
  summaryRow?: Partial<T>;
  loading: boolean;
  mockMode: boolean;
}

const TAB_ITEMS: Array<{ key: TabKey; label: string }> = [
  { key: 'ad_products', label: '广告产品' },
  { key: 'targeting', label: '投放' },
  { key: 'search_terms', label: '搜索词' },
  { key: 'negative_targeting', label: '否定投放' },
  { key: 'tips', label: '提示词' },
  { key: 'settings', label: '广告组设置' },
  { key: 'logs', label: '广告日志' },
];

const statusMeta: Record<string, { label: string; className: string }> = {
  enabled: { label: '启用', className: 'bg-green-500/20 text-green-400' },
  paused: { label: '暂停', className: 'bg-yellow-500/20 text-yellow-400' },
  archived: { label: '已归档', className: 'bg-gray-500/20 text-gray-400' },
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

function AdGroupSettingsForm({ adGroup }: { adGroup: AdGroupInfo | null }) {
  return (
    <div className="grid gap-4 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900 md:grid-cols-2">
      <ReadOnlyField label="广告组名称" value={adGroup?.ad_group_name || '-'} />
      <ReadOnlyField label="所属Campaign" value={adGroup?.campaign_name || '-'} />
      <ReadOnlyField label="状态" value={adGroup?.status || '-'} />
      <ReadOnlyField label="默认竞价" value={adGroup ? formatCurrency(adGroup.default_bid) : '-'} />
    </div>
  );
}

export default function AdGroupDetail() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const adGroupId = params.id ?? '';
  const [activeTab, setActiveTab] = useState<TabKey>('ad_products');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [adGroup, setAdGroup] = useState<AdGroupInfo | null>(null);
  const [adGroupLoading, setAdGroupLoading] = useState(true);
  const [adGroupMockMode, setAdGroupMockMode] = useState(false);
  const [listState, setListState] = useState<Record<Exclude<TabKey, 'tips' | 'settings'>, ListState<BaseListRow>>>(() => ({
    ad_products: { data: [], total: 0, loading: false, mockMode: false },
    targeting: { data: [], total: 0, loading: false, mockMode: false },
    search_terms: { data: [], total: 0, loading: false, mockMode: false },
    negative_targeting: { data: [], total: 0, loading: false, mockMode: false },
    logs: { data: [], total: 0, loading: false, mockMode: false },
  }));

  const currentAdGroupName = adGroup?.ad_group_name || (adGroupId ? `Ad Group ${adGroupId}` : '广告组详情');

  useEffect(() => {
    let alive = true;

    async function fetchAdGroup() {
      if (!adGroupId) {
        setAdGroupLoading(false);
        setAdGroupMockMode(true);
        return;
      }

      setAdGroupLoading(true);
      setAdGroupMockMode(false);
      try {
        const response = await api.get(`/ads/ad_groups/${adGroupId}`);
        const payload = getObjectPayload<AdGroupInfo>(response.data, ['data', 'ad_group', 'item']);
        if (alive && payload) {
          const normalized = Object.assign({}, payload) as AdGroupInfo;
          normalized.id = String(payload.id ?? adGroupId);
          normalized.ad_group_name = String(payload.ad_group_name ?? payload.name ?? `Ad Group ${adGroupId}`);
          normalized.campaign_name = String(payload.campaign_name ?? '-');
          normalized.status = String(payload.status ?? 'unknown');
          normalized.default_bid = typeof payload.default_bid === 'number' ? payload.default_bid : undefined;
          setAdGroup(normalized);
        }
      } catch {
        if (alive) {
          setAdGroup({
            id: adGroupId,
            ad_group_name: `Ad Group ${adGroupId}`,
            campaign_name: '-',
            status: 'unknown',
          });
          setAdGroupMockMode(true);
        }
      } finally {
        if (alive) {
          setAdGroupLoading(false);
        }
      }
    }

    fetchAdGroup();
    return () => {
      alive = false;
    };
  }, [adGroupId]);

  useEffect(() => {
    const listTab = activeTab === 'tips' || activeTab === 'settings' ? null : activeTab;
    if (listTab === null) {
      return;
    }
    const tabKey = listTab as Exclude<TabKey, 'tips' | 'settings'>;

    let alive = true;
    const endpointMap: Record<Exclude<TabKey, 'tips' | 'settings'>, string> = {
      ad_products: `/ads/ad_groups/${adGroupId}/ad_products`,
      targeting: `/ads/ad_groups/${adGroupId}/targeting`,
      search_terms: `/ads/ad_groups/${adGroupId}/search_terms`,
      negative_targeting: `/ads/ad_groups/${adGroupId}/negative_targeting`,
      logs: `/ads/ad_groups/${adGroupId}/logs`,
    };

    async function fetchList() {
      if (!adGroupId) {
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
  }, [activeTab, adGroupId, page, pageSize]);

  useEffect(() => {
    setPage(1);
  }, [activeTab]);

  const adProductsColumns = useMemo<Column<BaseListRow>[]>(() => [
    { key: 'asin', title: 'ASIN', render: (_, row) => String(row.asin ?? '-') },
    { key: 'product_title', title: '产品', render: (_, row) => String(row.product_title ?? row.title ?? '-') },
    { key: 'status', title: '状态', render: (_, row) => <StatusBadge status={String(row.status ?? row.service_status ?? '')} /> },
    { key: 'price', title: '价格', render: (_, row) => formatCurrency(typeof row.price === 'number' ? row.price : undefined) },
    { key: 'rating_count', title: '评分数', render: (_, row) => formatNumber(typeof row.rating_count === 'number' ? row.rating_count : undefined) },
    { key: 'star_rating', title: '星级', render: (_, row) => formatNumber(typeof row.star_rating === 'number' ? row.star_rating : undefined) },
  ], []);

  const targetingColumns = useMemo<Column<BaseListRow>[]>(() => [
    { key: 'keyword', title: '关键词', render: (_, row) => String(row.keyword ?? '-') },
    { key: 'match_type', title: '匹配类型', render: (_, row) => String(row.match_type ?? '-') },
    { key: 'status', title: '状态', render: (_, row) => String(row.status ?? row.service_status ?? '-') },
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

  const activeListState = activeTab === 'tips' || activeTab === 'settings' ? null : listState[activeTab as Exclude<TabKey, 'tips' | 'settings'>];

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
      </div>

      <div className="mb-4 flex items-center gap-2 text-sm">
        <span
          className="cursor-pointer text-blue-500 hover:underline dark:text-blue-400"
          onClick={() => navigate(`/ads/manage${location.search}`)}
        >
          广告管理
        </span>
        <span className="text-gray-500 dark:text-gray-400">/</span>
        <span className="text-gray-700 dark:text-gray-200">广告组</span>
        <span className="text-gray-500 dark:text-gray-400">/</span>
        <span className="font-medium text-gray-900 dark:text-gray-100">{currentAdGroupName}</span>
      </div>

      <div className="mb-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{currentAdGroupName}</h1>
              <StatusBadge status={adGroup?.status || 'unknown'} />
            </div>
            <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {adGroupLoading ? '加载中...' : adGroupMockMode ? '未读取到广告组详情' : '广告组详情'}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[540px]">
            <InfoCard label="所属Campaign" value={adGroup?.campaign_name || '-'} />
            <InfoCard label="状态" value={adGroup?.status || '-'} />
            <InfoCard label="默认竞价" value={adGroup ? formatCurrency(adGroup.default_bid) : '-'} />
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

      {activeTab === 'tips' ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-5 text-sm leading-7 text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
            当前广告组暂无AI生成的投放提示词。您可以通过广告优化Agent获取智能投放建议。
          </div>
        </div>
      ) : activeTab === 'settings' ? (
        <div className="space-y-4">
          {adGroupMockMode ? (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
              未读取到广告组详情，请确认该广告组已同步或稍后重试。
            </div>
          ) : null}
          <AdGroupSettingsForm adGroup={adGroup} />
        </div>
      ) : (
        <div className="space-y-4">
          {activeListState?.mockMode ? (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
              接口暂未返回数据，请确认筛选条件或稍后重试。
            </div>
          ) : null}

          <DataTable
            columns={
              activeTab === 'ad_products'
                ? adProductsColumns
                : activeTab === 'targeting'
                  ? targetingColumns
                  : activeTab === 'search_terms'
                    ? searchTermColumns
                    : activeTab === 'negative_targeting'
                      ? negativeTargetingColumns
                      : logColumns
            }
            data={activeListState?.data ?? []}
            rowKey="id"
            loading={activeListState?.loading ?? false}
            summaryRow={activeListState?.summaryRow}
            emptyText={activeListState?.mockMode ? '接口暂未返回数据' : '暂无数据'}
            pagination={{
              current: page,
              pageSize,
              total: activeListState?.total ?? 0,
              onChange: (nextPage) => setPage(nextPage),
            }}
          />
        </div>
      )}
    </div>
  );
}

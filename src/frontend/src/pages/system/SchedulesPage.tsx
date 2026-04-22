import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock3, PauseCircle, PlayCircle, RefreshCw, Zap } from 'lucide-react';
import { DataTable } from '../../components/DataTable';
import { Column } from '../../types/table';
import api from '../../api/client';
import { formatSiteTime } from '../../utils/timezone';

interface SchedulerJob {
  id: string;
  description: string;
  trigger: string;
  next_run_time: string | null;
  [key: string]: unknown;
}

type JobAction = 'pause' | 'resume' | 'trigger' | null;

function isPaused(job: SchedulerJob): boolean {
  return job.next_run_time === null;
}

export default function SchedulesPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<SchedulerJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  const [pendingJobId, setPendingJobId] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<JobAction>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3000);
  };

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const response = await api.get<SchedulerJob[]>('/scheduler/jobs');
      setJobs(Array.isArray(response.data) ? response.data : []);
    } catch (_error: unknown) {
      showToast('获取计划任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleJobAction = async (job: SchedulerJob, action: Exclude<JobAction, null>) => {
    setPendingJobId(job.id);
    setPendingAction(action);
    try {
      if (action === 'trigger') {
        await api.post(`/scheduler/trigger/${job.id}`);
      } else {
        await api.post(`/scheduler/jobs/${job.id}/${action}`);
      }
      const actionText = action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : '触发';
      showToast(`任务${actionText}成功`);
      await fetchJobs();
    } catch (_error: unknown) {
      const actionText = action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : '触发';
      showToast(`任务${actionText}失败`);
    } finally {
      setPendingJobId(null);
      setPendingAction(null);
    }
  };

  const columns: Column<SchedulerJob>[] = [
    {
      key: 'id',
      title: '任务 ID',
      render: (val) => (
        <code className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-sm text-gray-700 dark:text-gray-300">
          {String(val)}
        </code>
      ),
    },
    {
      key: 'description',
      title: '任务说明',
      render: (val) => <span className="text-gray-900 dark:text-white">{String(val || '-')}</span>,
    },
    {
      key: 'trigger',
      title: '触发规则',
      render: (val) => (
        <span className="font-mono text-xs text-gray-500 dark:text-gray-400">{String(val || '-')}</span>
      ),
    },
    {
      key: 'next_run_time',
      title: '下次执行时间',
      render: (val) => (val ? formatSiteTime(new Date(String(val))) : '-'),
    },
    {
      key: 'status',
      title: '状态',
      render: (_, row) => {
        const paused = isPaused(row);
        return paused ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">
            已暂停
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
            启用中
          </span>
        );
      },
    },
    {
      key: 'actions',
      title: '操作',
      align: 'center',
      render: (_, row) => {
        const acting = pendingJobId === row.id;
        const paused = isPaused(row);
        return (
          <div className="flex items-center justify-center gap-2">
            {paused ? (
              <button
                onClick={() => handleJobAction(row, 'resume')}
                disabled={acting}
                className="inline-flex items-center px-3 py-1.5 rounded-md text-xs font-medium border border-green-200 text-green-700 hover:bg-green-50 dark:border-green-900/50 dark:text-green-400 dark:hover:bg-green-900/20 disabled:opacity-50"
              >
                <PlayCircle className="w-3.5 h-3.5 mr-1" />
                {acting && pendingAction === 'resume' ? '处理中...' : '恢复'}
              </button>
            ) : (
              <button
                onClick={() => handleJobAction(row, 'pause')}
                disabled={acting}
                className="inline-flex items-center px-3 py-1.5 rounded-md text-xs font-medium border border-amber-200 text-amber-700 hover:bg-amber-50 dark:border-amber-900/50 dark:text-amber-400 dark:hover:bg-amber-900/20 disabled:opacity-50"
              >
                <PauseCircle className="w-3.5 h-3.5 mr-1" />
                {acting && pendingAction === 'pause' ? '处理中...' : '暂停'}
              </button>
            )}
            <button
              onClick={() => handleJobAction(row, 'trigger')}
              disabled={acting}
              className="inline-flex items-center px-3 py-1.5 rounded-md text-xs font-medium border border-blue-200 text-blue-700 hover:bg-blue-50 dark:border-blue-900/50 dark:text-blue-400 dark:hover:bg-blue-900/20 disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5 mr-1" />
              {acting && pendingAction === 'trigger' ? '处理中...' : '立即触发'}
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Clock3 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            计划任务
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            复用现有 scheduler API，仅支持查看任务、暂停、恢复和立即触发。
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/system')}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white dark:bg-gray-800 dark:text-gray-200 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            返回系统管理
          </button>
          <button
            onClick={fetchJobs}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新任务
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
        <DataTable
          columns={columns}
          data={jobs}
          rowKey="id"
          loading={loading}
          emptyText="暂无计划任务"
        />
      </div>

      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50">
          {toastMsg}
        </div>
      )}
    </div>
  );
}

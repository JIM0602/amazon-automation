"""调度器包 — APScheduler BackgroundScheduler 模块级单例。

对外暴露：
    get_scheduler()      — 返回调度器实例（懒加载）
    start_scheduler()    — 启动调度器，加载 SCHEDULED_JOBS
    shutdown_scheduler() — 优雅关闭

当 apscheduler 未安装时，所有函数都能安全降级（get_scheduler 返回 None）。
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# APScheduler 懒加载 — 未安装时降级
# ---------------------------------------------------------------------------
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor

    _APSCHEDULER_AVAILABLE = True
except ImportError:  # pragma: no cover — 测试环境可能未安装
    BackgroundScheduler = None  # type: ignore[assignment,misc]
    MemoryJobStore = None  # type: ignore[assignment]
    ThreadPoolExecutor = None  # type: ignore[assignment]
    _APSCHEDULER_AVAILABLE = False

# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------
_scheduler: Optional[object] = None


def get_scheduler() -> Optional[object]:
    """返回全局调度器实例（懒加载）。

    未安装 apscheduler 时返回 None。
    """
    global _scheduler
    if not _APSCHEDULER_AVAILABLE:
        logger.warning("APScheduler 未安装，调度功能不可用")
        return None

    if _scheduler is None:
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=4)}
        job_defaults = {
            "coalesce": True,       # 错过执行时合并为一次
            "max_instances": 1,     # 同一任务最多同时运行1个
        }
        _scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )
        logger.info("APScheduler 实例已创建")
    return _scheduler


def start_scheduler() -> bool:
    """启动调度器并加载预配置任务。

    Returns:
        True — 启动成功；False — APScheduler 未安装。
    """
    if not _APSCHEDULER_AVAILABLE:
        logger.warning("APScheduler 未安装，跳过启动")
        return False

    scheduler = get_scheduler()
    if scheduler is None:
        return False

    # 已经在运行时不重复启动
    if scheduler.running:  # type: ignore[union-attr]
        logger.info("调度器已在运行，跳过重复启动")
        return True

    # 加载预配置任务
    from src.scheduler.config import SCHEDULED_JOBS

    for job_conf in SCHEDULED_JOBS:
        job_conf_copy = dict(job_conf)
        description = job_conf_copy.pop("description", "")
        job_id = job_conf_copy.get("id", "unknown")

        try:
            scheduler.add_job(**job_conf_copy)  # type: ignore[union-attr]
            logger.info("已加载任务: %s — %s", job_id, description)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("加载任务失败 %s: %s", job_id, exc)

    scheduler.start()  # type: ignore[union-attr]
    logger.info("调度器已启动，共 %d 个任务", len(SCHEDULED_JOBS))
    return True


def shutdown_scheduler(wait: bool = True) -> None:
    """优雅关闭调度器。

    Args:
        wait: 是否等待正在运行的任务完成（默认 True）。
    """
    global _scheduler
    if _scheduler is None:
        return

    try:
        if _scheduler.running:  # type: ignore[union-attr]
            _scheduler.shutdown(wait=wait)  # type: ignore[union-attr]
            logger.info("调度器已关闭")
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("关闭调度器失败: %s", exc)
    finally:
        _scheduler = None


__all__ = ["get_scheduler", "start_scheduler", "shutdown_scheduler"]

"""飞书多维表格（Bitable）同步模块 — 封装 Bitable v1 REST API。

提供 BitableSyncClient 类，支持多维表格记录的增删改查与批量创建操作。
所有写操作均记录到 audit_logs 表。
"""
from __future__ import annotations

import logging
from typing import Optional

try:
    import httpx
except ImportError as _exc:  # pragma: no cover
    raise ImportError("httpx 未安装，请执行 pip install httpx") from _exc

try:
    from src.feishu.bot_handler import get_bot
except ImportError:  # pragma: no cover
    get_bot = None  # type: ignore[assignment]

try:
    from src.db.connection import db_session
    from src.db.models import AuditLog
    _DB_AVAILABLE = True
except ImportError:  # pragma: no cover
    db_session = None  # type: ignore[assignment]
    AuditLog = None  # type: ignore[assignment]
    _DB_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
_BITABLE_BASE = "https://open.feishu.cn/open-apis/bitable/v1"
_BATCH_SIZE = 50  # 每批最多创建记录数（飞书限制）
_ACTOR = "bitable_sync"  # audit_log actor 标识


def _records_url(app_token: str, table_id: str) -> str:
    """拼接多维表格记录的基础 URL。"""
    return f"{_BITABLE_BASE}/apps/{app_token}/tables/{table_id}/records"


def _record_url(app_token: str, table_id: str, record_id: str) -> str:
    """拼接单条记录 URL。"""
    return f"{_BITABLE_BASE}/apps/{app_token}/tables/{table_id}/records/{record_id}"


def _batch_records_url(app_token: str, table_id: str) -> str:
    """拼接批量创建记录 URL。"""
    return f"{_BITABLE_BASE}/apps/{app_token}/tables/{table_id}/records/batch_create"


def _get_auth_headers() -> dict:
    """通过 FeishuBot 获取 tenant_access_token 并构造请求头。"""
    bot = get_bot()
    token = bot.get_tenant_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _write_audit_log(action: str, pre_state: Optional[dict], post_state: Optional[dict]) -> None:
    """将写操作写入 audit_logs 表，失败时仅记录日志不抛异常。"""
    if not _DB_AVAILABLE or db_session is None or AuditLog is None:
        logger.debug("数据库不可用，跳过审计日志写入: action=%s", action)
        return
    try:
        with db_session() as session:
            log = AuditLog(
                action=action,
                actor=_ACTOR,
                pre_state=pre_state,
                post_state=post_state,
            )
            session.add(log)
            session.commit()
    except Exception:
        logger.exception("写入审计日志失败: action=%s", action)


# ---------------------------------------------------------------------------
# BitableSyncClient
# ---------------------------------------------------------------------------

class BitableSyncClient:
    """飞书多维表格同步客户端。

    所有方法均为无状态调用（token 由 FeishuBot 全局单例管理），
    app_token 与 table_id 从方法参数传入，不硬编码。
    """

    # ------------------------------------------------------------------ #
    #  新建记录
    # ------------------------------------------------------------------ #

    def create_record(
        self,
        app_token: str,
        table_id: str,
        fields: dict,
    ) -> dict:
        """在多维表格中新建一条记录。

        Args:
            app_token: 多维表格应用 Token（在飞书多维表格 URL 中获取）。
            table_id:  表格 ID（如 tblXXXXXX）。
            fields:    记录字段字典，key 为列名，value 为字段值。

        Returns:
            飞书 API 返回的 record 对象；失败时返回空 dict。
        """
        url = _records_url(app_token, table_id)
        payload = {"fields": fields}
        try:
            headers = _get_auth_headers()
            with httpx.Client(timeout=10) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error("create_record API 返回错误: %s", data)
                return {}
            record = data.get("data", {}).get("record", {})
            _write_audit_log(
                action="bitable.create_record",
                pre_state=None,
                post_state={"app_token": app_token, "table_id": table_id, "record": record},
            )
            return record
        except Exception:
            logger.exception(
                "create_record 失败: app_token=%s table_id=%s", app_token, table_id
            )
            return {}

    # ------------------------------------------------------------------ #
    #  更新记录
    # ------------------------------------------------------------------ #

    def update_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: dict,
    ) -> dict:
        """更新多维表格中的一条记录。

        Args:
            app_token: 多维表格应用 Token。
            table_id:  表格 ID。
            record_id: 记录 ID（recXXXXXX）。
            fields:    需要更新的字段字典。

        Returns:
            更新后的 record 对象；失败时返回空 dict。
        """
        url = _record_url(app_token, table_id, record_id)
        payload = {"fields": fields}
        try:
            headers = _get_auth_headers()
            with httpx.Client(timeout=10) as client:
                resp = client.put(url, headers=headers, json=payload)
                resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error("update_record API 返回错误: %s", data)
                return {}
            record = data.get("data", {}).get("record", {})
            _write_audit_log(
                action="bitable.update_record",
                pre_state={"app_token": app_token, "table_id": table_id, "record_id": record_id},
                post_state={"app_token": app_token, "table_id": table_id, "record": record},
            )
            return record
        except Exception:
            logger.exception(
                "update_record 失败: app_token=%s table_id=%s record_id=%s",
                app_token, table_id, record_id,
            )
            return {}

    # ------------------------------------------------------------------ #
    #  列出记录
    # ------------------------------------------------------------------ #

    def list_records(
        self,
        app_token: str,
        table_id: str,
        filter_expr: Optional[str] = None,
    ) -> list:
        """列出多维表格中的所有记录（自动翻页）。

        Args:
            app_token:   多维表格应用 Token。
            table_id:    表格 ID。
            filter_expr: 飞书公式过滤表达式，例如 `CurrentValue.[状态]="待处理"`。
                         为 None 时不过滤。

        Returns:
            记录列表；失败时返回空 list。
        """
        url = _records_url(app_token, table_id)
        records: list = []
        page_token: Optional[str] = None

        try:
            headers = _get_auth_headers()
            while True:
                params: dict = {"page_size": 100}
                if filter_expr:
                    params["filter"] = filter_expr
                if page_token:
                    params["page_token"] = page_token

                with httpx.Client(timeout=10) as client:
                    resp = client.get(url, headers=headers, params=params)
                    resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    logger.error("list_records API 返回错误: %s", data)
                    return records

                page_data = data.get("data", {})
                items = page_data.get("items", [])
                records.extend(items)

                has_more = page_data.get("has_more", False)
                page_token = page_data.get("page_token")
                if not has_more or not page_token:
                    break

        except Exception:
            logger.exception(
                "list_records 失败: app_token=%s table_id=%s", app_token, table_id
            )
        return records

    # ------------------------------------------------------------------ #
    #  删除记录
    # ------------------------------------------------------------------ #

    def delete_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
    ) -> bool:
        """删除多维表格中的一条记录。

        Args:
            app_token: 多维表格应用 Token。
            table_id:  表格 ID。
            record_id: 记录 ID。

        Returns:
            成功返回 True，失败返回 False。
        """
        url = _record_url(app_token, table_id, record_id)
        try:
            headers = _get_auth_headers()
            with httpx.Client(timeout=10) as client:
                resp = client.delete(url, headers=headers)
                resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error("delete_record API 返回错误: %s", data)
                return False
            deleted = data.get("data", {}).get("deleted", False)
            if deleted:
                _write_audit_log(
                    action="bitable.delete_record",
                    pre_state={"app_token": app_token, "table_id": table_id, "record_id": record_id},
                    post_state={"deleted": True},
                )
            return bool(deleted)
        except Exception:
            logger.exception(
                "delete_record 失败: app_token=%s table_id=%s record_id=%s",
                app_token, table_id, record_id,
            )
            return False

    # ------------------------------------------------------------------ #
    #  批量创建记录
    # ------------------------------------------------------------------ #

    def batch_create_records(
        self,
        app_token: str,
        table_id: str,
        records: list[dict],
    ) -> list:
        """批量创建多维表格记录（每批最多 50 条，自动分批）。

        Args:
            app_token: 多维表格应用 Token。
            table_id:  表格 ID。
            records:   字段字典列表，每个元素对应一条记录的 fields。

        Returns:
            所有成功创建的 record 列表；失败的批次跳过并记录日志。
        """
        url = _batch_records_url(app_token, table_id)
        all_created: list = []

        try:
            headers = _get_auth_headers()
        except Exception:
            logger.exception("batch_create_records 获取 token 失败")
            return all_created

        # 按批次切片
        for i in range(0, len(records), _BATCH_SIZE):
            batch = records[i: i + _BATCH_SIZE]
            payload = {"records": [{"fields": r} for r in batch]}
            try:
                with httpx.Client(timeout=15) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    logger.error(
                        "batch_create_records 批次 %d API 返回错误: %s", i // _BATCH_SIZE, data
                    )
                    continue
                created = data.get("data", {}).get("records", [])
                all_created.extend(created)
                _write_audit_log(
                    action="bitable.batch_create_records",
                    pre_state=None,
                    post_state={
                        "app_token": app_token,
                        "table_id": table_id,
                        "batch_index": i // _BATCH_SIZE,
                        "count": len(created),
                    },
                )
            except Exception:
                logger.exception(
                    "batch_create_records 批次 %d 失败: app_token=%s table_id=%s",
                    i // _BATCH_SIZE, app_token, table_id,
                )
        return all_created

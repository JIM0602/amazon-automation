"""飞书多维表格（Bitable）同步模块单元测试。

全部使用 unittest.mock 进行 mock，不调用真实飞书 API。
运行方式：pytest tests/test_bitable_sync.py --mock-external-apis
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import httpx
import pytest


# ============================================================================ #
#  Fixtures
# ============================================================================ #

APP_TOKEN = "bascXXXXXXXXXXXX"
TABLE_ID = "tblYYYYYYYYYYYYYY"
RECORD_ID = "recZZZZZZZZZZZZZZ"


@pytest.fixture()
def mock_get_token():
    """Mock FeishuBot.get_tenant_access_token，始终返回 mock_token_xxx。"""
    with patch("src.feishu.bitable_sync.get_bot") as mock_get_bot:
        mock_bot = MagicMock()
        mock_bot.get_tenant_access_token.return_value = "mock_token_xxx"
        mock_get_bot.return_value = mock_bot
        yield mock_get_bot


@pytest.fixture()
def mock_db():
    """Mock db_session，不操作真实数据库。"""
    with patch("src.feishu.bitable_sync.db_session") as mock_ds:
        mock_session = MagicMock()
        mock_ds.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_ds.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_session


@pytest.fixture()
def client(mock_get_token, mock_db):
    """返回 BitableSyncClient 实例，依赖均已 mock。"""
    from src.feishu.bitable_sync import BitableSyncClient
    return BitableSyncClient()


def _mock_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """构造一个模拟 httpx 响应对象。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _make_mock_httpx_client(response: MagicMock) -> MagicMock:
    """构造支持 context manager 协议的 mock httpx.Client。"""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = response
    mock_client.put.return_value = response
    mock_client.get.return_value = response
    mock_client.delete.return_value = response
    return mock_client


# ============================================================================ #
#  BitableSyncClient.create_record
# ============================================================================ #

class TestCreateRecord:
    def test_returns_record_on_success(self, client):
        """成功时返回 API 返回的 record dict。"""
        expected_record = {"record_id": RECORD_ID, "fields": {"名称": "测试商品"}}
        api_resp = {"code": 0, "msg": "success", "data": {"record": expected_record}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.create_record(APP_TOKEN, TABLE_ID, {"名称": "测试商品"})

        assert result == expected_record
        assert result["record_id"] == RECORD_ID

    def test_calls_correct_url(self, client):
        """应调用正确的 URL（records 端点）。"""
        api_resp = {"code": 0, "data": {"record": {"record_id": RECORD_ID, "fields": {}}}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.create_record(APP_TOKEN, TABLE_ID, {})

        expected_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1"
            f"/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
        )
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == expected_url

    def test_sends_bearer_token(self, client):
        """请求头应包含 Bearer token。"""
        api_resp = {"code": 0, "data": {"record": {"record_id": RECORD_ID, "fields": {}}}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.create_record(APP_TOKEN, TABLE_ID, {"test": "value"})

        call_kwargs = mock_httpx_client.post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer mock_token_xxx"

    def test_returns_empty_dict_on_api_error(self, client):
        """API 返回非 0 code 时返回空 dict。"""
        api_resp = {"code": 99991663, "msg": "app not exist", "data": {}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.create_record(APP_TOKEN, TABLE_ID, {"test": "val"})

        assert result == {}

    def test_returns_empty_dict_on_http_exception(self, client):
        """HTTP 异常时返回空 dict，不抛异常。"""
        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.post.side_effect = httpx.ConnectError("连接超时")

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.create_record(APP_TOKEN, TABLE_ID, {"test": "val"})

        assert result == {}

    def test_writes_audit_log_on_success(self, client, mock_db):
        """成功时应写入审计日志（调用 session.add）。"""
        api_resp = {"code": 0, "data": {"record": {"record_id": RECORD_ID, "fields": {}}}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.create_record(APP_TOKEN, TABLE_ID, {"key": "val"})

        mock_db.add.assert_called_once()
        log_arg = mock_db.add.call_args[0][0]
        assert log_arg.action == "bitable.create_record"
        assert log_arg.actor == "bitable_sync"


# ============================================================================ #
#  BitableSyncClient.update_record
# ============================================================================ #

class TestUpdateRecord:
    def test_returns_updated_record_on_success(self, client):
        """成功时返回更新后的 record dict。"""
        expected_record = {"record_id": RECORD_ID, "fields": {"状态": "已完成"}}
        api_resp = {"code": 0, "data": {"record": expected_record}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.update_record(APP_TOKEN, TABLE_ID, RECORD_ID, {"状态": "已完成"})

        assert result == expected_record

    def test_calls_correct_url_with_put(self, client):
        """应使用 PUT 方法并调用带 record_id 的 URL。"""
        api_resp = {"code": 0, "data": {"record": {"record_id": RECORD_ID, "fields": {}}}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.update_record(APP_TOKEN, TABLE_ID, RECORD_ID, {})

        expected_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1"
            f"/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{RECORD_ID}"
        )
        mock_httpx_client.put.assert_called_once()
        call_args = mock_httpx_client.put.call_args
        assert call_args[0][0] == expected_url

    def test_returns_empty_dict_on_api_error(self, client):
        """API 错误时返回空 dict。"""
        api_resp = {"code": 1254040, "msg": "record not found"}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.update_record(APP_TOKEN, TABLE_ID, RECORD_ID, {})

        assert result == {}

    def test_returns_empty_dict_on_exception(self, client):
        """网络异常时返回空 dict，不抛异常。"""
        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.put.side_effect = httpx.TimeoutException("超时")

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.update_record(APP_TOKEN, TABLE_ID, RECORD_ID, {})

        assert result == {}

    def test_writes_audit_log_on_success(self, client, mock_db):
        """成功时写入审计日志，pre_state 含 record_id。"""
        api_resp = {"code": 0, "data": {"record": {"record_id": RECORD_ID, "fields": {}}}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.update_record(APP_TOKEN, TABLE_ID, RECORD_ID, {"状态": "已完成"})

        mock_db.add.assert_called_once()
        log_arg = mock_db.add.call_args[0][0]
        assert log_arg.action == "bitable.update_record"
        assert log_arg.pre_state["record_id"] == RECORD_ID


# ============================================================================ #
#  BitableSyncClient.list_records
# ============================================================================ #

class TestListRecords:
    def test_returns_records_on_success(self, client):
        """成功时返回记录列表。"""
        items = [
            {"record_id": "rec001", "fields": {"名称": "商品A"}},
            {"record_id": "rec002", "fields": {"名称": "商品B"}},
        ]
        api_resp = {
            "code": 0,
            "data": {"items": items, "has_more": False, "page_token": None},
        }
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.list_records(APP_TOKEN, TABLE_ID)

        assert len(result) == 2
        assert result[0]["record_id"] == "rec001"

    def test_sends_filter_expr_as_param(self, client):
        """传入 filter_expr 时应作为 filter 查询参数发送。"""
        api_resp = {
            "code": 0,
            "data": {"items": [], "has_more": False, "page_token": None},
        }
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        filter_expr = 'CurrentValue.[状态]="待处理"'
        with patch("httpx.Client", return_value=mock_httpx_client):
            client.list_records(APP_TOKEN, TABLE_ID, filter_expr=filter_expr)

        call_kwargs = mock_httpx_client.get.call_args[1]
        assert call_kwargs["params"]["filter"] == filter_expr

    def test_paginates_automatically(self, client):
        """当 has_more=True 时应继续请求下一页直到 has_more=False。"""
        page1_items = [{"record_id": f"rec00{i}", "fields": {}} for i in range(3)]
        page2_items = [{"record_id": f"rec01{i}", "fields": {}} for i in range(2)]

        resp1 = _mock_httpx_response({
            "code": 0,
            "data": {"items": page1_items, "has_more": True, "page_token": "token_page2"},
        })
        resp2 = _mock_httpx_response({
            "code": 0,
            "data": {"items": page2_items, "has_more": False, "page_token": None},
        })

        mock_httpx_client1 = _make_mock_httpx_client(resp1)
        mock_httpx_client2 = _make_mock_httpx_client(resp2)

        call_count = {"n": 0}

        def client_factory(*args, **kwargs):
            call_count["n"] += 1
            return mock_httpx_client1 if call_count["n"] == 1 else mock_httpx_client2

        with patch("httpx.Client", side_effect=client_factory):
            result = client.list_records(APP_TOKEN, TABLE_ID)

        assert len(result) == 5

    def test_returns_empty_list_on_api_error(self, client):
        """API 返回错误时返回空列表。"""
        api_resp = {"code": 99991663, "msg": "error"}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.list_records(APP_TOKEN, TABLE_ID)

        assert result == []

    def test_returns_empty_list_on_exception(self, client):
        """网络异常时返回空列表，不抛异常。"""
        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.get.side_effect = httpx.ConnectError("连接失败")

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.list_records(APP_TOKEN, TABLE_ID)

        assert result == []

    def test_no_filter_when_none(self, client):
        """filter_expr 为 None 时不应发送 filter 参数。"""
        api_resp = {
            "code": 0,
            "data": {"items": [], "has_more": False, "page_token": None},
        }
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.list_records(APP_TOKEN, TABLE_ID, filter_expr=None)

        call_kwargs = mock_httpx_client.get.call_args[1]
        assert "filter" not in call_kwargs["params"]


# ============================================================================ #
#  BitableSyncClient.delete_record
# ============================================================================ #

class TestDeleteRecord:
    def test_returns_true_on_success(self, client):
        """成功删除时返回 True。"""
        api_resp = {"code": 0, "data": {"deleted": True, "record_id": RECORD_ID}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.delete_record(APP_TOKEN, TABLE_ID, RECORD_ID)

        assert result is True

    def test_calls_delete_method(self, client):
        """应使用 DELETE 方法。"""
        api_resp = {"code": 0, "data": {"deleted": True, "record_id": RECORD_ID}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.delete_record(APP_TOKEN, TABLE_ID, RECORD_ID)

        mock_httpx_client.delete.assert_called_once()
        call_args = mock_httpx_client.delete.call_args
        expected_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1"
            f"/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{RECORD_ID}"
        )
        assert call_args[0][0] == expected_url

    def test_returns_false_on_api_error(self, client):
        """API 错误时返回 False。"""
        api_resp = {"code": 1254040, "msg": "record not found"}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.delete_record(APP_TOKEN, TABLE_ID, RECORD_ID)

        assert result is False

    def test_returns_false_on_exception(self, client):
        """异常时返回 False，不抛出。"""
        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.delete.side_effect = httpx.ConnectError("连接失败")

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.delete_record(APP_TOKEN, TABLE_ID, RECORD_ID)

        assert result is False

    def test_writes_audit_log_on_success(self, client, mock_db):
        """成功删除时写入审计日志。"""
        api_resp = {"code": 0, "data": {"deleted": True, "record_id": RECORD_ID}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.delete_record(APP_TOKEN, TABLE_ID, RECORD_ID)

        mock_db.add.assert_called_once()
        log_arg = mock_db.add.call_args[0][0]
        assert log_arg.action == "bitable.delete_record"
        assert log_arg.post_state["deleted"] is True


# ============================================================================ #
#  BitableSyncClient.batch_create_records
# ============================================================================ #

class TestBatchCreateRecords:
    def test_creates_all_records_in_single_batch(self, client):
        """少于 50 条时单批发送，返回所有记录。"""
        input_records = [{"名称": f"商品{i}"} for i in range(10)]
        created = [{"record_id": f"rec{i:03d}", "fields": {"名称": f"商品{i}"}} for i in range(10)]
        api_resp = {"code": 0, "data": {"records": created}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            result = client.batch_create_records(APP_TOKEN, TABLE_ID, input_records)

        assert len(result) == 10
        mock_httpx_client.post.assert_called_once()

    def test_splits_into_batches_when_over_50(self, client):
        """超过 50 条时自动分批，每批不超过 50 条。"""
        input_records = [{"名称": f"商品{i}"} for i in range(110)]

        def make_created(batch_records):
            return [{"record_id": f"rec{i:03d}", "fields": r} for i, r in enumerate(batch_records)]

        call_responses = []
        for i in range(0, 110, 50):
            batch = input_records[i: i + 50]
            api_resp = {"code": 0, "data": {"records": make_created(batch)}}
            mock_resp = _mock_httpx_response(api_resp)
            mock_httpx_client = _make_mock_httpx_client(mock_resp)
            call_responses.append(mock_httpx_client)

        call_count = {"n": 0}

        def client_factory(*args, **kwargs):
            idx = call_count["n"]
            call_count["n"] += 1
            return call_responses[idx]

        with patch("httpx.Client", side_effect=client_factory):
            result = client.batch_create_records(APP_TOKEN, TABLE_ID, input_records)

        # 3 批（50+50+10）
        assert call_count["n"] == 3
        assert len(result) == 110

    def test_skips_failed_batch_continues_rest(self, client):
        """某批失败时跳过该批，继续处理后续批次。"""
        input_records = [{"名称": f"商品{i}"} for i in range(60)]

        batch2_created = [{"record_id": f"rec{i:03d}", "fields": {"名称": f"商品{i}"}} for i in range(10)]

        # 第一批：API 错误
        resp1 = _mock_httpx_response({"code": 99999, "msg": "error"})
        mock_client1 = _make_mock_httpx_client(resp1)

        # 第二批：成功
        resp2 = _mock_httpx_response({"code": 0, "data": {"records": batch2_created}})
        mock_client2 = _make_mock_httpx_client(resp2)

        call_count = {"n": 0}

        def client_factory(*args, **kwargs):
            idx = call_count["n"]
            call_count["n"] += 1
            return mock_client1 if idx == 0 else mock_client2

        with patch("httpx.Client", side_effect=client_factory):
            result = client.batch_create_records(APP_TOKEN, TABLE_ID, input_records)

        # 第一批失败，第二批成功 → 共 10 条
        assert len(result) == 10

    def test_returns_empty_list_when_no_records(self, client):
        """传入空列表时无请求，返回空列表。"""
        with patch("httpx.Client") as mock_client_cls:
            result = client.batch_create_records(APP_TOKEN, TABLE_ID, [])

        assert result == []
        mock_client_cls.assert_not_called()

    def test_uses_batch_create_url(self, client):
        """应调用 batch_create 端点。"""
        input_records = [{"名称": "商品A"}]
        api_resp = {"code": 0, "data": {"records": [{"record_id": "rec001", "fields": {}}]}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.batch_create_records(APP_TOKEN, TABLE_ID, input_records)

        expected_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1"
            f"/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create"
        )
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == expected_url

    def test_payload_wraps_fields(self, client):
        """发送的 payload 应将每条记录的字段包裹在 fields 键下。"""
        input_records = [{"名称": "商品A"}, {"名称": "商品B"}]
        api_resp = {"code": 0, "data": {"records": []}}
        mock_resp = _mock_httpx_response(api_resp)
        mock_httpx_client = _make_mock_httpx_client(mock_resp)

        with patch("httpx.Client", return_value=mock_httpx_client):
            client.batch_create_records(APP_TOKEN, TABLE_ID, input_records)

        call_kwargs = mock_httpx_client.post.call_args[1]
        payload = call_kwargs["json"]
        assert "records" in payload
        assert payload["records"][0] == {"fields": {"名称": "商品A"}}
        assert payload["records"][1] == {"fields": {"名称": "商品B"}}

    def test_writes_audit_log_per_batch(self, client, mock_db):
        """每成功批次写一条审计日志。"""
        input_records = [{"名称": f"商品{i}"} for i in range(60)]

        def make_resp(n):
            created = [{"record_id": f"rec{i:03d}", "fields": {}} for i in range(n)]
            return _mock_httpx_response({"code": 0, "data": {"records": created}})

        call_count = {"n": 0}

        def client_factory(*args, **kwargs):
            idx = call_count["n"]
            call_count["n"] += 1
            resp = make_resp(50 if idx == 0 else 10)
            mc = _make_mock_httpx_client(resp)
            return mc

        with patch("httpx.Client", side_effect=client_factory):
            client.batch_create_records(APP_TOKEN, TABLE_ID, input_records)

        # 2 批 → 2 次 add
        assert mock_db.add.call_count == 2
        for c in mock_db.add.call_args_list:
            assert c[0][0].action == "bitable.batch_create_records"


# ============================================================================ #
#  模块级导入测试
# ============================================================================ #

class TestModuleImport:
    def test_can_import_bitable_sync(self):
        """bitable_sync 模块应可正常导入。"""
        from src.feishu import bitable_sync  # noqa: F401
        assert bitable_sync is not None

    def test_can_import_BitableSyncClient_from_package(self):
        """BitableSyncClient 应从 src.feishu 包直接导入。"""
        from src.feishu import BitableSyncClient  # noqa: F401
        assert BitableSyncClient is not None

    def test_bitable_sync_client_is_instantiable(self):
        """BitableSyncClient 应可不传参实例化。"""
        from src.feishu.bitable_sync import BitableSyncClient
        c = BitableSyncClient()
        assert c is not None

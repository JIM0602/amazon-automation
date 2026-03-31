"""飞书模块单元测试 — 全部使用 unittest.mock，无需真实飞书账号。"""
from __future__ import annotations

import hashlib
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ============================================================================ #
#  Fixtures / Helpers
# ============================================================================ #

@pytest.fixture()
def mock_settings():
    """伪造 settings，避免读取 .env 文件。"""
    # 必须先导入，patch 才能找到对象
    import src.feishu.bot_handler  # noqa: F401
    with patch("src.feishu.bot_handler.settings") as m:
        m.FEISHU_APP_ID = "test_app_id"
        m.FEISHU_APP_SECRET = "test_app_secret"
        m.FEISHU_ENCRYPT_KEY = None
        yield m


@pytest.fixture()
def bot(mock_settings):
    """返回一个注入了 mock settings 的 FeishuBot 实例。"""
    # 重置全局单例，防止跨测试污染
    import src.feishu.bot_handler as bh
    bh._bot_instance = None

    from src.feishu.bot_handler import FeishuBot
    return FeishuBot(
        app_id="test_app_id",
        app_secret="test_app_secret",
        encrypt_key=None,
    )


@pytest.fixture()
def mock_token_response():
    """模拟获取 tenant_access_token 的 HTTP 响应。"""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "code": 0,
        "tenant_access_token": "mock_token_abc123",
        "expire": 7200,
    }
    return resp


@pytest.fixture()
def mock_send_response():
    """模拟发送消息的 HTTP 响应。"""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"code": 0, "data": {"message_id": "om_test_msg_001"}}
    return resp


# ============================================================================ #
#  FeishuBot — get_tenant_access_token
# ============================================================================ #

class TestGetTenantAccessToken:
    def test_fetches_token_on_first_call(self, bot, mock_token_response):
        """首次调用应发起 HTTP 请求并返回 token。"""
        with patch("src.feishu.bot_handler.requests.post", return_value=mock_token_response) as mock_post:
            token = bot.get_tenant_access_token()

        assert token == "mock_token_abc123"
        mock_post.assert_called_once_with(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": "test_app_id", "app_secret": "test_app_secret"},
            timeout=10,
        )

    def test_caches_token_within_expiry(self, bot, mock_token_response):
        """有效期内复用 token，不重复请求。"""
        with patch("src.feishu.bot_handler.requests.post", return_value=mock_token_response) as mock_post:
            t1 = bot.get_tenant_access_token()
            t2 = bot.get_tenant_access_token()

        assert t1 == t2 == "mock_token_abc123"
        # 只调用了一次
        mock_post.assert_called_once()

    def test_refreshes_token_when_expired(self, bot, mock_token_response):
        """token 过期后应重新请求。"""
        with patch("src.feishu.bot_handler.requests.post", return_value=mock_token_response) as mock_post:
            bot.get_tenant_access_token()
            # 强制让 token 过期
            bot._token_expire_at = time.time() - 1
            bot.get_tenant_access_token()

        assert mock_post.call_count == 2

    def test_raises_on_api_error(self, bot):
        """API 返回非0 code 时应抛出 RuntimeError。"""
        error_resp = MagicMock()
        error_resp.raise_for_status = MagicMock()
        error_resp.json.return_value = {"code": 99991663, "msg": "app not exist"}

        with patch("src.feishu.bot_handler.requests.post", return_value=error_resp):
            with pytest.raises(RuntimeError, match="获取飞书 token 失败"):
                bot.get_tenant_access_token()


# ============================================================================ #
#  FeishuBot — send_text_message
# ============================================================================ #

class TestSendTextMessage:
    def test_sends_correct_payload(self, bot, mock_token_response, mock_send_response):
        """应以正确的格式发送文本消息。"""
        with patch("src.feishu.bot_handler.requests.post") as mock_post:
            # 第1次调用获取 token，第2次发消息
            mock_post.side_effect = [mock_token_response, mock_send_response]
            result = bot.send_text_message("oc_test_chat_001", "Hello 飞书！")

        assert result["code"] == 0
        assert result["data"]["message_id"] == "om_test_msg_001"

        # 验证发消息时的请求参数
        send_call = mock_post.call_args_list[1]
        call_kwargs = send_call.kwargs if send_call.kwargs else send_call[1]
        payload = call_kwargs["json"]

        assert payload["receive_id"] == "oc_test_chat_001"
        assert payload["msg_type"] == "text"
        # content 应为 JSON 字符串，包含 text 字段
        content_dict = json.loads(payload["content"])
        assert content_dict["text"] == "Hello 飞书！"

    def test_sets_authorization_header(self, bot, mock_token_response, mock_send_response):
        """请求头应包含 Bearer token。"""
        with patch("src.feishu.bot_handler.requests.post") as mock_post:
            mock_post.side_effect = [mock_token_response, mock_send_response]
            bot.send_text_message("oc_chat", "test")

        send_call = mock_post.call_args_list[1]
        call_kwargs = send_call.kwargs if send_call.kwargs else send_call[1]
        headers = call_kwargs["headers"]
        assert headers["Authorization"] == "Bearer mock_token_abc123"


# ============================================================================ #
#  FeishuBot — send_card_message
# ============================================================================ #

class TestSendCardMessage:
    def test_sends_interactive_msg_type(self, bot, mock_token_response, mock_send_response):
        """卡片消息应使用 msg_type=interactive。"""
        card = {
            "config": {"wide_screen_mode": True},
            "elements": [{"tag": "div", "text": {"content": "选品报告", "tag": "plain_text"}}],
        }

        with patch("src.feishu.bot_handler.requests.post") as mock_post:
            mock_post.side_effect = [mock_token_response, mock_send_response]
            result = bot.send_card_message("oc_test_chat_002", card)

        assert result["code"] == 0

        send_call = mock_post.call_args_list[1]
        call_kwargs = send_call.kwargs if send_call.kwargs else send_call[1]
        payload = call_kwargs["json"]

        assert payload["msg_type"] == "interactive"
        content_dict = json.loads(payload["content"])
        assert content_dict["config"]["wide_screen_mode"] is True

    def test_card_content_serialized_as_json_string(self, bot, mock_token_response, mock_send_response):
        """card 参数应被序列化为 JSON 字符串作为 content 字段。"""
        card = {"elements": [{"tag": "hr"}]}

        with patch("src.feishu.bot_handler.requests.post") as mock_post:
            mock_post.side_effect = [mock_token_response, mock_send_response]
            bot.send_card_message("oc_chat", card)

        send_call = mock_post.call_args_list[1]
        call_kwargs = send_call.kwargs if send_call.kwargs else send_call[1]
        payload = call_kwargs["json"]
        # content 必须是字符串，而非嵌套 dict
        assert isinstance(payload["content"], str)


# ============================================================================ #
#  FeishuBot — parse_webhook_event
# ============================================================================ #

class TestParseWebhookEvent:
    def test_parses_valid_json_body(self, bot):
        """合法 JSON 请求体应被正确解析为 dict。"""
        body = json.dumps({"type": "url_verification", "challenge": "abc"}).encode()
        event = bot.parse_webhook_event(body, {})
        assert event["type"] == "url_verification"
        assert event["challenge"] == "abc"

    def test_raises_on_invalid_json(self, bot):
        """非法 JSON 应抛出 ValueError。"""
        with pytest.raises(ValueError, match="无效的 JSON"):
            bot.parse_webhook_event(b"not json", {})

    def test_skips_signature_check_without_encrypt_key(self, bot):
        """没有 encrypt_key 时不进行签名验证，直接解析。"""
        bot._encrypt_key = None
        body = json.dumps({"type": "url_verification", "challenge": "xyz"}).encode()
        # 不提供签名头，也不应抛异常
        event = bot.parse_webhook_event(body, {})
        assert event["challenge"] == "xyz"

    def test_validates_signature_with_encrypt_key(self):
        """配置了 encrypt_key 时，签名正确应通过验证。"""
        from src.feishu.bot_handler import FeishuBot

        encrypt_key = "my_secret_key"
        bot_with_key = FeishuBot("app_id", "app_secret", encrypt_key=encrypt_key)

        body = json.dumps({"type": "event_callback"}).encode("utf-8")
        timestamp = "1609459200"
        nonce = "abc123"

        # 构造正确签名
        raw = (timestamp + nonce + encrypt_key + body.decode("utf-8")).encode("utf-8")
        signature = hashlib.sha256(raw).hexdigest()

        headers = {
            "X-Lark-Signature": signature,
            "X-Lark-Request-Timestamp": timestamp,
            "X-Lark-Request-Nonce": nonce,
        }
        event = bot_with_key.parse_webhook_event(body, headers)
        assert event["type"] == "event_callback"

    def test_rejects_wrong_signature(self):
        """签名错误时应抛出 ValueError。"""
        from src.feishu.bot_handler import FeishuBot

        bot_with_key = FeishuBot("app_id", "app_secret", encrypt_key="secret")
        body = b'{"type": "event_callback"}'
        headers = {
            "X-Lark-Signature": "wrong_signature",
            "X-Lark-Request-Timestamp": "1609459200",
            "X-Lark-Request-Nonce": "nonce",
        }
        with pytest.raises(ValueError, match="签名验证失败"):
            bot_with_key.parse_webhook_event(body, headers)


# ============================================================================ #
#  command_router — route_command
# ============================================================================ #

class TestRouteCommand:
    def test_knowledge_query_with_question_mark_en(self):
        """英文问号开头 → knowledge_query。"""
        from src.feishu.command_router import route_command

        result = route_command("?如何处理差评", "user_001")
        assert result["action"] == "knowledge_query"
        assert result["query"] == "如何处理差评"
        assert result["sender_id"] == "user_001"

    def test_knowledge_query_with_question_mark_cn(self):
        """中文问号开头 → knowledge_query。"""
        from src.feishu.command_router import route_command

        result = route_command("？亚马逊广告优化", "user_002")
        assert result["action"] == "knowledge_query"
        assert result["query"] == "亚马逊广告优化"

    def test_daily_report_with_ribao(self):
        """包含"日报" → daily_report。"""
        from src.feishu.command_router import route_command

        result = route_command("帮我生成今天的日报", "user_003")
        assert result["action"] == "daily_report"

    def test_daily_report_with_baogao(self):
        """包含"报告" → daily_report。"""
        from src.feishu.command_router import route_command

        result = route_command("发一下昨天的报告", "user_004")
        assert result["action"] == "daily_report"

    def test_selection_analysis(self):
        """包含"选品" → selection_analysis。"""
        from src.feishu.command_router import route_command

        result = route_command("帮我做选品分析", "user_005")
        assert result["action"] == "selection_analysis"

    def test_unknown_command_returns_help(self):
        """未知命令 → unknown + 帮助提示。"""
        from src.feishu.command_router import route_command

        result = route_command("你好", "user_006")
        assert result["action"] == "unknown"
        assert "message" in result
        assert len(result["message"]) > 0

    def test_unknown_command_includes_usage_hints(self):
        """帮助提示应包含主要命令说明。"""
        from src.feishu.command_router import route_command

        result = route_command("随便说点什么", "user_007")
        assert "?" in result["message"] or "？" in result["message"]

    def test_empty_message_returns_unknown(self):
        """空消息 → unknown。"""
        from src.feishu.command_router import route_command

        result = route_command("   ", "user_008")
        assert result["action"] == "unknown"


# ============================================================================ #
#  FastAPI 接口测试
# ============================================================================ #

@pytest.fixture()
def client(mock_settings):
    """创建 FastAPI TestClient，并重置全局 bot 单例。"""
    import src.feishu.bot_handler as bh
    bh._bot_instance = None

    # 注入一个 mock bot，避免在 get_bot() 时读取真实 settings
    mock_bot = MagicMock()
    mock_bot.parse_webhook_event.side_effect = lambda body, headers: json.loads(body)
    bh._bot_instance = mock_bot

    from src.api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_returns_ok(self, client):
        """/health 应返回 200 {"status": "ok"}。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestFeishuWebhookEndpoint:
    def test_url_verification_returns_challenge(self, client):
        """url_verification 类型应返回 challenge 字符串。"""
        payload = {"type": "url_verification", "challenge": "test_challenge_xyz"}
        resp = client.post(
            "/feishu/webhook",
            content=json.dumps(payload),
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "test_challenge_xyz"

    def test_message_event_returns_code_zero(self, client):
        """普通消息事件应返回 {"code": 0}。"""
        payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_type": "text",
                    "content": json.dumps({"text": "?如何优化广告"}),
                },
                "sender": {"sender_id": {"open_id": "ou_test_sender"}},
            },
        }
        resp = client.post(
            "/feishu/webhook",
            content=json.dumps(payload),
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"code": 0}

    def test_invalid_json_returns_400(self, mock_settings):
        """签名验证失败（模拟）应返回 400。"""
        import src.feishu.bot_handler as bh
        bh._bot_instance = None

        # 构造一个 bot 实例，parse_webhook_event 抛出 ValueError
        mock_bot = MagicMock()
        mock_bot.parse_webhook_event.side_effect = ValueError("飞书 Webhook 签名验证失败")
        bh._bot_instance = mock_bot

        from src.api.main import app
        c = TestClient(app)
        resp = c.post(
            "/feishu/webhook",
            content=b"bad body",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 1

    def test_non_message_event_returns_code_zero(self, client):
        """非消息类型事件也应返回 {"code": 0}（忽略处理）。"""
        payload = {
            "header": {"event_type": "contact.user.created_v3"},
            "event": {},
        }
        resp = client.post(
            "/feishu/webhook",
            content=json.dumps(payload),
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"code": 0}

    def test_non_text_message_type_ignored(self, client):
        """图片/文件等非文本消息应被忽略，仍返回 {"code": 0}。"""
        payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {"message_type": "image", "content": "{}"},
                "sender": {"sender_id": {"open_id": "ou_test"}},
            },
        }
        resp = client.post(
            "/feishu/webhook",
            content=json.dumps(payload),
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"code": 0}

"""飞书机器人核心模块：消息发送+Webhook接收处理。"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

import requests

try:
    from src.config import settings
except ImportError:  # pragma: no cover
    settings = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  飞书 Open API 端点
# --------------------------------------------------------------------------- #
_FEISHU_API_BASE = "https://open.feishu.cn/open-apis"
_TOKEN_URL = f"{_FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
_SEND_MSG_URL = f"{_FEISHU_API_BASE}/im/v1/messages?receive_id_type=chat_id"
_UPDATE_MSG_URL = f"{_FEISHU_API_BASE}/im/v1/messages/{{message_id}}"

class FeishuBot:
    """飞书自建应用机器人封装，支持文本/卡片消息发送及 Webhook 事件解析。"""

    def __init__(self, app_id: str, app_secret: str, encrypt_key: Optional[str] = None):
        self._app_id = app_id
        self._app_secret = app_secret
        self._encrypt_key = encrypt_key

        # token 缓存
        self._tenant_access_token: Optional[str] = None
        self._token_expire_at: float = 0.0

    # ---------------------------------------------------------------------- #
    #  Token 管理
    # ---------------------------------------------------------------------- #

    def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token，在有效期内复用（有效期约 2 小时）。"""
        now = time.time()
        # 提前 5 分钟刷新
        if self._tenant_access_token and now < self._token_expire_at - 300:
            return self._tenant_access_token

        resp = requests.post(
            _TOKEN_URL,
            json={"app_id": self._app_id, "app_secret": self._app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取飞书 token 失败: {data}")

        self._tenant_access_token = data["tenant_access_token"]
        if not isinstance(self._tenant_access_token, str) or not self._tenant_access_token:
            raise RuntimeError(f"获取飞书 token 失败: {data}")
        # expire 字段单位为秒
        self._token_expire_at = now + data.get("expire", 7200)
        return self._tenant_access_token

    # ---------------------------------------------------------------------- #
    #  消息发送
    # ---------------------------------------------------------------------- #

    def _auth_headers(self) -> Dict[str, str]:
        token = self.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def send_text_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """发送文本消息到飞书群，返回 API 响应 dict。"""
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        resp = requests.post(
            _SEND_MSG_URL,
            headers=self._auth_headers(),
            json=payload,
            timeout=10,
        )
        if not resp.ok:
            logger.error("send_text_message 失败: status=%s body=%s chat_id=%s", resp.status_code, resp.text, chat_id)
        resp.raise_for_status()
        return resp.json()

    def send_card_message(self, chat_id: str, card: Dict[str, Any]) -> Dict[str, Any]:
        """发送交互卡片消息到飞书群，card 参数为飞书卡片 JSON dict。"""
        payload = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        }
        resp = requests.post(
            _SEND_MSG_URL,
            headers=self._auth_headers(),
            json=payload,
            timeout=10,
        )
        if not resp.ok:
            logger.error("send_card_message 失败: status=%s body=%s chat_id=%s", resp.status_code, resp.text, chat_id)
        resp.raise_for_status()
        return resp.json()

    def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """兼容别名：发送文本消息。"""
        return self.send_text_message(chat_id, text)

    def send_card(self, chat_id: str, card: Dict[str, Any]) -> Dict[str, Any]:
        """兼容别名：发送交互卡片消息。"""
        return self.send_card_message(chat_id, card)

    def send_thinking(self, chat_id: str) -> str:
        """发送"🤔 正在思考中..."临时消息，返回 message_id。"""
        result = self.send_text_message(chat_id, "🤔 正在思考中...")
        # 从响应中提取 message_id
        message_id = result.get("data", {}).get("message_id", "")
        return message_id

    def update_message(self, message_id: str, new_content: str) -> Dict[str, Any]:
        """用新内容替换已发送的消息（PUT /im/v1/messages/{message_id}）。"""
        url = _UPDATE_MSG_URL.format(message_id=message_id)
        payload = {
            "msg_type": "text",
            "content": json.dumps({"text": new_content}, ensure_ascii=False),
        }
        resp = requests.patch(
            url,
            headers=self._auth_headers(),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # ---------------------------------------------------------------------- #
    #  Webhook 解析
    # ---------------------------------------------------------------------- #

    def parse_webhook_event(self, request_body: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """解析飞书 Webhook 回调事件。

        如果配置了 encrypt_key，则验证签名（X-Lark-Signature）。
        返回事件 dict（已解析 JSON）。
        """
        # 1. 签名验证
        self.verify_webhook(request_body, headers)

        # 2. 解析 JSON
        try:
            event = json.loads(request_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"无效的 JSON 请求体: {exc}") from exc

        return event

    def verify_webhook(self, body: bytes, headers: Dict[str, str]) -> None:
        """验证飞书 Webhook 签名（HMAC-SHA256）。"""
        if not self._encrypt_key:
            return

        # 飞书签名头字段
        signature = headers.get("X-Lark-Signature") or headers.get("x-lark-signature", "")
        timestamp = headers.get("X-Lark-Request-Timestamp") or headers.get(
            "x-lark-request-timestamp", ""
        )
        nonce = headers.get("X-Lark-Request-Nonce") or headers.get(
            "x-lark-request-nonce", ""
        )

        # 构造待签字符串：timestamp + nonce + encrypt_key + body
        raw = (timestamp + nonce + (self._encrypt_key or "") + body.decode("utf-8")).encode(
            "utf-8"
        )
        expected = hashlib.sha256(raw).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError("飞书 Webhook 签名验证失败")

    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """简化的事件处理：仅保留 Web 跳转与握手响应。"""
        try:
            if event.get("type") == "url_verification":
                return {"challenge": event.get("challenge", "")}

            header = event.get("header", {})
            if header.get("event_type") != "im.message.receive_v1":
                return {"code": 0}

            message_obj = event.get("event", {}).get("message", {})
            if message_obj.get("message_type") != "text":
                return {"code": 0}

            return {
                "chat_id": message_obj.get("chat_id", ""),
                "reply": "请使用 Web 端进行对话交互: https://52.221.207.30",
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("handle_event 失败: %s", exc, exc_info=True)
            return {"code": 0}


# --------------------------------------------------------------------------- #
#  全局单例
# --------------------------------------------------------------------------- #
_bot_instance: Optional[FeishuBot] = None


def get_bot() -> FeishuBot:
    """返回全局 FeishuBot 实例（懒加载），凭证从 settings 读取。"""
    global _bot_instance
    if _bot_instance is None:
        if settings is None:
            raise RuntimeError("settings 未初始化，无法创建 FeishuBot")
        _bot_instance = FeishuBot(
            app_id=settings.FEISHU_APP_ID,
            app_secret=settings.FEISHU_APP_SECRET,
            encrypt_key=getattr(settings, "FEISHU_ENCRYPT_KEY", None),
        )
    return _bot_instance

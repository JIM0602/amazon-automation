"""飞书机器人核心模块：消息发送+Webhook接收处理。"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Optional

import requests

try:
    from src.config import settings
except ImportError:  # pragma: no cover
    settings = None  # type: ignore[assignment]

try:
    from src.knowledge_base.rag_engine import query as rag_query
except ImportError:  # pragma: no cover
    rag_query = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  飞书 Open API 端点
# --------------------------------------------------------------------------- #
_FEISHU_API_BASE = "https://open.feishu.cn/open-apis"
_TOKEN_URL = f"{_FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
_SEND_MSG_URL = f"{_FEISHU_API_BASE}/im/v1/messages?receive_id_type=chat_id"
_UPDATE_MSG_URL = f"{_FEISHU_API_BASE}/im/v1/messages/{{message_id}}"

# --------------------------------------------------------------------------- #
#  会话上下文存储（内存，模块级字典）
# --------------------------------------------------------------------------- #
_CONTEXT: dict = {}
_MAX_CONTEXT_ROUNDS = 5


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
        # expire 字段单位为秒
        self._token_expire_at = now + data.get("expire", 7200)
        return self._tenant_access_token  # type: ignore[return-value]

    # ---------------------------------------------------------------------- #
    #  消息发送
    # ---------------------------------------------------------------------- #

    def _auth_headers(self) -> dict:
        token = self.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def send_text_message(self, chat_id: str, text: str) -> dict:
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

    def send_card_message(self, chat_id: str, card: dict) -> dict:
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

    def send_thinking(self, chat_id: str) -> str:
        """发送"🤔 正在思考中..."临时消息，返回 message_id。"""
        result = self.send_text_message(chat_id, "🤔 正在思考中...")
        # 从响应中提取 message_id
        message_id = result.get("data", {}).get("message_id", "")
        return message_id

    def update_message(self, message_id: str, new_content: str) -> dict:
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

    def parse_webhook_event(self, request_body: bytes, headers: dict) -> dict:
        """解析飞书 Webhook 回调事件。

        如果配置了 encrypt_key，则验证签名（X-Lark-Signature）。
        返回事件 dict（已解析 JSON）。
        """
        # 1. 签名验证
        if self._encrypt_key:
            self._verify_signature(request_body, headers)

        # 2. 解析 JSON
        try:
            event = json.loads(request_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"无效的 JSON 请求体: {exc}") from exc

        return event

    def _verify_signature(self, body: bytes, headers: dict) -> None:
        """验证飞书 Webhook 签名（HMAC-SHA256）。"""
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


# --------------------------------------------------------------------------- #
#  模块级问答辅助函数
# --------------------------------------------------------------------------- #

def _get_context(user_id: str) -> list:
    """获取用户会话上下文列表。"""
    return _CONTEXT.get(user_id, [])


def _add_to_context(user_id: str, role: str, content: str) -> None:
    """向用户会话上下文追加一条消息，超过5轮时清除。"""
    if user_id not in _CONTEXT:
        _CONTEXT[user_id] = []
    _CONTEXT[user_id].append({"role": role, "content": content})
    # 每轮含一条 user + 一条 assistant，超过5轮（10条）时清除
    if len(_CONTEXT[user_id]) > _MAX_CONTEXT_ROUNDS * 2:
        _CONTEXT[user_id] = []


def handle_qa(user_id: str, chat_id: str, question: str) -> str:
    """完整问答流程：发送thinking → 调用RAG → 格式化 → 更新消息。

    Args:
        user_id: 发送者 open_id（用于会话上下文）。
        chat_id: 飞书群/会话 ID（用于发送消息）。
        question: 用户提问文本。

    Returns:
        最终回答字符串。
    """
    bot = get_bot()

    # 1. 发送"正在思考中..."占位消息
    message_id = ""
    try:
        message_id = bot.send_thinking(chat_id)
    except Exception:
        logger.warning("send_thinking 失败，跳过占位消息")

    # 2. 记录用户问题到上下文
    _add_to_context(user_id, "user", question)

    # 3. 调用 RAG 获取答案
    answer = ""
    try:
        if rag_query is None:
            raise ImportError("rag_query 不可用")
        answer = rag_query(question)
    except ImportError:
        answer = "系统出错，请稍后重试"
    except Exception:
        answer = "系统出错，请稍后重试"

    # 4. 记录助手回答到上下文
    _add_to_context(user_id, "assistant", answer)

    # 5. 更新占位消息为正式回答
    if message_id:
        try:
            bot.update_message(message_id, answer)
        except Exception:
            logger.warning("update_message 失败，尝试发送新消息")
            try:
                bot.send_text_message(chat_id, answer)
            except Exception:
                logger.error("send_text_message 也失败，放弃发送")

    return answer
